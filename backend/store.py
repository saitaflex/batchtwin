"""
Persistence + GMP domain logic for BatchTwin.

Everything that matters for compliance lives here:
  * append-only, hash-chained audit trail (tamper-evident -> ALCOA+ / 21 CFR Part 11)
  * electronic signatures bound to a role, a meaning, and a record hash
  * the four-part Dossier de Lot lifecycle with role-gated release
  * live mass-balance (real consumption incl. losses) and SPC fill-check data

SQLite is used deliberately: one file, zero setup, transactional -> perfect for a
demo that must "just run", while still being a real relational store.
"""
from __future__ import annotations
import json
import sqlite3
import hashlib
import datetime as _dt
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).with_name("batchtwin.db")

# --- GMP roles. Release is gated: only QA can libere, and only if the rest is done.
# Real Medicka signatory roles (from the actual DFA/DCO/DCT dossiers):
# R. PROD = Responsable Production, R. CQ = Responsable Controle Qualite,
# SMQ = Systeme Management Qualite (Assurance Qualite), PRT = Pharmacien Responsable Technique.
ROLES = {
    "r_prod": "R. PROD — Responsable Production",
    "r_cq":   "R. CQ — Responsable Controle Qualite",
    "smq":    "SMQ — Assurance Qualite",
    "prt":    "PRT — Pharmacien Responsable Technique",
}

STAGES = ["fabrication", "conditionnement", "qualite", "liberation"]
STAGE_SIGNER = {           # which role is allowed to sign off each dossier section
    "fabrication":     "r_prod",   # DFA — Dossier de Fabrication
    "conditionnement": "r_prod",   # DCO — Dossier de Conditionnement (primaire/secondaire)
    "qualite":         "r_cq",     # DCT — Dossier de Controle
    "liberation":      "prt",      # Liberation — Pharmacien Responsable Technique
}


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


_TABLES = ["audit", "signature", "form_entry", "bom_change", "energy", "qc_sample",
           "dispense", "checklist", "stage", "batch"]

# --- Formula change control (who may touch the recipe, and how far) -----------
# GMP reality: the formula is a registered document. Production may adjust a
# quantity inside the registered range; anything else is a DEVIATION and needs
# Quality Assurance. Control (R. CQ) checks the product, it never reformulates it.
QA_ROLES = {"smq", "prt"}          # may approve a change (and self-approve their own)
CHANGE_REQUESTERS = {"r_prod"} | QA_ROLES
MINOR_TOLERANCE_PCT = 5.0          # +/- 5 % on an existing line = in-range adjustment

# Instrumented workstations per dossier (rated power kW) — what the IoT clamps meter.
MACHINES = {
    "fabrication":     [("Cuve de melange & agitation", 12.0), ("Chauffe / homogeneisation", 6.0)],
    "conditionnement": [("Ligne de remplissage liquide & bouchage", 8.0), ("Etiqueteuse / etuyeuse", 1.6)],
    "qualite":         [("Instruments laboratoire", 1.5)],
    "liberation":      [],  # office review, negligible
}


def init_db(reset: bool = False) -> None:
    with _conn() as c:
        if reset:
            # Drop tables rather than unlink the file: unlink fails on Windows
            # while any connection holds the DB open (WinError 32).
            for t in _TABLES:
                c.execute(f"DROP TABLE IF EXISTS {t}")
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS batch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_name TEXT NOT NULL,
                product TEXT NOT NULL,
                qty_target INTEGER NOT NULL,
                of_ref TEXT, oc_ref TEXT, sale_order TEXT,
                target_fill_g REAL, fill_tol_g REAL, fill_unit TEXT DEFAULT 'mL',
                good_units INTEGER, mfg_date TEXT, expiry_date TEXT,
                state TEXT NOT NULL DEFAULT 'open',   -- open | released | rejected
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                name TEXT NOT NULL,                    -- one of STAGES
                status TEXT NOT NULL DEFAULT 'pending',-- pending | in_progress | signed
                UNIQUE(batch_id, name)
            );
            CREATE TABLE IF NOT EXISTS checklist (   -- vide de ligne / line clearance
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                label TEXT NOT NULL,
                ok INTEGER,                            -- NULL unchecked, 0 fail, 1 pass
                note TEXT,
                escalated_to TEXT
            );
            CREATE TABLE IF NOT EXISTS dispense (    -- pesee + mass balance
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                material TEXT NOT NULL,
                unit TEXT NOT NULL,
                qty_target REAL NOT NULL,
                qty_dispensed REAL,                    -- into the product
                qty_loss REAL DEFAULT 0,               -- to air / drip / spill
                unit_cost REAL DEFAULT 0,
                supplier TEXT, rm_lot TEXT, rm_expiry TEXT,
                at TEXT
            );
            CREATE TABLE IF NOT EXISTS qc_sample (   -- 10 flacons / 30 min contenance
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                taken_at TEXT NOT NULL,
                measurements TEXT NOT NULL,            -- json list of 10 fill weights
                mean REAL, rng REAL, verdict TEXT
            );
            CREATE TABLE IF NOT EXISTS energy (     -- kWh per stage, from IoT or estimate
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                stage TEXT NOT NULL,
                machine TEXT NOT NULL,
                kwh REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'iot',    -- iot | estimate | manual
                at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS form_entry (  -- digitalised dossier fields
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                doc_key TEXT NOT NULL,                -- DFA | DCOI | DCOII | DCT
                field_key TEXT NOT NULL,              -- t3.r1.c2 (+ #n for added rows)
                value TEXT,
                user TEXT NOT NULL, at TEXT NOT NULL,
                UNIQUE(batch_id, doc_key, field_key)
            );
            CREATE TABLE IF NOT EXISTS bom_change (  -- formula change control (deviation)
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                kind TEXT NOT NULL,                   -- add | amend | remove
                dispense_id INTEGER,                  -- line touched (NULL until an 'add' is applied)
                material TEXT NOT NULL,
                unit TEXT, unit_cost REAL DEFAULT 0,
                supplier TEXT, rm_lot TEXT, rm_expiry TEXT,
                old_qty REAL, new_qty REAL, delta_pct REAL,
                reason TEXT NOT NULL,
                requested_by TEXT NOT NULL, requested_role TEXT NOT NULL, requested_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- pending | approved | rejected
                route TEXT NOT NULL DEFAULT 'qa',       -- qa | minor (in-range, self-approved)
                decided_by TEXT, decided_role TEXT, decided_at TEXT, decision_note TEXT
            );
            CREATE TABLE IF NOT EXISTS signature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                stage TEXT NOT NULL,
                user TEXT NOT NULL, role TEXT NOT NULL,
                meaning TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                signed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (       -- append-only, hash-chained
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER,
                at TEXT NOT NULL,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL
            );
            """
        )


# ----------------------------------------------------------------------------
# Tamper-evident audit trail
# ----------------------------------------------------------------------------
GENESIS = "0" * 64


def _last_hash(c: sqlite3.Connection) -> str:
    row = c.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    return row["hash"] if row else GENESIS


def audit(c: sqlite3.Connection, user: str, action: str,
          detail: dict | None = None, batch_id: int | None = None) -> str:
    prev = _last_hash(c)
    at = _now()
    payload = json.dumps(detail or {}, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(
        f"{prev}|{at}|{user}|{action}|{payload}|{batch_id}".encode("utf-8")
    ).hexdigest()
    c.execute(
        "INSERT INTO audit(batch_id, at, user, action, detail, prev_hash, hash)"
        " VALUES(?,?,?,?,?,?,?)",
        (batch_id, at, user, action, payload, prev, digest),
    )
    return digest


def verify_chain() -> dict:
    """Recompute the whole chain. Any altered/deleted row breaks it -> proof of
    tamper-evidence for the pitch."""
    with _conn() as c:
        rows = c.execute("SELECT * FROM audit ORDER BY id").fetchall()
    prev = GENESIS
    for r in rows:
        recomputed = hashlib.sha256(
            f"{prev}|{r['at']}|{r['user']}|{r['action']}|{r['detail']}|{r['batch_id']}"
            .encode("utf-8")
        ).hexdigest()
        if recomputed != r["hash"] or r["prev_hash"] != prev:
            return {"valid": False, "broken_at": r["id"], "entries": len(rows)}
        prev = r["hash"]
    return {"valid": True, "entries": len(rows), "head": prev}


# ----------------------------------------------------------------------------
# Dossier de Lot lifecycle
# ----------------------------------------------------------------------------
DEFAULT_CHECKLIST = [
    "Zone de production vide du lot precedent",
    "Zone et equipements propres (nettoyage valide)",
    "Machine de remplissage operationnelle",
    "Cartons de matiere premiere sortis de la zone (securite)",
    "Documentation du lot presente et conforme",
]


def build_workflow_summary(batch: dict, stages: list[dict], signatures: list[dict], qc_samples: list[dict]) -> dict:
    stage_status = {s.get("name"): s.get("status") for s in stages}
    signed_count = sum(1 for s in stages if s.get("status") == "signed")
    qc_fail = sum(1 for s in qc_samples if s.get("verdict") == "FAIL")
    has_release = stage_status.get("liberation") == "signed"

    if batch.get("state") == "released" or has_release:
        status = "released"
        headline = "Release complete"
        notifications = ["Release complete", "The dossier is fully signed and ready for archive."]
    elif qc_fail:
        status = "quality_review"
        headline = "Quality review required"
        notifications = ["Quality review required", f"{qc_fail} quality check(s) failed and blocked release."]
    elif signed_count >= len(stages):
        status = "approved"
        headline = "Approval ready"
        notifications = ["Approval ready", "All stages are signed and only final release remains."]
    elif signed_count > 0:
        status = "in_production"
        headline = "In production"
        notifications = ["In production", "The batch is moving through production and quality review."]
    else:
        status = "draft"
        headline = "Draft dossier"
        notifications = ["Draft dossier", "Start line clearance and weigh-in to begin the batch record."]

    pending = [s.get("name") for s in stages if s.get("status") != "signed"]
    if pending:
        notifications.append("Next: " + ", ".join(pending))
    if signatures:
        notifications.append("Electronic signatures recorded")

    return {
        "status": status,
        "headline": headline,
        "progress": int(round(100 * signed_count / max(1, len(stages)), 0)),
        "notifications": notifications,
        "signed_count": signed_count,
        "pending_stages": pending,
        "quality_failures": qc_fail,
    }


def create_batch_from_odoo(odoo, of_id: int, oc_id: int, user: str) -> int:
    of = odoo.read("mrp.production", [of_id],
                   ["name", "product_id", "product_qty", "bom_id", "lot_id",
                    "sale_order", "target_fill_g", "fill_tolerance_g", "fill_unit"])[0]
    oc = odoo.read("mrp.production", [oc_id], ["name", "bom_id"])[0]
    lot_name = of["lot_id"][1] if of.get("lot_id") else of["name"]
    product = of["product_id"][1]
    today = _dt.date.today()
    fg_shelf = 900 if any(x in product for x in ("Spiruline", "Gelules", "Gélules", "capsule")) else 730
    mfg_date = today.isoformat()
    expiry_date = (today + _dt.timedelta(days=fg_shelf)).isoformat()

    with _conn() as c:
        cur = c.execute(
            "INSERT INTO batch(lot_name, product, qty_target, of_ref, oc_ref,"
            " sale_order, target_fill_g, fill_tol_g, fill_unit, mfg_date, expiry_date, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (lot_name, product, of["product_qty"], of["name"], oc["name"],
             of.get("sale_order"), of.get("target_fill_g"),
             of.get("fill_tolerance_g"), of.get("fill_unit") or "mL", mfg_date, expiry_date, _now()),
        )
        batch_id = cur.lastrowid
        for s in STAGES:
            c.execute("INSERT INTO stage(batch_id, name) VALUES(?,?)", (batch_id, s))
        for label in DEFAULT_CHECKLIST:
            c.execute("INSERT INTO checklist(batch_id, label) VALUES(?,?)",
                      (batch_id, label))
        _seed_dispense(c, odoo, batch_id, of["bom_id"][0])
        _seed_dispense(c, odoo, batch_id, oc["bom_id"][0])
        audit(c, user, "batch.create",
              {"lot": lot_name, "of": of["name"], "oc": oc["name"]}, batch_id)
    return batch_id


def _seed_dispense(c, odoo, batch_id, bom_id):
    from .inventory import PROFILE
    bom = odoo.read("mrp.bom", [bom_id], ["bom_line_ids"])[0]
    today = _dt.date.today()
    for line in odoo.read("mrp.bom.line", bom["bom_line_ids"],
                          ["product_id", "product_qty", "uom"]):
        pid = line["product_id"][0]
        prod = odoo.read("product.product", [pid], ["name", "standard_price", "default_code"])[0]
        code = prod.get("default_code") or ""
        prof = PROFILE.get(code, {})
        supplier = prof.get("sup", "—")
        shelf = prof.get("shelf", 730)
        rm_lot = f"{code}-{today.strftime('%y%m%d')}"
        rm_expiry = (today + _dt.timedelta(days=shelf)).isoformat()
        c.execute(
            "INSERT INTO dispense(batch_id, material, unit, qty_target, unit_cost,"
            " supplier, rm_lot, rm_expiry) VALUES(?,?,?,?,?,?,?,?)",
            (batch_id, prod["name"], line["uom"], line["product_qty"],
             prod.get("standard_price") or 0, supplier, rm_lot, rm_expiry),
        )


# ----------------------------------------------------------------------------
# Digitalised dossier forms (the .docx rendered as fillable fields)
# ----------------------------------------------------------------------------
def get_form_values(batch_id: int, doc_key: str) -> dict[str, str]:
    with _conn() as c:
        return {r["field_key"]: r["value"] for r in c.execute(
            "SELECT field_key, value FROM form_entry WHERE batch_id=? AND doc_key=?",
            (batch_id, doc_key))}


def save_form_field(batch_id: int, doc_key: str, field_key: str, value: str,
                    user: str, role: str) -> dict:
    """One field, one audit line. The stage the document belongs to must not be
    signed yet -- a signed dossier section is a closed record."""
    from .docx_forms import stage_of
    stage = stage_of(doc_key)
    with _conn() as c:
        r = c.execute("SELECT status FROM stage WHERE batch_id=? AND name=?",
                      (batch_id, stage)).fetchone()
        if r and r["status"] == "signed":
            raise PermissionError(
                f"{doc_key}: section '{stage}' deja signee, le document est clos")
        prev = c.execute("SELECT value FROM form_entry WHERE batch_id=? AND doc_key=?"
                         " AND field_key=?", (batch_id, doc_key, field_key)).fetchone()
        c.execute("INSERT INTO form_entry(batch_id, doc_key, field_key, value, user, at)"
                  " VALUES(?,?,?,?,?,?)"
                  " ON CONFLICT(batch_id, doc_key, field_key) DO UPDATE SET"
                  " value=excluded.value, user=excluded.user, at=excluded.at",
                  (batch_id, doc_key, field_key, value, user, _now()))
        # GMP: never silently overwrite -- a correction keeps the old value visible
        detail = {"doc": doc_key, "field": field_key, "value": value}
        if prev and prev["value"] not in (None, "", value):
            detail["was"] = prev["value"]
        audit(c, user, "form.correct" if "was" in detail else "form.fill", detail, batch_id)
    return {"ok": True, "field": field_key}


def form_progress(batch_id: int, forms: list[dict]) -> dict[str, dict]:
    """How much of each digital dossier is filled -- drives the completeness gauge."""
    out = {}
    with _conn() as c:
        for f in forms:
            n = c.execute("SELECT COUNT(*) n FROM form_entry WHERE batch_id=? AND doc_key=?"
                          " AND value IS NOT NULL AND value<>''",
                          (batch_id, f["doc_key"])).fetchone()["n"]
            total = f["field_count"] or 1
            out[f["doc_key"]] = {"filled": n, "total": total,
                                 "pct": round(min(n / total, 1.0) * 100)}
    return out


# ----------------------------------------------------------------------------
# Formula change control -- add / amend / remove a material under GMP rules
# ----------------------------------------------------------------------------
def _fab_signed(c, batch_id: int) -> bool:
    r = c.execute("SELECT status FROM stage WHERE batch_id=? AND name='fabrication'",
                  (batch_id,)).fetchone()
    return bool(r) and r["status"] == "signed"


def request_bom_change(batch_id: int, kind: str, user: str, role: str, reason: str,
                       dispense_id: int | None = None, material: str | None = None,
                       unit: str | None = None, unit_cost: float = 0.0,
                       supplier: str | None = None, rm_lot: str | None = None,
                       rm_expiry: str | None = None, new_qty: float | None = None) -> dict:
    """Ask to add / amend / remove a material line.

    Routing depends on *who* asks and *how big* the change is:
      * R. CQ (control) is refused outright -- it is not a manufacturing role.
      * R. PROD amending an existing line by <= +/-5 % -> 'minor', applied at once.
      * Anything else from R. PROD -> 'pending', waits for SMQ or PRT.
      * SMQ / PRT hold QA authority -> their own request is approved on the spot.
    A pending change blocks liberation. Nothing may change after fabrication
    is signed: the record is closed, a later change needs a new lot.
    """
    if kind not in ("add", "amend", "remove"):
        raise ValueError(f"unknown change kind {kind}")
    if role not in CHANGE_REQUESTERS:
        raise PermissionError(
            f"role '{role}' ne peut pas modifier la formule "
            f"(autorises: {', '.join(sorted(CHANGE_REQUESTERS))})")
    if not (reason or "").strip():
        raise ValueError("un motif est obligatoire pour toute modification de formule")

    with _conn() as c:
        if _fab_signed(c, batch_id):
            raise PermissionError(
                "fabrication deja signee: le dossier est clos, "
                "toute modification exige un nouveau lot")

        old_qty = None
        if kind in ("amend", "remove"):
            row = c.execute("SELECT material, unit, unit_cost, qty_target, supplier, rm_lot,"
                            " rm_expiry FROM dispense WHERE id=? AND batch_id=?",
                            (dispense_id, batch_id)).fetchone()
            if not row:
                raise ValueError("ligne matiere introuvable")
            old_qty = row["qty_target"]
            material = row["material"]
            unit = row["unit"]
            unit_cost = row["unit_cost"] or 0.0
            supplier, rm_lot, rm_expiry = row["supplier"], row["rm_lot"], row["rm_expiry"]
            if kind == "remove":
                new_qty = 0.0
        else:
            if not (material or "").strip():
                raise ValueError("matiere obligatoire")
            if new_qty is None or new_qty <= 0:
                raise ValueError("quantite obligatoire et strictement positive")

        delta_pct = None
        if kind == "amend" and old_qty:
            delta_pct = abs(new_qty - old_qty) / old_qty * 100.0

        minor = (kind == "amend" and delta_pct is not None
                 and delta_pct <= MINOR_TOLERANCE_PCT)
        route = "minor" if minor else "qa"
        auto = minor or role in QA_ROLES
        status = "approved" if auto else "pending"

        cur = c.execute(
            "INSERT INTO bom_change(batch_id, kind, dispense_id, material, unit, unit_cost,"
            " supplier, rm_lot, rm_expiry, old_qty, new_qty, delta_pct, reason,"
            " requested_by, requested_role, requested_at, status, route,"
            " decided_by, decided_role, decided_at, decision_note)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (batch_id, kind, dispense_id, material, unit, unit_cost, supplier, rm_lot,
             rm_expiry, old_qty, new_qty, delta_pct, reason, user, role, _now(),
             status, route,
             user if auto else None, role if auto else None, _now() if auto else None,
             ("ajustement en plage +/-%.0f%%" % MINOR_TOLERANCE_PCT) if minor
             else ("autorite AQ" if auto else None)))
        change_id = cur.lastrowid

        audit(c, user, "bom.change.request",
              {"kind": kind, "material": material, "old": old_qty, "new": new_qty,
               "delta_pct": None if delta_pct is None else round(delta_pct, 2),
               "route": route, "status": status, "reason": reason}, batch_id)

        if auto:
            _apply_bom_change(c, change_id, user)
        return {"change_id": change_id, "status": status, "route": route,
                "delta_pct": delta_pct}


def decide_bom_change(change_id: int, user: str, role: str, approve: bool,
                      note: str = "") -> dict:
    """SMQ / PRT accept or refuse a pending formula change."""
    if role not in QA_ROLES:
        raise PermissionError(
            f"role '{role}' ne peut pas approuver une modification de formule "
            f"(reserve a {', '.join(sorted(QA_ROLES))})")
    with _conn() as c:
        ch = c.execute("SELECT * FROM bom_change WHERE id=?", (change_id,)).fetchone()
        if not ch:
            raise ValueError("modification introuvable")
        if ch["status"] != "pending":
            raise ValueError(f"modification deja {ch['status']}")
        if approve and ch["requested_by"] == user:
            raise PermissionError("separation des taches: on ne peut pas approuver sa propre demande")
        status = "approved" if approve else "rejected"
        c.execute("UPDATE bom_change SET status=?, decided_by=?, decided_role=?,"
                  " decided_at=?, decision_note=? WHERE id=?",
                  (status, user, role, _now(), note, change_id))
        audit(c, user, "bom.change." + status,
              {"change": change_id, "material": ch["material"], "note": note},
              ch["batch_id"])
        if approve:
            _apply_bom_change(c, change_id, user)
        return {"change_id": change_id, "status": status}


def _apply_bom_change(c, change_id: int, user: str) -> None:
    """Write an approved change into the live dispense table."""
    ch = c.execute("SELECT * FROM bom_change WHERE id=?", (change_id,)).fetchone()
    bid = ch["batch_id"]
    if ch["kind"] == "add":
        cur = c.execute(
            "INSERT INTO dispense(batch_id, material, unit, qty_target, unit_cost,"
            " supplier, rm_lot, rm_expiry) VALUES(?,?,?,?,?,?,?,?)",
            (bid, ch["material"], ch["unit"] or "kg", ch["new_qty"], ch["unit_cost"] or 0,
             ch["supplier"], ch["rm_lot"], ch["rm_expiry"]))
        c.execute("UPDATE bom_change SET dispense_id=? WHERE id=?", (cur.lastrowid, change_id))
    elif ch["kind"] == "amend":
        c.execute("UPDATE dispense SET qty_target=? WHERE id=?", (ch["new_qty"], ch["dispense_id"]))
    elif ch["kind"] == "remove":
        c.execute("DELETE FROM dispense WHERE id=?", (ch["dispense_id"],))
    audit(c, user, "bom.change.applied",
          {"kind": ch["kind"], "material": ch["material"], "new": ch["new_qty"]}, bid)


def list_bom_changes(batch_id: int) -> list[dict]:
    with _conn() as c:
        return _rows(c, "SELECT * FROM bom_change WHERE batch_id=? ORDER BY id DESC", batch_id)


def material_catalog(odoo) -> list[dict]:
    """Approved raw-material / packaging catalog straight from Odoo.
    You may only add what Quality has already qualified -- no free text."""
    prods = odoo.search_read("product.product", [("type", "=", "product")],
                             ["name", "default_code", "uom_name", "standard_price"])
    from .inventory import PROFILE
    out = []
    for p in prods:
        code = p.get("default_code") or ""
        if not (code.startswith("RM-") or code.startswith("PK-")):
            continue   # finished goods are not ingredients
        prof = PROFILE.get(code, {})
        out.append({"code": code, "name": p["name"],
                    "unit": "kg" if code.startswith("RM-") else "Unit",
                    "unit_cost": p.get("standard_price") or 0,
                    "supplier": prof.get("sup", "—"),
                    "shelf_days": prof.get("shelf", 730)})
    return sorted(out, key=lambda x: x["name"])


def _stage_hash(c, batch_id: int, stage: str) -> str:
    """Hash the current content of a stage -> what the signature attests to."""
    parts = [f"batch:{batch_id}", f"stage:{stage}"]
    if stage == "fabrication":
        for r in c.execute("SELECT material, qty_target, qty_dispensed, qty_loss"
                           " FROM dispense WHERE batch_id=? ORDER BY id", (batch_id,)):
            parts.append(f"{r['material']}:{r['qty_dispensed']}:{r['qty_loss']}")
        for r in c.execute("SELECT label, ok FROM checklist WHERE batch_id=? ORDER BY id",
                           (batch_id,)):
            parts.append(f"{r['label']}:{r['ok']}")
        # an approved formula change is part of what the signature attests to
        for r in c.execute("SELECT kind, material, new_qty, status FROM bom_change"
                           " WHERE batch_id=? ORDER BY id", (batch_id,)):
            parts.append(f"chg:{r['kind']}:{r['material']}:{r['new_qty']}:{r['status']}")
    elif stage == "qualite":
        for r in c.execute("SELECT taken_at, mean, verdict FROM qc_sample"
                           " WHERE batch_id=? ORDER BY id", (batch_id,)):
            parts.append(f"{r['taken_at']}:{r['mean']}:{r['verdict']}")
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def sign_stage(batch_id: int, stage: str, user: str, role: str, meaning: str) -> dict:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage}")
    if STAGE_SIGNER[stage] != role:
        raise PermissionError(
            f"role '{role}' cannot sign '{stage}' (requires '{STAGE_SIGNER[stage]}')")
    with _conn() as c:
        _guard_release(c, batch_id, stage)
        h = _stage_hash(c, batch_id, stage)
        c.execute(
            "INSERT INTO signature(batch_id, stage, user, role, meaning, record_hash, signed_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (batch_id, stage, user, role, meaning, h, _now()))
        c.execute("UPDATE stage SET status='signed' WHERE batch_id=? AND name=?",
                  (batch_id, stage))
        audit(c, user, "stage.sign",
              {"stage": stage, "role": role, "meaning": meaning, "hash": h}, batch_id)
        if stage == "liberation":
            c.execute("UPDATE batch SET state='released' WHERE id=?", (batch_id,))
            audit(c, user, "batch.release", {"lot": _lot(c, batch_id)}, batch_id)
    return {"stage": stage, "record_hash": h}


def _guard_release(c, batch_id, stage):
    """Liberation cannot be signed until the other three stages are signed and
    QC verdict is PASS. This is the core compliance gate."""
    if stage != "liberation":
        return
    open_chg = c.execute("SELECT COUNT(*) n FROM bom_change WHERE batch_id=? AND status='pending'",
                         (batch_id,)).fetchone()["n"]
    if open_chg:
        raise PermissionError(
            f"liberation bloquee: {open_chg} modification(s) de formule en attente d'approbation AQ")
    signed = {r["name"] for r in c.execute(
        "SELECT name FROM stage WHERE batch_id=? AND status='signed'", (batch_id,))}
    missing = [s for s in ("fabrication", "conditionnement", "qualite") if s not in signed]
    if missing:
        raise PermissionError(f"liberation bloquee: etapes non signees {missing}")
    fails = c.execute("SELECT COUNT(*) n FROM qc_sample WHERE batch_id=? AND verdict='FAIL'",
                      (batch_id,)).fetchone()["n"]
    if fails:
        raise PermissionError(f"liberation bloquee: {fails} controle(s) contenance hors tolerance")


def _lot(c, batch_id):
    r = c.execute("SELECT lot_name FROM batch WHERE id=?", (batch_id,)).fetchone()
    return r["lot_name"] if r else None


# ----------------------------------------------------------------------------
# Data access (all SQL lives here; the API layer stays thin)
# ----------------------------------------------------------------------------
def _rows(c, q, *a):
    return [dict(r) for r in c.execute(q, a).fetchall()]


def list_batches() -> list[dict]:
    with _conn() as c:
        return _rows(c, "SELECT id, lot_name, product, qty_target, state,"
                        " of_ref, oc_ref, created_at FROM batch ORDER BY id ASC")


def get_batch(batch_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM batch WHERE id=?", (batch_id,)).fetchone()
        if not r:
            return None
        b = dict(r)
        b["stages"] = _rows(c, "SELECT name, status FROM stage WHERE batch_id=? ORDER BY id", batch_id)
        b["checklist"] = _rows(c, "SELECT id, label, ok, note, escalated_to"
                                  " FROM checklist WHERE batch_id=? ORDER BY id", batch_id)
        b["dispense"] = _rows(c, "SELECT * FROM dispense WHERE batch_id=? ORDER BY id", batch_id)
        b["qc"] = _rows(c, "SELECT * FROM qc_sample WHERE batch_id=? ORDER BY id", batch_id)
        b["signatures"] = _rows(c, "SELECT stage, user, role, meaning, record_hash, signed_at"
                                   " FROM signature WHERE batch_id=? ORDER BY id", batch_id)
        b["energy"] = _rows(c, "SELECT stage, machine, kwh, source, at FROM energy"
                               " WHERE batch_id=? ORDER BY id", batch_id)
        b["changes"] = _rows(c, "SELECT * FROM bom_change WHERE batch_id=? ORDER BY id DESC",
                             batch_id)
        b["changes_pending"] = sum(1 for x in b["changes"] if x["status"] == "pending")
        b["workflow"] = build_workflow_summary(b, b["stages"], b["signatures"], b["qc"])
        return b


def update_checklist(item_id: int, ok: int, note: str, user: str,
                     escalate_to: str | None) -> None:
    with _conn() as c:
        c.execute("UPDATE checklist SET ok=?, note=?, escalated_to=? WHERE id=?",
                  (ok, note, escalate_to, item_id))
        row = c.execute("SELECT batch_id, label FROM checklist WHERE id=?", (item_id,)).fetchone()
        audit(c, user, "checklist.update",
              {"item": row["label"], "ok": bool(ok), "escalated_to": escalate_to},
              row["batch_id"])


def record_dispense(line_id: int, dispensed: float, loss: float, user: str) -> None:
    with _conn() as c:
        row = c.execute("SELECT batch_id, material, qty_target FROM dispense WHERE id=?",
                        (line_id,)).fetchone()
        c.execute("UPDATE dispense SET qty_dispensed=?, qty_loss=?, at=? WHERE id=?",
                  (dispensed, loss, _now(), line_id))
        audit(c, user, "dispense.record",
              {"material": row["material"], "target": row["qty_target"],
               "dispensed": dispensed, "loss": loss}, row["batch_id"])


def add_qc_sample(batch_id: int, measurements: list[float], user: str) -> dict:
    b = get_batch(batch_id)
    lo = (b["target_fill_g"] or 0) - (b["fill_tol_g"] or 0)
    hi = (b["target_fill_g"] or 0) + (b["fill_tol_g"] or 0)
    mean = sum(measurements) / len(measurements)
    rng = max(measurements) - min(measurements)
    verdict = "PASS" if all(lo <= m <= hi for m in measurements) else "FAIL"
    with _conn() as c:
        c.execute("INSERT INTO qc_sample(batch_id, taken_at, measurements, mean, rng, verdict)"
                  " VALUES(?,?,?,?,?,?)",
                  (batch_id, _now(), json.dumps(measurements), mean, rng, verdict))
        audit(c, user, "qc.sample",
              {"n": len(measurements), "mean": round(mean, 2), "verdict": verdict}, batch_id)
    return {"mean": round(mean, 2), "range": round(rng, 2), "verdict": verdict}


def set_good_units(batch_id: int, units: int, user: str) -> None:
    with _conn() as c:
        c.execute("UPDATE batch SET good_units=? WHERE id=?", (units, batch_id))
        audit(c, user, "conditionnement.count", {"good_units": units}, batch_id)


def record_energy(batch_id: int, stage: str, machine: str, kwh: float,
                  source: str, user: str) -> None:
    with _conn() as c:
        c.execute("INSERT INTO energy(batch_id, stage, machine, kwh, source, at)"
                  " VALUES(?,?,?,?,?,?)", (batch_id, stage, machine, kwh, source, _now()))
        audit(c, user, "energy.reading",
              {"stage": stage, "machine": machine, "kwh": round(kwh, 3), "source": source}, batch_id)


def simulate_energy(batch_id: int, user: str) -> int:
    """Populate realistic per-machine energy for the batch, as if IoT clamps had
    metered each workstation for the batch run. Returns number of readings."""
    import random
    b = get_batch(batch_id)
    units = b["qty_target"] or 500
    # rough run hours scaled to batch size
    hours = {"fabrication": 1.2, "conditionnement": units / 300.0, "qualite": 0.8, "liberation": 0.0}
    n = 0
    with _conn() as c:
        c.execute("DELETE FROM energy WHERE batch_id=?", (batch_id,))
    for stage, machines in MACHINES.items():
        for name, kw in machines:
            load = random.uniform(0.55, 0.8)   # machines rarely run at nameplate
            kwh = round(kw * hours[stage] * load, 2)
            if kwh > 0:
                record_energy(batch_id, stage, name, kwh, "iot", user)
                n += 1
    return n


def get_audit(batch_id: int | None = None) -> list[dict]:
    with _conn() as c:
        if batch_id:
            return _rows(c, "SELECT * FROM audit WHERE batch_id=? ORDER BY id", batch_id)
        return _rows(c, "SELECT * FROM audit ORDER BY id")


# --- demo-only: prove tamper-evidence live -----------------------------------
def demo_tamper(audit_id: int) -> dict:
    """Overwrite an audit row's payload WITHOUT re-hashing (simulating someone
    editing the database directly). verify_chain() will then flag it."""
    with _conn() as c:
        r = c.execute("SELECT detail FROM audit WHERE id=?", (audit_id,)).fetchone()
        if not r:
            return {"ok": False}
        c.execute("UPDATE audit SET detail=? WHERE id=?",
                  (json.dumps({"_forged": True}), audit_id))
    return {"ok": True, "tampered_id": audit_id}

