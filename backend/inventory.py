"""
VERA — Veritas Engine for Replenishment & Anticipation.
The self-correcting inventory brain behind BatchTwin.

Thesis: classic inventory AI forecasts demand on numbers that are already wrong,
because the ERP deducts *theoretical* BOM quantities and ignores real process
losses. VERA corrects the numbers first (real consumption = theoretical x (1+loss),
learned from execution), then:
  1. forecasts finished-good demand (seasonal-trend decomposition),
  2. explodes it into TRUE raw-material requirements through the BOM,
  3. projects each SKU forward with FEFO + shelf-life (stockout AND expiry),
  4. emits a ranked decision queue: what to order, how much, by when — and what
     will spoil if nothing changes.

Deterministic (seeded) so the demo and tests are stable.
"""
from __future__ import annotations
import datetime as _dt
import math
import numpy as np

from .odoo_adapter import MockOdoo

TODAY = _dt.date.today()
HISTORY_DAYS = 540
HORIZON = 120
Z_95 = 1.65                       # service-level factor for safety stock
REVIEW_DAYS = 7                   # ordering review period

# Per-material profile overrides keyed by Odoo default_code.
# lead = supplier lead time (days), lt_std = its variability, shelf = shelf life,
# loss = real process loss fraction (the correction the ERP ignore), cover = the
# days-of-cover we seed on hand to script a realistic story, exp = lot expiry days.
PROFILE = {
    # imported actives — long lead, high value → stockout-prone
    "RM-MGCIT": dict(lead=45, lt_std=9, shelf=730, loss=0.020, cover=50, exp=560, sup="BioMinerals EU"),
    "RM-B6":    dict(lead=50, lt_std=11, shelf=730, loss=0.015, cover=72, exp=610, sup="VitaSynth Asia"),
    "RM-SPIR":  dict(lead=50, lt_std=12, shelf=730, loss=0.025, cover=38, exp=500, sup="AlgaeSource Asia"),
    # local excipients — short lead, cheap
    "RM-SORB":  dict(lead=14, lt_std=3, shelf=1095, loss=0.008, cover=70, exp=900, sup="ChimiTunisie"),
    "RM-CMC":   dict(lead=16, lt_std=4, shelf=1095, loss=0.010, cover=80, exp=800, sup="ExciPharma TN"),
    "RM-STMG":  dict(lead=18, lt_std=4, shelf=1095, loss=0.012, cover=95, exp=850, sup="ExciPharma TN"),
    "RM-SIL":   dict(lead=18, lt_std=4, shelf=1095, loss=0.012, cover=110, exp=850, sup="ExciPharma TN"),
    "RM-SORBK": dict(lead=20, lt_std=5, shelf=730, loss=0.009, cover=85, exp=700, sup="ConservaChem"),
    "RM-ACID":  dict(lead=12, lt_std=3, shelf=1095, loss=0.007, cover=75, exp=900, sup="ChimiTunisie"),
    # arome — deliberately over-stocked + near expiry → expiry write-off story
    "RM-AROM":  dict(lead=30, lt_std=6, shelf=365, loss=0.008, cover=420, exp=58, sup="AromaMed"),
    # purified water — short shelf life
    "RM-EAU":   dict(lead=3, lt_std=1, shelf=90, loss=0.003, cover=35, exp=75, sup="Interne"),
    # packaging — no real expiry
    "PK-FLA-200": dict(lead=25, lt_std=6, shelf=3650, loss=0.006, cover=70, exp=3000, sup="PlastiPack"),
    "PK-GOB":     dict(lead=22, lt_std=5, shelf=3650, loss=0.004, cover=90, exp=3000, sup="PlastiPack"),
    "PK-ETIQ":    dict(lead=18, lt_std=4, shelf=3650, loss=0.005, cover=120, exp=3000, sup="ImpriLabel"),
    "PK-ETUI":    dict(lead=20, lt_std=5, shelf=3650, loss=0.005, cover=100, exp=3000, sup="CartonPro"),
    "PK-GEL-T0":  dict(lead=28, lt_std=7, shelf=1460, loss=0.007, cover=60, exp=1200, sup="CapsuleCo"),
    "PK-PIL":     dict(lead=24, lt_std=6, shelf=3650, loss=0.005, cover=85, exp=3000, sup="PlastiPack"),
    "PK-ETIQ-G":  dict(lead=18, lt_std=4, shelf=3650, loss=0.005, cover=130, exp=3000, sup="ImpriLabel"),
    "PK-ETUI-G":  dict(lead=20, lt_std=5, shelf=3650, loss=0.005, cover=110, exp=3000, sup="CartonPro"),
}
# finished-good demand shape: base units/day, yearly trend, month multipliers (Jan..Dec)
FG_DEMAND = {
    "FG-MGB6-200": dict(base=175, trend=0.06,
                        months=[1.25, 1.20, 1.10, 1.00, 0.95, 0.90, 0.88, 0.90, 1.00, 1.10, 1.18, 1.22]),  # immunity, winter-heavy
    "FG-SPIR-60":  dict(base=42, trend=0.10,
                        months=[1.05, 1.10, 1.25, 1.30, 1.25, 1.10, 0.95, 0.90, 0.95, 1.00, 1.00, 1.05]),  # weight/vitality, spring-heavy
}
WEEKDAY = np.array([1.08, 1.10, 1.06, 1.07, 1.12, 0.82, 0.68])  # Mon..Sun
# Tunisia Ramadan windows (approx) — a real local demand signal.
RAMADAN = [(_dt.date(2025, 3, 1), _dt.date(2025, 3, 30)),
           (_dt.date(2026, 2, 18), _dt.date(2026, 3, 19))]


def _ramadan_factor(d: _dt.date) -> float:
    for a, b in RAMADAN:
        if a <= d <= b:
            return 1.18   # supplements demand rises around Ramadan
    return 1.0


class Vera:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.odoo = MockOdoo()
        self._build()

    # ---- data assembly -----------------------------------------------------
    def _build(self):
        rng = np.random.default_rng(self.seed)
        prods = {p["default_code"]: p for p in self.odoo.search_read(
            "product.product", [], ["name", "default_code", "standard_price", "uom_name", "list_price"])}
        self.prods = prods

        # per-unit BOM consumption for each finished good
        self.bom_pu = {}      # fg_code -> {rm_code: qty per finished unit}
        self.fg_batch = {}
        for bom in self.odoo.search_read("mrp.bom", [], ["product_id", "product_qty", "bom_line_ids"]):
            fg_code = prods_by_id(prods, bom["product_id"][0])
            per = self.bom_pu.setdefault(fg_code, {})
            for ln in self.odoo.read("mrp.bom.line", bom["bom_line_ids"], ["product_id", "product_qty"]):
                rmc = prods_by_id(prods, ln["product_id"][0])
                per[rmc] = per.get(rmc, 0) + ln["product_qty"] / bom["product_qty"]

        # finished-good demand history (daily)
        self.dates = [TODAY - _dt.timedelta(days=HISTORY_DAYS - 1 - i) for i in range(HISTORY_DAYS)]
        self.fg_hist = {}
        for fg, cfg in FG_DEMAND.items():
            base = np.array([cfg["base"] * (1 + cfg["trend"] / 365 * i) for i in range(HISTORY_DAYS)])
            season = np.array([WEEKDAY[d.weekday()] * cfg["months"][d.month - 1] * _ramadan_factor(d)
                               for d in self.dates])
            noise = rng.normal(1.0, 0.06, HISTORY_DAYS)
            self.fg_hist[fg] = np.maximum(0, base * season * noise)

        # forecast finished-good demand and explode into TRUE rm requirements
        self.fg_fc = {fg: self._forecast(self.fg_hist[fg]) for fg in FG_DEMAND}
        self.future = [TODAY + _dt.timedelta(days=i + 1) for i in range(HORIZON)]

        self.rm_cons = {}     # code -> np.array(HORIZON) TRUE daily consumption (loss-corrected)
        self.rm_cons_theo = {}
        self.rm_product = {}  # code -> finished-good code that consumes it (materials are disjoint)
        for fg, per in self.bom_pu.items():
            fc = self.fg_fc[fg]["mean"]
            for rmc, qpu in per.items():
                loss = PROFILE.get(rmc, {}).get("loss", 0.0)
                self.rm_cons.setdefault(rmc, np.zeros(HORIZON))
                self.rm_cons_theo.setdefault(rmc, np.zeros(HORIZON))
                self.rm_cons[rmc] += fc * qpu * (1 + loss)
                self.rm_cons_theo[rmc] += fc * qpu
                self.rm_product[rmc] = fg

        # seed on-hand stock lots to hit each material's scripted days-of-cover
        self.stock = {}
        for code, cons in self.rm_cons.items():
            prof = PROFILE.get(code, dict(cover=90, exp=800, shelf=730))
            avg = max(cons[:HORIZON].mean(), 1e-6)
            on_hand = round(avg * prof["cover"], 3)
            self.stock[code] = [{"qty": on_hand,
                                 "expiry": TODAY + _dt.timedelta(days=prof["exp"]),
                                 "received": TODAY - _dt.timedelta(days=max(prof["shelf"] - prof["exp"], 0))}]
        self.open_pos = {}    # code -> [{qty, arrival_day_offset}]  (none on order initially)

    # ---- forecasting: seasonal-trend decomposition -------------------------
    def _forecast(self, y: np.ndarray) -> dict:
        n = len(y)
        t = np.arange(n)
        slope, intercept = np.polyfit(t, y, 1)
        trend = np.clip(intercept + slope * t, 1e-6, None)
        ratio = y / trend
        wd = np.array([d.weekday() for d in self.dates])
        mo = np.array([d.month - 1 for d in self.dates])
        wd_idx = np.array([ratio[wd == k].mean() if (wd == k).any() else 1.0 for k in range(7)])
        wd_idx /= wd_idx.mean()
        mo_idx = np.array([ratio[mo == k].mean() if (mo == k).any() else 1.0 for k in range(12)])
        mo_idx /= mo_idx.mean()
        fitted = trend * wd_idx[wd] * mo_idx[mo]
        resid_std = float((y - fitted).std())
        ft = np.arange(n, n + HORIZON)
        ftrend = np.clip(intercept + slope * ft, 1e-6, None)
        fdates = [TODAY + _dt.timedelta(days=i + 1) for i in range(HORIZON)]
        fwd = np.array([d.weekday() for d in fdates])
        fmo = np.array([d.month - 1 for d in fdates])
        mean = ftrend * wd_idx[fwd] * mo_idx[fmo]
        return {"mean": mean, "band": 1.28 * resid_std, "slope": float(slope),
                "wd_idx": wd_idx.tolist(), "mo_idx": mo_idx.tolist(), "resid_std": resid_std}

    # ---- projection: FEFO + shelf life + stockout --------------------------
    def project(self, code: str) -> dict:
        cons = self.rm_cons.get(code)
        if cons is None:
            return {}
        prof = PROFILE.get(code, dict(shelf=730))
        lots = [dict(l) for l in self.stock.get(code, [])]
        traj, stockout_day, expiry_qty, expiry_day = [], None, 0.0, None
        receipts = np.zeros(HORIZON)
        for po in self.open_pos.get(code, []):
            if po["offset"] < HORIZON:
                receipts[po["offset"]] += po["qty"]
        for i in range(HORIZON):
            day = self.future[i]
            if receipts[i] > 0:
                lots.append({"qty": receipts[i], "expiry": day + _dt.timedelta(days=prof["shelf"])})
            for lot in lots:
                if lot["qty"] > 1e-9 and lot["expiry"] <= day:
                    expiry_qty += lot["qty"]
                    if expiry_day is None:
                        expiry_day = i
                    lot["qty"] = 0.0
            need = cons[i]
            for lot in sorted(lots, key=lambda l: l["expiry"]):
                take = min(lot["qty"], need)
                lot["qty"] -= take
                need -= take
                if need <= 1e-9:
                    break
            if need > 1e-6 and stockout_day is None:
                stockout_day = i
            traj.append(round(sum(l["qty"] for l in lots), 3))
        on_hand0 = round(sum(l["qty"] for l in self.stock.get(code, [])), 3)
        avg = float(cons.mean())
        cover = on_hand0 / avg if avg else 999
        unit_cost = self.prods.get(code, {}).get("standard_price", 0) or 0
        return {
            "code": code, "name": self.prods.get(code, {}).get("name", code),
            "unit": self.prods.get(code, {}).get("uom_name", ""),
            "on_hand": on_hand0, "avg_daily": round(avg, 4), "days_cover": round(cover, 1),
            "trajectory": traj, "stockout_day": stockout_day,
            "expiry_qty": round(expiry_qty, 3), "expiry_day": expiry_day,
            "expiry_value": round(expiry_qty * unit_cost, 2),
            "unit_cost": unit_cost, "lead": prof.get("lead"), "shelf": prof.get("shelf"),
            "supplier": prof.get("sup", "—"),
        }

    # ---- recommendation ----------------------------------------------------
    def recommend(self, code: str) -> dict | None:
        pr = self.project(code)
        if not pr:
            return None
        cons = self.rm_cons[code]
        prof = PROFILE.get(code, {})
        lead = prof.get("lead", 21)
        unit_cost = pr["unit_cost"]
        std = float(cons.std())
        safety = Z_95 * std * math.sqrt(max(lead, 1))
        avg = pr["avg_daily"]
        rop = avg * lead + safety
        on_order = sum(po["qty"] for po in self.open_pos.get(code, []))
        available = pr["on_hand"] + on_order

        rec = None
        # stockout-driven order
        if pr["stockout_day"] is not None or available <= rop:
            qty = avg * (lead + REVIEW_DAYS) + safety - available
            # never order more than can be consumed before it would expire
            max_before_expiry = avg * prof.get("shelf", 730) * 0.6
            qty = float(np.clip(qty, 0, max_before_expiry))
            order_by = (pr["stockout_day"] - lead) if pr["stockout_day"] is not None else 0
            if qty > 0:
                rec = {"code": code, "name": pr["name"], "unit": pr["unit"], "action": "ORDER",
                       "qty": round(qty, 3), "order_by_day": max(order_by, 0),
                       "reason": (f"rupture prévue J+{pr['stockout_day']} · délai fournisseur {lead} j"
                                  if pr["stockout_day"] is not None else
                                  f"stock sous le point de commande · délai {lead} j"),
                       "value": round(qty * unit_cost, 2), "supplier": pr["supplier"],
                       "urgency": max(order_by, 0), "stockout_day": pr["stockout_day"]}
        # expiry-driven caution
        if pr["expiry_qty"] > 1e-6:
            over = {"code": code, "name": pr["name"], "unit": pr["unit"], "action": "EXPIRY",
                    "qty": round(pr["expiry_qty"], 3), "order_by_day": pr["expiry_day"],
                    "reason": f"{pr['expiry_qty']:.1f} {pr['unit']} périment J+{pr['expiry_day']} · surstock",
                    "value": pr["expiry_value"], "supplier": pr["supplier"],
                    "urgency": pr["expiry_day"] or 0, "stockout_day": None}
            # expiry is the dominant signal for an over-stocked item
            if rec is None or pr["expiry_qty"] > 0:
                return over if rec is None else (over if pr["expiry_value"] > rec["value"] else rec)
        return rec

    # ---- portfolio views (optional product filter) -------------------------
    def _codes(self, product: str | None) -> list[str]:
        if not product or product == "all":
            return list(self.rm_cons)
        return [c for c in self.rm_cons if self.rm_product.get(c) == product]

    def products(self) -> list[dict]:
        return [{"code": fg, "name": self.prods.get(fg, {}).get("name", fg)} for fg in FG_DEMAND]

    def decision_queue(self, product: str | None = None) -> list[dict]:
        recs = [r for c in self._codes(product) if (r := self.recommend(c))]
        return sorted(recs, key=lambda r: (r["urgency"], -r["value"]))

    def kpis(self, product: str | None = None) -> dict:
        codes = self._codes(product)
        theo_annual = sum(self.rm_cons_theo[c].mean() * 365 * (self.prods.get(c, {}).get("standard_price") or 0)
                          for c in codes)
        true_annual = sum(self.rm_cons[c].mean() * 365 * (self.prods.get(c, {}).get("standard_price") or 0)
                          for c in codes)
        gap = true_annual - theo_annual
        projections = [self.project(c) for c in codes]
        # "urgent" = will stock out before a fresh order could ever arrive (lead time)
        urgent = [p for p in projections
                  if p["stockout_day"] is not None and p["stockout_day"] <= (PROFILE.get(p["code"], {}).get("lead", 21))]
        expiry_val = sum(p["expiry_value"] for p in projections)
        inv_value = sum(p["on_hand"] * p["unit_cost"] for p in projections)
        dead = sum(p["on_hand"] * p["unit_cost"] for p in projections if p["days_cover"] > 180)
        order_now = sum(1 for r in self.decision_queue(product) if r["action"] == "ORDER" and r["order_by_day"] <= REVIEW_DAYS)
        return {
            "truth_gap_pct": round(100 * gap / theo_annual, 2) if theo_annual else 0,
            "truth_gap_eur": round(gap, 0),
            "materials_total": len(codes),
            "urgent_count": len(urgent),
            "urgent_soonest": min((p["stockout_day"] for p in urgent), default=None),
            "order_now_count": order_now,
            "expiry_value": round(expiry_val, 0),
            "inventory_value": round(inv_value, 0),
            "dead_stock_value": round(dead, 0),
            "horizon": HORIZON,
        }

    def sku_list(self, product: str | None = None) -> list[dict]:
        out = []
        for c in self._codes(product):
            p = self.project(c)
            rec = self.recommend(c)
            status = "critical" if p["stockout_day"] is not None and p["stockout_day"] <= (PROFILE.get(c, {}).get("lead", 21)) \
                else "warning" if p["stockout_day"] is not None or p["expiry_qty"] > 0 \
                else "good"
            out.append({"code": c, "name": p["name"], "unit": p["unit"], "days_cover": p["days_cover"],
                        "on_hand": p["on_hand"], "stockout_day": p["stockout_day"],
                        "expiry_value": p["expiry_value"], "status": status,
                        "action": rec["action"] if rec else None})
        order = {"critical": 0, "warning": 1, "good": 2}
        return sorted(out, key=lambda s: (order[s["status"]], s["days_cover"]))

    def forecast_series(self, fg: str) -> dict:
        fc = self.fg_fc.get(fg)
        if not fc:
            return {}
        hist = self.fg_hist[fg]
        return {
            "history": [{"d": self.dates[i].isoformat(), "y": round(float(hist[i]), 1)}
                        for i in range(0, HISTORY_DAYS, 3)],
            "forecast": [{"d": self.future[i].isoformat(), "y": round(float(fc["mean"][i]), 1),
                          "lo": round(float(max(0, fc["mean"][i] - fc["band"])), 1),
                          "hi": round(float(fc["mean"][i] + fc["band"]), 1)} for i in range(HORIZON)],
            "name": self.prods.get(fg, {}).get("name", fg),
        }


def prods_by_id(prods: dict, pid: int) -> str:
    for code, p in prods.items():
        if p["id"] == pid:
            return code
    return str(pid)


VERA = Vera()


def reseed(seed: int = 42):
    global VERA
    VERA = Vera(seed)
