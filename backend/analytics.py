"""
Numbers that turn the paper dossier into intelligence.

  mass_balance() : theoretical BOM vs. what was really consumed (incl. losses to
                   air / drip). Yields the TRUE material cost and a loss KPI Odoo
                   never sees.
  spc()          : X-bar / R control chart on the 10-flacon contenance samples,
                   with Western Electric rule checks and a short-horizon drift
                   forecast -> catch underfill before it becomes scrap.
"""
from __future__ import annotations
import json
import statistics as st

# d2 / D3 / D4 SPC constants for subgroup size n=10 (standard control-chart tables)
_D2, _D3, _D4 = 3.078, 0.223, 1.777


def mass_balance(rows: list[dict]) -> dict:
    lines, theo_cost, real_cost, loss_cost = [], 0.0, 0.0, 0.0
    for r in rows:
        target = r["qty_target"] or 0
        disp = r["qty_dispensed"]
        loss = r["qty_loss"] or 0
        cost = r["unit_cost"] or 0
        consumed = (disp + loss) if disp is not None else None
        variance = None if disp is None else round(disp - target, 4)
        loss_pct = None
        if disp is not None and consumed:
            loss_pct = round(100 * loss / consumed, 2)
        theo_cost += target * cost
        if consumed is not None:
            real_cost += consumed * cost
            loss_cost += loss * cost
        lines.append({
            "material": r["material"], "unit": r["unit"],
            "target": target, "dispensed": disp, "loss": loss,
            "consumed": consumed, "variance": variance,
            "loss_pct": loss_pct, "unit_cost": cost,
            "line_cost": None if consumed is None else round(consumed * cost, 2),
        })
    done = all(l["dispensed"] is not None for l in lines) and bool(lines)
    return {
        "lines": lines,
        "theoretical_cost": round(theo_cost, 2),
        "real_cost": round(real_cost, 2) if done else None,
        "loss_cost": round(loss_cost, 2) if done else None,
        "cost_gap": round(real_cost - theo_cost, 2) if done else None,
        "complete": done,
    }


def batch_kpis(batch: dict, mb: dict, good_units: int | None) -> dict:
    target_units = batch["qty_target"] or 0
    yield_pct = None
    if good_units is not None and target_units:
        yield_pct = round(100 * good_units / target_units, 1)
    unit_cost = None
    if mb["real_cost"] is not None and good_units:
        unit_cost = round(mb["real_cost"] / good_units, 3)
    return {
        "target_units": target_units,
        "good_units": good_units,
        "yield_pct": yield_pct,
        "true_unit_material_cost": unit_cost,
    }


# Grid emission factor (kg CO2e per kWh). Default ~ mixed EU/North-Africa grid;
# configurable per site. Sources: national grid factors, e.g. ~0.05 (FR) .. ~0.5 (TN).
CO2_KG_PER_KWH = 0.40


def energy_summary(rows: list[dict], good_units: int | None,
                   co2_factor: float = CO2_KG_PER_KWH) -> dict:
    stages = {}
    total_kwh = 0.0
    for r in rows:
        s = stages.setdefault(r["stage"], {"kwh": 0.0, "machines": []})
        s["kwh"] += r["kwh"]
        s["machines"].append({"machine": r["machine"], "kwh": round(r["kwh"], 2), "source": r["source"]})
        total_kwh += r["kwh"]
    per_stage = [{"stage": st, "kwh": round(v["kwh"], 2),
                  "co2_kg": round(v["kwh"] * co2_factor, 3),
                  "machines": v["machines"]} for st, v in stages.items()]
    total_co2 = total_kwh * co2_factor
    unit = good_units or None
    return {
        "per_stage": per_stage,
        "total_kwh": round(total_kwh, 2),
        "total_co2_kg": round(total_co2, 2),
        "kwh_per_unit": round(total_kwh / unit, 4) if unit else None,
        "co2_g_per_unit": round(total_co2 * 1000 / unit, 1) if unit else None,
        "co2_factor": co2_factor,
        "complete": total_kwh > 0,
    }


def spc(samples: list[dict], norm: float, tol_min: float, tol_max: float) -> dict:
    points = []
    for s in samples:
        vals = json.loads(s["measurements"])
        points.append({
            "at": s["taken_at"], "mean": round(st.mean(vals), 2),
            "range": round(max(vals) - min(vals), 2),
            "verdict": s["verdict"], "n": len(vals),
        })
    out = {"points": points, "norm": norm, "usl": tol_max, "lsl": tol_min,
           "control_limits": None, "signals": [], "forecast": None}
    if len(points) < 2:
        return out

    xbar = st.mean(p["mean"] for p in points)
    rbar = st.mean(p["range"] for p in points)
    sigma_hat = rbar / _D2 if rbar else 0
    out["control_limits"] = {
        "x_center": round(xbar, 2),
        "x_ucl": round(xbar + 3 * sigma_hat / (10 ** 0.5) * (10 ** 0.5), 2),  # 3-sigma on subgroup mean
        "x_lcl": round(xbar - 3 * sigma_hat / (10 ** 0.5) * (10 ** 0.5), 2),
        "r_center": round(rbar, 2),
        "r_ucl": round(_D4 * rbar, 2), "r_lcl": round(_D3 * rbar, 2),
        "sigma_hat": round(sigma_hat, 3),
    }
    ucl = out["control_limits"]["x_ucl"]
    lcl = out["control_limits"]["x_lcl"]

    # Western Electric rules (subset): point outside 3-sigma; 2/3 beyond 2-sigma;
    # 6-point monotonic trend (drift).
    means = [p["mean"] for p in points]
    two_sig_hi = xbar + 2 * sigma_hat
    two_sig_lo = xbar - 2 * sigma_hat
    for i, m in enumerate(means):
        if m > ucl or m < lcl:
            out["signals"].append({"idx": i, "rule": "hors limite de controle (3 sigma)"})
        if i >= 2:
            trio = means[i - 2:i + 1]
            if sum(v > two_sig_hi for v in trio) >= 2 or sum(v < two_sig_lo for v in trio) >= 2:
                out["signals"].append({"idx": i, "rule": "2/3 points au-dela de 2 sigma"})
    if len(means) >= 6:
        tail = means[-6:]
        if all(x < y for x, y in zip(tail, tail[1:])) or all(x > y for x, y in zip(tail, tail[1:])):
            out["signals"].append({"idx": len(means) - 1, "rule": "derive: 6 points monotones"})

    # Simple linear drift forecast: when does the trend cross a spec limit?
    n = len(means)
    xs = list(range(n))
    mx, my = st.mean(xs), st.mean(means)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom:
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, means)) / denom
        intercept = my - slope * mx
        if abs(slope) > 1e-6:
            limit = tol_min if slope < 0 else tol_max
            cross = (limit - intercept) / slope
            steps = cross - (n - 1)
            if 0 < steps <= 20:
                out["forecast"] = {
                    "slope_g_per_sample": round(slope, 3),
                    "samples_to_spec_breach": round(steps, 1),
                    "minutes_to_spec_breach": round(steps * 30, 0),  # 1 sample / 30 min
                    "toward": "LSL (sous-remplissage)" if slope < 0 else "USL (sur-remplissage)",
                }
    return out
