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
import threading
import datetime as _dt
from pathlib import Path
from typing import Any

import os

from . import auth, anchor, products, industry

DB_PATH = Path(__file__).with_name("batchtwin.db")

# --- GMP roles. Release is gated: only QA can libere, and only if the rest is done.
# Real Medicka signatory roles (from the actual DFA/DCO/DCT dossiers):
# R. PROD = Responsable Production, R. CQ = Responsable Controle Qualite,
# SMQ = Systeme Management Qualite (Assurance Qualite), PRT = Pharmacien Responsable Technique.


# --- The lifecycle comes from the active INDUSTRY PROFILE, not from constants.
# The mechanics (staged record, role-gated signatures, mass balance, deviations)
# are the product; the vocabulary and the rulebook differ by sector. Adding an
# industry is writing a profile, not editing this engine.
PROFILE = industry.load(os.environ.get("BATCHTWIN_PROFILE"))
STAGES = industry.stage_names(PROFILE)
STAGE_SIGNER = industry.stage_signer(PROFILE)
STAGE_DOC = industry.stage_doc(PROFILE)
# Every stage before release must be signed for a lot to be released.
PREREQUISITE_STAGES = [s for s in STAGES if s != "liberation"]


def use_profile(key: str) -> dict:
    """Switch industry profile at runtime.

    Existing batches keep the stages they were created with -- a profile change
    must never rewrite a signed record. Only new batches follow the new profile.
    """
    global PROFILE, STAGES, STAGE_SIGNER, STAGE_DOC, PREREQUISITE_STAGES
    global ROLES, QA_ROLES, CHANGE_REQUESTERS, MINOR_TOLERANCE_PCT
    global DEFAULT_CHECKLIST, QUALIFICATION_LOTS, PACKAGING_VARIANCE_PCT
    PROFILE = industry.load(key)
    STAGES = industry.stage_names(PROFILE)
    STAGE_SIGNER = industry.stage_signer(PROFILE)
    STAGE_DOC = industry.stage_doc(PROFILE)
    PREREQUISITE_STAGES = [s for s in STAGES if s != "liberation"]
    ROLES = dict(PROFILE["roles"])
    QA_ROLES = set(PROFILE["qa_roles"])
    CHANGE_REQUESTERS = set(PROFILE.get("change_requesters") or []) | QA_ROLES
    MINOR_TOLERANCE_PCT = industry.rule(PROFILE, "minor_tolerance_pct", 5.0)
    PACKAGING_VARIANCE_PCT = industry.rule(PROFILE, "packaging_variance_pct", 1.0)
    QUALIFICATION_LOTS = industry.rule(PROFILE, "qualification_lots", 3)
    DEFAULT_CHECKLIST = list(PROFILE["checklist"])
    return PROFILE


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    """One tuned connection per operation.

    WAL lets readers run while a writer holds the DB, and busy_timeout makes a
    concurrent writer wait for the lock instead of raising 'database is locked'.
    Without these two, several operators signing at once produce hard errors.
    """
    c = sqlite3.connect(DB_PATH, timeout=30.0, isolation_level="DEFERRED")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA busy_timeout = 30000")
    c.execute("PRAGMA synchronous = NORMAL")
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _write_conn() -> sqlite3.Connection:
    """Connection for transactions that read-then-write.

    BEGIN IMMEDIATE takes the write lock up front, so two operators cannot both
    read the same state and then both write it (the classic lost update). Any
    audited mutation must use this, never _conn().
    """
    c = _conn()
    c.execute("BEGIN IMMEDIATE")
    return c


# Batch data: dropped by a demo reset.
_TABLES = ["audit", "signature", "form_entry", "bom_change", "deviation",
           "packaging_recon", "applied_op", "energy", "qc_sample", "dispense",
           "checklist", "stage", "batch", "product_nutrient", "product"]

# Identity: deliberately NOT dropped by a reset. Wiping the session table logs
# out the very person who triggered the reset -- including, on a demo, whoever
# is standing in front of a jury. Accounts and sessions outlive batch data.
_IDENTITY_TABLES = ["session", "app_user"]

# --- Offline capture -------------------------------------------------------
# A tablet on a shop floor loses Wi-Fi. Data capture is queued locally and
# replayed; SIGNATURES ARE NOT. Verifying a password offline would mean caching
# credentials on a shared device, and a signature that cannot check identity is
# not a signature (21 CFR 11.200). So: capture works offline, signing needs the
# network -- a deliberate limit, not an oversight.
OFFLINE_KINDS = {"form", "dispense", "qc", "checklist", "packaging", "units"}

# --- Formula change control (who may touch the recipe, and how far) -----------
# GMP reality: the formula is a registered document. Production may adjust a
# quantity inside the registered range; anything else is a DEVIATION and needs
# Quality Assurance. Control (R. CQ) checks the product, it never reformulates it.
ROLES = dict(PROFILE["roles"])
QA_ROLES = set(PROFILE["qa_roles"])            # may approve a change
CHANGE_REQUESTERS = set(PROFILE.get("change_requesters") or []) | QA_ROLES
MINOR_TOLERANCE_PCT = industry.rule(PROFILE, "minor_tolerance_pct", 5.0)
PACKAGING_VARIANCE_PCT = industry.rule(PROFILE, "packaging_variance_pct", 1.0)

# Instrumented workstations per dossier (rated power kW) — what the IoT clamps meter.
MACHINES = {
    "fabrication":     [("Cuve de melange & agitation", 12.0), ("Chauffe / homogeneisation", 6.0)],
    "cond_primaire":   [("Ligne de remplissage liquide & bouchage", 8.0)],
    "cond_secondaire": [("Etiqueteuse / etuyeuse", 1.6), ("Encaisseuse / palettiseur", 2.2)],
    "qualite":         [("Instruments laboratoire", 1.5)],
    "liberation":      [],  # office review, negligible
}


def init_db(reset: bool = False, purge_identity: bool = False) -> None:
    """Create the schema. `reset` clears BATCH data only.

    Accounts and sessions survive a reset on purpose -- see _IDENTITY_TABLES.
    `purge_identity` is for tests and a genuine teardown, never for the demo
    reset button.
    """
    with _conn() as c:
        if reset and purge_identity:
            for t in _IDENTITY_TABLES:
                c.execute(f"DROP TABLE IF EXISTS {t}")
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
                -- product_id points at ONE immutable product version, so a lot
                -- stays readable against the spec it was actually made to.
                product_id INTEGER REFERENCES product(id),
                product TEXT NOT NULL,
                qty_target INTEGER NOT NULL,
                of_ref TEXT, oc_ref TEXT, sale_order TEXT,
                target_fill_g REAL, fill_tol_g REAL, fill_unit TEXT DEFAULT 'mL',
                good_units INTEGER, mfg_date TEXT, expiry_date TEXT,
                state TEXT NOT NULL DEFAULT 'open',   -- open | released | rejected
                -- Migration: during a parallel run the PAPER dossier is the
                -- legal record and this one shadows it. Nothing digital may
                -- claim legal release until the product line is cut over.
                run_mode TEXT NOT NULL DEFAULT 'live', -- parallel | live
                paper_ref TEXT,
                -- The rulebook this lot was opened under. Repair and display use
                -- THIS profile, never the currently-active one: changing the
                -- industry profile must not rewrite a record already signed.
                profile_key TEXT,                        -- the paper dossier it shadows
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
            CREATE TABLE IF NOT EXISTS applied_op (  -- offline replay de-duplication
                op_id TEXT PRIMARY KEY,               -- client-generated UUID
                kind TEXT NOT NULL,
                batch_id INTEGER,
                client_at TEXT,                       -- when the operator actually acted
                applied_at TEXT NOT NULL,             -- when the server received it
                result TEXT
            );
            CREATE TABLE IF NOT EXISTS deviation (   -- GMP deviation / CAPA record
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                ref TEXT NOT NULL,                    -- DEV-<batch>-<n>
                kind TEXT NOT NULL,                   -- qc_fail | line_clearance | manual
                severity TEXT NOT NULL,               -- minor | major | critical
                title TEXT NOT NULL,
                detail TEXT,
                opened_by TEXT NOT NULL, opened_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',  -- open | closed
                disposition TEXT,                     -- accept | reject | rework
                root_cause TEXT, capa TEXT,
                closed_by TEXT, closed_role TEXT, closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS packaging_recon (  -- DCOI/DCOII article balance
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES batch(id),
                stage TEXT NOT NULL,                  -- cond_primaire | cond_secondaire
                code TEXT NOT NULL,                   -- CAPS005 / ALU001 / PVC001 / ET994 / CG005
                label TEXT NOT NULL,
                unit TEXT NOT NULL,
                issued REAL,                          -- bon d'approvisionnement
                used REAL,                            -- on product
                returned REAL,                        -- bon de retour
                waste REAL,                           -- bon de dechet
                at TEXT,
                UNIQUE(batch_id, code)
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
        auth.init_users(c)
        products.init(c)
        products.seed(c)


_ANCHOR_LOCK = threading.Lock()


def anchor_now() -> dict | None:
    """Publish the current chain head to the external append-only witness.

    Called after every audited transaction *commits* -- anchoring inside the
    transaction would publish a head that a rollback then erases.

    Serialised and monotonic: two threads that commit at nearly the same moment
    must not write their heads out of order, or the last line of the log would
    name a superseded state and every later verification would cry tamper.
    """
    with _ANCHOR_LOCK:
        with _conn() as c:
            row = c.execute("SELECT COUNT(*) n, MAX(id) m FROM audit").fetchone()
            if not row["n"]:
                return None
            head = c.execute("SELECT hash FROM audit WHERE id=?",
                             (row["m"],)).fetchone()["hash"]
        last = anchor.last_anchor()
        if last and row["n"] <= last["entries"]:
            return last          # a peer already anchored this state or newer
        return anchor.append(_now(), row["n"], head)


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
    """Two independent checks.

    1. Internal: recompute every link. Catches an edited or deleted row.
    2. External: compare the head against `audit_anchor.log`, which lives
       outside the database. Catches a *wholesale rewrite* -- the case where an
       attacker with DB access recomputes the entire chain so that check 1
       passes. Without step 2 the chain proves nothing against that attacker.
    """
    with _conn() as c:
        rows = c.execute("SELECT * FROM audit ORDER BY id").fetchall()
    prev = GENESIS
    for r in rows:
        recomputed = hashlib.sha256(
            f"{prev}|{r['at']}|{r['user']}|{r['action']}|{r['detail']}|{r['batch_id']}"
            .encode("utf-8")
        ).hexdigest()
        if recomputed != r["hash"] or r["prev_hash"] != prev:
            ext = anchor.cross_check(None, len(rows))
            return {"valid": False, "broken_at": r["id"], "entries": len(rows),
                    "internal": False, "anchor": ext}
        prev = r["hash"]
    ext = anchor.cross_check(prev, len(rows))
    return {"valid": bool(ext["valid"]), "entries": len(rows), "head": prev,
            "internal": True, "anchor": ext,
            "broken_at": None if ext["valid"] else "ancrage externe"}


# ----------------------------------------------------------------------------
# Dossier de Lot lifecycle
# ----------------------------------------------------------------------------
DEFAULT_CHECKLIST = list(PROFILE["checklist"])


def build_workflow_summary(batch: dict, stages: list[dict], signatures: list[dict], qc_samples: list[dict]) -> dict:
    stage_status = {s.get("name"): s.get("status") for s in stages}
    signed_count = sum(1 for s in stages if s.get("status") == "signed")
    qc_fail = sum(1 for s in qc_samples if s.get("verdict") == "FAIL")
    has_release = stage_status.get("liberation") == "signed"

    # The API returns translation KEYS, never prose. The client speaks three
    # languages; the server has no business deciding which one the operator reads.
    if batch.get("state") == "rejected":
        status = "rejected"
    elif batch.get("state") == "released" or has_release:
        status = "released"
    elif qc_fail:
        status = "quality_review"
    elif signed_count >= len(stages):
        status = "approved"
    elif signed_count > 0:
        status = "in_production"
    else:
        status = "draft"

    pending = [s.get("name") for s in stages if s.get("status") != "signed"]
    notes: list[dict] = [{"key": f"wf_note_{status}",
                          "args": {"n": qc_fail} if status == "quality_review" else {}}]
    if pending:
        notes.append({"key": "wf_note_next", "args": {"stages": ", ".join(pending)},
                      "stages": pending})
    if signatures:
        notes.append({"key": "wf_note_signed", "args": {"n": len(signatures)}})

    return {
        "status": status,
        "headline_key": f"wf_{status}",
        "progress": int(round(100 * signed_count / max(1, len(stages)), 0)),
        "notes": notes,
        "signed_count": signed_count,
        "pending_stages": pending,
        "quality_failures": qc_fail,
    }


def create_batch_for_product(odoo, product_id: int, of_id: int, oc_id: int,
                             user: str, qty_target: int | None = None) -> int:
    """Open a Dossier de Lot against ONE product version.

    Everything the dossier prints about the product -- name, presentation,
    strength, fill target, shelf life -- comes from the specification rather
    than from whatever the manufacturing order happened to say.
    """
    with _conn() as c:
        p = products.get(c, product_id)
    if not p:
        raise ValueError("produit introuvable")
    if p["status"] == "superseded":
        raise ValueError(
            f"{p['code']} v{p['version']} est superseded -- utilisez la version active")
    return create_batch_from_odoo(odoo, of_id, oc_id, user, product=p,
                                  qty_target=qty_target)


def create_batch_from_odoo(odoo, of_id: int, oc_id: int, user: str,
                           product: dict | None = None,
                           qty_target: int | None = None) -> int:
    of = odoo.read("mrp.production", [of_id],
                   ["name", "product_id", "product_qty", "bom_id", "lot_id",
                    "sale_order", "target_fill_g", "fill_tolerance_g", "fill_unit"])[0]
    oc = odoo.read("mrp.production", [oc_id], ["name", "bom_id"])[0]
    today = _dt.date.today()

    if product:
        # Product-led: the specification is the source of truth.
        product_id = product["id"]
        product_name = products.label(product)
        lot_name = f"{product['code']}-{today.strftime('%y%m%d')}-001"
        fill_target = product.get("fill_target")
        fill_tol = product.get("fill_tolerance")
        fill_unit = product.get("fill_unit") or "mL"
        shelf_days = int((product.get("shelf_life_months") or 24) * 30.44)
        qty = qty_target or of["product_qty"]
    else:
        # Legacy path: whatever the manufacturing order carried.
        product_id = None
        product_name = of["product_id"][1]
        lot_name = of["lot_id"][1] if of.get("lot_id") else of["name"]
        fill_target = of.get("target_fill_g")
        fill_tol = of.get("fill_tolerance_g")
        fill_unit = of.get("fill_unit") or "mL"
        shelf_days = 900 if any(x in product_name for x in
                                ("Spiruline", "Gelules", "Gélules", "capsule")) else 730
        qty = qty_target or of["product_qty"]

    mfg_date = today.isoformat()
    expiry_date = (today + _dt.timedelta(days=shelf_days)).isoformat()

    with _conn() as c:
        if product_id:
            # Lot numbers must be unique per product per day.
            n = c.execute("SELECT COUNT(*) n FROM batch WHERE lot_name LIKE ?",
                          (lot_name[:-3] + "%",)).fetchone()["n"]
            lot_name = f"{lot_name[:-3]}{n + 1:03d}"
        cur = c.execute(
            "INSERT INTO batch(lot_name, product_id, product, qty_target, of_ref, oc_ref,"
            " sale_order, target_fill_g, fill_tol_g, fill_unit, mfg_date, expiry_date,"
            " profile_key, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (lot_name, product_id, product_name, qty, of["name"], oc["name"],
             of.get("sale_order"), fill_target, fill_tol, fill_unit,
             mfg_date, expiry_date, PROFILE["key"], _now()),
        )
        batch_id = cur.lastrowid
        for s in STAGES:
            c.execute("INSERT INTO stage(batch_id, name) VALUES(?,?)", (batch_id, s))
        for label in DEFAULT_CHECKLIST:
            c.execute("INSERT INTO checklist(batch_id, label) VALUES(?,?)",
                      (batch_id, label))
        _seed_dispense(c, odoo, batch_id, of["bom_id"][0])
        _seed_dispense(c, odoo, batch_id, oc["bom_id"][0])
        _seed_packaging(c, odoo, batch_id, oc["bom_id"][0], of["product_qty"])
        audit(c, user, "batch.create",
              {"lot": lot_name, "of": of["name"], "oc": oc["name"],
               "product": f"{product['code']} v{product['version']}" if product else None},
              batch_id)
    anchor_now()
    return batch_id


# Which packaging articles belong to the primary vs the secondary dossier.
# Primary touches the product (blister, flacon, bouchon); secondary is the
# outer presentation (etui, caisse, etiquette de groupage).
_SECONDARY_CODES = ("PK-ETIQ", "PK-ETUI", "PK-CAISSE", "ET994", "CG005")


def _seed_packaging(c, odoo, batch_id, bom_id, qty_target):
    """Seed the DCOI/DCOII article balance from the packaging BOM.

    'Issued' is pre-filled with the theoretical requirement -- what the store
    would hand over. The operator records used / returned / waste, and the
    variance must close to zero.
    """
    bom = odoo.read("mrp.bom", [bom_id], ["bom_line_ids"])[0]
    for line in odoo.read("mrp.bom.line", bom["bom_line_ids"],
                          ["product_id", "product_qty", "uom"]):
        prod = odoo.read("product.product", [line["product_id"][0]],
                         ["name", "default_code"])[0]
        code = prod.get("default_code") or ""
        if not code.startswith("PK-"):
            continue                       # raw materials are not packaging articles
        stage = "cond_secondaire" if code in _SECONDARY_CODES else "cond_primaire"
        c.execute(
            "INSERT INTO packaging_recon(batch_id, stage, code, label, unit, issued)"
            " VALUES(?,?,?,?,?,?) ON CONFLICT(batch_id, code) DO NOTHING",
            (batch_id, stage, code, prod["name"], line["uom"], line["product_qty"]))


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
# Offline replay -- idempotent, and honest about when the operator really acted
# ----------------------------------------------------------------------------
def already_applied(op_id: str) -> dict | None:
    if not op_id:
        return None
    with _conn() as c:
        r = c.execute("SELECT * FROM applied_op WHERE op_id=?", (op_id,)).fetchone()
    return dict(r) if r else None


def mark_applied(op_id: str, kind: str, batch_id: int | None,
                 client_at: str | None, result: Any) -> None:
    """Remember a replayed operation so a retry cannot double-apply it.

    A flaky connection means the client may send the same weighing twice; without
    this the mass balance would silently double-count.
    """
    if not op_id:
        return
    with _write_conn() as c:
        c.execute("INSERT INTO applied_op(op_id, kind, batch_id, client_at, applied_at, result)"
                  " VALUES(?,?,?,?,?,?) ON CONFLICT(op_id) DO NOTHING",
                  (op_id, kind, batch_id, client_at, _now(),
                   json.dumps(result, ensure_ascii=False, default=str)))
        if client_at:
            # ALCOA+ "Contemporaneous": record the gap between acting and syncing.
            audit(c, "system", "offline.replay",
                  {"op": op_id, "kind": kind, "acted_at": client_at}, batch_id)


def sync_stats(batch_id: int | None = None) -> dict:
    with _conn() as c:
        q = "SELECT COUNT(*) n FROM applied_op WHERE client_at IS NOT NULL"
        a = (batch_id,) if batch_id else ()
        if batch_id:
            q += " AND batch_id=?"
        return {"replayed": c.execute(q, a).fetchone()["n"],
                "offline_kinds": sorted(OFFLINE_KINDS)}


# ----------------------------------------------------------------------------
# Deviations / CAPA -- opened automatically the moment something goes wrong
# ----------------------------------------------------------------------------
DISPOSITIONS = {"accept": "Accepte en l'etat", "rework": "Retraitement",
                "reject": "Rejet du lot"}


def open_deviation(c, batch_id: int, kind: str, severity: str, title: str,
                   detail: str, user: str) -> int | None:
    """Raise a deviation. Idempotent per (batch, kind, title) while still open,
    so a repeated failure does not spawn duplicate records."""
    dup = c.execute("SELECT id FROM deviation WHERE batch_id=? AND kind=? AND title=?"
                    " AND status='open'", (batch_id, kind, title)).fetchone()
    if dup:
        return None
    n = c.execute("SELECT COUNT(*) n FROM deviation WHERE batch_id=?",
                  (batch_id,)).fetchone()["n"] + 1
    ref = f"DEV-{batch_id:04d}-{n:02d}"
    cur = c.execute(
        "INSERT INTO deviation(batch_id, ref, kind, severity, title, detail,"
        " opened_by, opened_at) VALUES(?,?,?,?,?,?,?,?)",
        (batch_id, ref, kind, severity, title, detail, user, _now()))
    audit(c, user, "deviation.open",
          {"ref": ref, "kind": kind, "severity": severity, "title": title}, batch_id)
    return cur.lastrowid


def close_deviation(deviation_id: int, user: str, role: str, password: str,
                    disposition: str, root_cause: str, capa: str) -> dict:
    """Only QA closes a deviation, and closing is a signed act: password required.
    A root cause and a CAPA are mandatory -- 'closed, no action' is not a closure."""
    if role not in QA_ROLES:
        raise PermissionError(
            f"le role '{role}' ne peut pas cloturer une deviation "
            f"(reserve a {', '.join(sorted(QA_ROLES))})")
    if disposition not in DISPOSITIONS:
        raise ValueError(f"decision invalide: {disposition}")
    if not (root_cause or "").strip():
        raise ValueError("cause racine obligatoire")
    if not (capa or "").strip():
        raise ValueError("action corrective (CAPA) obligatoire")
    with _write_conn() as c:
        u = auth.check_credentials(c, user, password)
        if u["role"] != role:
            raise PermissionError(f"role '{role}' ne correspond pas au compte '{user}'")
        d = c.execute("SELECT * FROM deviation WHERE id=?", (deviation_id,)).fetchone()
        if not d:
            raise ValueError("deviation introuvable")
        if d["status"] == "closed":
            raise ValueError(f"{d['ref']} est deja cloturee")
        c.execute("UPDATE deviation SET status='closed', disposition=?, root_cause=?,"
                  " capa=?, closed_by=?, closed_role=?, closed_at=? WHERE id=?",
                  (disposition, root_cause, capa, user, role, _now(), deviation_id))
        audit(c, user, "deviation.close",
              {"ref": d["ref"], "disposition": disposition, "root_cause": root_cause,
               "capa": capa}, d["batch_id"])
        batch_id = d["batch_id"]
        if disposition == "reject":
            c.execute("UPDATE batch SET state='rejected' WHERE id=?", (batch_id,))
            audit(c, user, "batch.reject", {"ref": d["ref"]}, batch_id)
    anchor_now()
    return {"ref": d["ref"], "status": "closed", "disposition": disposition}


def list_deviations(batch_id: int) -> list[dict]:
    with _conn() as c:
        return _rows(c, "SELECT * FROM deviation WHERE batch_id=? ORDER BY id DESC", batch_id)


# ----------------------------------------------------------------------------
# Packaging article reconciliation (DCOI / DCOII "bilan des articles")
# ----------------------------------------------------------------------------
def set_packaging_recon(batch_id: int, code: str, field: str, value: float,
                        user: str) -> dict:
    """Record issued / used / returned / waste for one packaging article."""
    if field not in ("issued", "used", "returned", "waste"):
        raise ValueError(f"champ invalide: {field}")
    with _write_conn() as c:
        row = c.execute("SELECT * FROM packaging_recon WHERE batch_id=? AND code=?",
                        (batch_id, code)).fetchone()
        if not row:
            raise ValueError(f"article {code} absent du dossier")
        stage = row["stage"]
        st = c.execute("SELECT status FROM stage WHERE batch_id=? AND name=?",
                       (batch_id, stage)).fetchone()
        if st and st["status"] == "signed":
            raise PermissionError(f"{stage} deja signee: le bilan articles est clos")
        c.execute(f"UPDATE packaging_recon SET {field}=?, at=? WHERE id=?",
                  (value, _now(), row["id"]))
        audit(c, user, "packaging.recon",
              {"code": code, "field": field, "value": value}, batch_id)
    anchor_now()
    return packaging_balance(batch_id)


def packaging_balance(batch_id: int) -> dict:
    """issued - used - returned - waste should be zero. Anything else is an
    unexplained article discrepancy, which GMP requires you to justify."""
    with _conn() as c:
        rows = _rows(c, "SELECT * FROM packaging_recon WHERE batch_id=? ORDER BY stage, code",
                     batch_id)
    lines, worst = [], 0.0
    for r in rows:
        issued = r["issued"]
        # A line the operator has not touched is *incomplete*, not a 100 % loss.
        # Reporting an untouched form as a total discrepancy would train people
        # to ignore the warning, which is worse than not showing one.
        started = any(r[f] is not None for f in ("used", "returned", "waste"))
        if issued is None or not started:
            lines.append({**r, "accounted": None, "variance": None,
                          "variance_pct": None, "ok": None})
            continue
        accounted = (r["used"] or 0) + (r["returned"] or 0) + (r["waste"] or 0)
        variance = issued - accounted
        pct = abs(variance) / issued * 100 if issued else 0.0
        worst = max(worst, pct)
        lines.append({**r, "accounted": accounted, "variance": variance,
                      "variance_pct": round(pct, 2),
                      "ok": pct <= PACKAGING_VARIANCE_PCT})
    complete = bool(lines) and all(x["ok"] is not None for x in lines)
    return {"lines": lines, "complete": complete,
            "balanced": complete and all(x["ok"] for x in lines),
            "worst_variance_pct": round(worst, 2)}


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


def sign_stage(batch_id: int, stage: str, user: str, role: str, meaning: str,
               password: str = "") -> dict:
    """Apply an electronic signature to a dossier section.

    21 CFR Part 11.200(a): a signature needs two identification components, and
    the password is re-entered for *every* signing. `password` is not optional --
    an empty one fails, so a caller cannot skip the challenge by omitting it.
    """
    if stage not in STAGES:
        raise ValueError(f"etape inconnue: {stage}")
    with _write_conn() as c:
        # Identity first: verify who is signing before looking at anything else.
        u = auth.check_credentials(c, user, password)
        if u["role"] != role:
            raise PermissionError(
                f"role '{role}' ne correspond pas au compte '{user}' ({u['role']})")
        if STAGE_SIGNER[stage] != role:
            raise PermissionError(
                f"le role '{role}' ne peut pas signer '{stage}' "
                f"(reserve a '{STAGE_SIGNER[stage]}')")
        already = c.execute("SELECT status FROM stage WHERE batch_id=? AND name=?",
                            (batch_id, stage)).fetchone()
        if already and already["status"] == "signed":
            raise PermissionError(f"'{stage}' est deja signee")

        _guard_release(c, batch_id, stage)
        h = _stage_hash(c, batch_id, stage)
        c.execute(
            "INSERT INTO signature(batch_id, stage, user, role, meaning, record_hash, signed_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (batch_id, stage, user, role, meaning, h, _now()))
        c.execute("UPDATE stage SET status='signed' WHERE batch_id=? AND name=?",
                  (batch_id, stage))
        audit(c, user, "stage.sign",
              {"stage": stage, "role": role, "meaning": meaning, "hash": h,
               "auth": "password re-verified"}, batch_id)
        if stage == "liberation":
            mode = c.execute("SELECT run_mode, paper_ref FROM batch WHERE id=?",
                             (batch_id,)).fetchone()["run_mode"]
            if mode == "parallel":
                # Paper is still the legal record: mark the shadow complete.
                c.execute("UPDATE batch SET state='qualified' WHERE id=?", (batch_id,))
                audit(c, user, "batch.qualified",
                      {"lot": _lot(c, batch_id),
                       "note": "double saisie -- le dossier papier fait foi"}, batch_id)
            else:
                c.execute("UPDATE batch SET state='released' WHERE id=?", (batch_id,))
                audit(c, user, "batch.release", {"lot": _lot(c, batch_id)}, batch_id)
    anchor_now()
    return {"stage": stage, "record_hash": h, "signed_by": u["full_name"]}


def _guard_release(c, batch_id, stage):
    """The core compliance gate. Liberation is refused while anything is open."""
    if stage != "liberation":
        return
    # During a parallel run the paper dossier is the legal record. The digital
    # signature is still captured -- that is the point of the exercise -- but it
    # is recorded as a qualification signature, not a legal release.
    mode = c.execute("SELECT run_mode, paper_ref FROM batch WHERE id=?",
                     (batch_id,)).fetchone()
    if mode and mode["run_mode"] == "parallel" and not mode["paper_ref"]:
        raise PermissionError(
            "double saisie: renseignez la reference du dossier papier avant de signer")
    open_chg = c.execute("SELECT COUNT(*) n FROM bom_change WHERE batch_id=? AND status='pending'",
                         (batch_id,)).fetchone()["n"]
    if open_chg:
        raise PermissionError(
            f"liberation bloquee: {open_chg} modification(s) de formule en attente d'approbation AQ")
    open_dev = c.execute("SELECT COUNT(*) n FROM deviation WHERE batch_id=? AND status='open'",
                         (batch_id,)).fetchone()["n"]
    if open_dev:
        raise PermissionError(
            f"liberation bloquee: {open_dev} deviation(s) non cloturee(s)")
    rejected = c.execute("SELECT COUNT(*) n FROM deviation WHERE batch_id=?"
                         " AND disposition='reject'", (batch_id,)).fetchone()["n"]
    if rejected:
        raise PermissionError(
            f"liberation impossible: {rejected} deviation(s) avec decision de rejet")
    signed = {r["name"] for r in c.execute(
        "SELECT name FROM stage WHERE batch_id=? AND status='signed'", (batch_id,))}
    missing = [s for s in PREREQUISITE_STAGES if s not in signed]
    if missing:
        raise PermissionError(f"liberation bloquee: etapes non signees {missing}")
    fails = c.execute("SELECT COUNT(*) n FROM qc_sample WHERE batch_id=? AND verdict='FAIL'",
                      (batch_id,)).fetchone()["n"]
    if fails:
        raise PermissionError(f"liberation bloquee: {fails} controle(s) contenance hors tolerance")
    # Packaging articles must be accounted for. Queried on the caller's cursor:
    # opening a second connection here would deadlock against BEGIN IMMEDIATE.
    unbalanced, untouched = [], []
    for r in c.execute("SELECT code, issued, used, returned, waste FROM packaging_recon"
                       " WHERE batch_id=?", (batch_id,)):
        if r["issued"] is None:
            continue
        if not any(r[f] is not None for f in ("used", "returned", "waste")):
            untouched.append(r["code"])
            continue
        accounted = (r["used"] or 0) + (r["returned"] or 0) + (r["waste"] or 0)
        if r["issued"] and abs(r["issued"] - accounted) / r["issued"] * 100 > PACKAGING_VARIANCE_PCT:
            unbalanced.append(r["code"])
    if untouched:
        raise PermissionError(
            "liberation bloquee: bilan des articles de conditionnement non renseigne "
            f"({', '.join(untouched)})")
    if unbalanced:
        raise PermissionError(
            "liberation bloquee: bilan des articles de conditionnement non solde "
            f"({', '.join(unbalanced)})")


def _lot(c, batch_id):
    r = c.execute("SELECT lot_name FROM batch WHERE id=?", (batch_id,)).fetchone()
    return r["lot_name"] if r else None


# ----------------------------------------------------------------------------
# Data access (all SQL lives here; the API layer stays thin)
# ----------------------------------------------------------------------------
def _rows(c, q, *a):
    return [dict(r) for r in c.execute(q, a).fetchall()]


def list_batches(product_code: str | None = None) -> list[dict]:
    """All lots, or only those of one product across every one of its versions.

    Filtering by CODE rather than product_id is deliberate: a product's history
    spans its versions, and an operator looking for "PF201" means all of them.
    """
    q = ("SELECT b.id, b.lot_name, b.product, b.product_id, b.qty_target, b.state,"
         " b.of_ref, b.oc_ref, b.created_at, p.code AS product_code,"
         " p.version AS product_version FROM batch b"
         " LEFT JOIN product p ON p.id = b.product_id")
    args: tuple = ()
    if product_code:
        q += " WHERE p.code = ?"
        args = (product_code,)
    q += " ORDER BY b.id ASC"
    with _conn() as c:
        return _rows(c, q, *args)


# ----------------------------------------------------------------------------
# Migration: parallel run
# ----------------------------------------------------------------------------
# You cannot stop a GMP line to change record systems, and you cannot let an
# unvalidated system be the legal record. So a product line runs BOTH for an
# agreed number of lots: paper stays legally binding, BatchTwin shadows it, and
# QA compares them. Only when the divergence report is clean does the line cut
# over. This is the standard CSV approach and it is modelled here, not promised
# on a slide.
RUN_MODES = {"parallel": "Double saisie — le dossier papier fait foi",
             "live": "Dossier electronique — enregistrement legal"}
QUALIFICATION_LOTS = industry.rule(PROFILE, "qualification_lots", 3)


def set_run_mode(batch_id: int, mode: str, user: str, role: str,
                 paper_ref: str = "") -> dict:
    """Switch a lot between shadowing paper and being the legal record.

    Only QA decides this: it is the moment the legal record changes hands.
    """
    if mode not in RUN_MODES:
        raise ValueError(f"mode inconnu: {mode}")
    if role not in QA_ROLES:
        raise PermissionError(
            f"le role '{role}' ne peut pas changer le mode d'enregistrement "
            f"(reserve a {', '.join(sorted(QA_ROLES))})")
    if mode == "parallel" and not (paper_ref or "").strip():
        raise ValueError("reference du dossier papier obligatoire en double saisie")
    with _write_conn() as c:
        b = c.execute("SELECT state, run_mode FROM batch WHERE id=?", (batch_id,)).fetchone()
        if not b:
            raise ValueError("lot introuvable")
        if b["state"] == "released":
            raise PermissionError("lot deja libere: le mode d'enregistrement est fige")
        c.execute("UPDATE batch SET run_mode=?, paper_ref=? WHERE id=?",
                  (mode, paper_ref.strip() or None, batch_id))
        audit(c, user, "migration.run_mode",
              {"from": b["run_mode"], "to": mode, "paper_ref": paper_ref}, batch_id)
    anchor_now()
    return {"run_mode": mode, "paper_ref": paper_ref}


def migration_status(product_code: str | None = None) -> dict:
    """Where each product line stands on its way off paper.

    A line is ready to cut over once it has QUALIFICATION_LOTS parallel lots
    that completed with no open deviation and a balanced packaging reconciliation.
    """
    with _conn() as c:
        rows = _rows(c, """
            SELECT p.code, p.name, b.id, b.lot_name, b.run_mode, b.state, b.paper_ref,
                   (SELECT COUNT(*) FROM deviation d
                     WHERE d.batch_id=b.id AND d.status='open') AS open_dev,
                   (SELECT COUNT(*) FROM signature s WHERE s.batch_id=b.id) AS sigs
              FROM batch b JOIN product p ON p.id=b.product_id
             ORDER BY p.code, b.id""")
    lines: dict[str, dict] = {}
    for r in rows:
        if product_code and r["code"] != product_code:
            continue
        L = lines.setdefault(r["code"], {
            "code": r["code"], "name": r["name"], "parallel": 0, "live": 0,
            "qualified": 0, "blocking": [], "lots": []})
        L[r["run_mode"]] = L.get(r["run_mode"], 0) + 1
        # A qualification lot is a parallel lot that went the whole way cleanly.
        clean = r["run_mode"] == "parallel" and not r["open_dev"] and r["sigs"] >= len(STAGES)
        if clean:
            L["qualified"] += 1
        elif r["run_mode"] == "parallel" and r["open_dev"]:
            L["blocking"].append(f'{r["lot_name"]}: {r["open_dev"]} deviation(s) ouverte(s)')
        L["lots"].append({"id": r["id"], "lot": r["lot_name"], "mode": r["run_mode"],
                          "state": r["state"], "paper_ref": r["paper_ref"],
                          "qualification": clean})
    for L in lines.values():
        L["required"] = QUALIFICATION_LOTS
        L["ready_to_cut_over"] = L["qualified"] >= QUALIFICATION_LOTS and not L["blocking"]
        L["stage"] = ("cutover" if L["live"] and not L["parallel"]
                      else "ready" if L["ready_to_cut_over"]
                      else "parallel" if L["parallel"] else "not_started")
    return {"lines": sorted(lines.values(), key=lambda x: x["code"]),
            "required_lots": QUALIFICATION_LOTS, "run_modes": RUN_MODES}


def _norm_label(s: str) -> str:
    """Accents and case must not decide whether a field is recognised."""
    s = (s or "").lower().strip().rstrip(":").strip()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("ô", "o"),
                 ("î", "i"), ("ç", "c"), ("û", "u")):
        s = s.replace(a, b)
    return " ".join(s.split())


def apply_product_to_form(form: dict, product: dict | None) -> int:
    """Adapt a dossier template to the selected product.

    Medicka's Word templates are per-product: the identification block has
    "Probio D3 Green Castel" *printed into it*, which is precisely why a new
    product means a new document today. Here one template serves every product:
    wherever a row reads "Nom du produit | <printed value>", the printed value
    is replaced by the selected specification and marked as coming from it.

    Mutates `form` in place (it is a per-request copy) and returns the count.
    """
    if not product:
        return 0
    wanted = {_norm_label(k): v for k, v in products.dossier_prefill(product).items() if v}
    n = 0
    for section in form["sections"]:
        for block in section["blocks"]:
            if block["kind"] != "table":
                continue
            for row in block["rows"]:
                for i, cell in enumerate(row):
                    if cell["type"] != "label":
                        continue
                    val = wanted.get(_norm_label(cell.get("text", "")))
                    if val is None or i + 1 >= len(row):
                        continue
                    target = row[i + 1]
                    if target["type"] == "label":
                        # printed value -> replace with the specification
                        target["text"] = val
                    else:
                        target["value"] = val
                    target["from_spec"] = True
                    n += 1
    form["spec_fields"] = n
    return n


def _batch_stage_names(profile_key: str | None) -> list[str]:
    """The stage list of the rulebook a given batch was opened under."""
    if not profile_key or profile_key == PROFILE["key"]:
        return STAGES
    try:
        return industry.stage_names(industry.load(profile_key))
    except industry.ProfileError:
        return STAGES


def _stages_of(c, batch_id: int, order_names: list[str] | None = None) -> list[dict]:
    """Stages in lifecycle order, not insertion order.

    A repaired batch has its added rows at the end of the table, so ordering by
    id would present Liberation before Conditionnement.
    """
    order = {name: i for i, name in enumerate(order_names or STAGES)}
    rows = _rows(c, "SELECT name, status FROM stage WHERE batch_id=?", batch_id)
    return sorted(rows, key=lambda r: order.get(r["name"], 99))


def _ensure_stages(batch_id: int, have: set[str],
                   want: list[str] | None = None) -> None:
    """Create any lifecycle stage this batch is missing, in canonical order.

    Signed stages are never touched: this only ever adds rows.
    """
    want = want or STAGES
    with _write_conn() as c:
        for name in want:
            if name not in have:
                c.execute("INSERT INTO stage(batch_id, name) VALUES(?,?)"
                          " ON CONFLICT(batch_id, name) DO NOTHING", (batch_id, name))
        c.execute("DELETE FROM stage WHERE batch_id=? AND name NOT IN "
                  "(" + ",".join("?" * len(want)) + ") AND status<>'signed'",
                  (batch_id, *want))
        audit(c, "system", "stage.repair",
              {"added": sorted(set(want) - have)}, batch_id)


def get_batch(batch_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM batch WHERE id=?", (batch_id,)).fetchone()
        if not r:
            return None
        b = dict(r)
        # Order by the rulebook THIS lot was opened under, not the active one:
        # after a profile switch, ordering by the new lifecycle would push an
        # unknown stage to the end and misrepresent a signed record.
        own = _batch_stage_names(b.get("profile_key"))
        b["stages"] = _stages_of(c, batch_id, own)

    # Self-heal a batch whose stage rows are missing or predate the DCOI/DCOII
    # split. Without this the UI reads `undefined.status` and dies on a cryptic
    # error instead of showing a dossier -- and every batch created before the
    # split would be permanently unopenable.
    # Repair only against the rulebook this lot was opened under. A batch whose
    # stages merely differ from the CURRENT profile is not corrupt -- it belongs
    # to another lifecycle, and rewriting it would falsify a signed record.
    have = {s["name"] for s in b["stages"]}
    # Repair against the lot's OWN lifecycle -- which is the whole point of
    # storing profile_key. Anything that differs from it is genuinely wrong
    # (missing rows, or names from before the DCOI/DCOII split), while a lot
    # belonging to another profile resolves `own` to that profile and matches.
    if have != set(own):
        _ensure_stages(batch_id, have, own)
        with _conn() as c:
            b["stages"] = _stages_of(c, batch_id, own)

    with _conn() as c:
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
        b["deviations"] = _rows(c, "SELECT * FROM deviation WHERE batch_id=? ORDER BY id DESC",
                                batch_id)
        b["deviations_open"] = sum(1 for x in b["deviations"] if x["status"] == "open")
    b["packaging"] = packaging_balance(batch_id)
    with _conn() as c:
        # The dossier must show the spec version it was actually made against,
        # even after that version has been superseded.
        b["product_spec"] = products.get(c, b["product_id"]) if b.get("product_id") else None
        b["workflow"] = build_workflow_summary(b, b["stages"], b["signatures"], b["qc"])
        return b


def update_checklist(item_id: int, ok: int, note: str, user: str,
                     escalate_to: str | None) -> None:
    """A failed line clearance is not just a red tick -- it opens a deviation,
    and the lot cannot be released until QA dispositions it."""
    with _write_conn() as c:
        c.execute("UPDATE checklist SET ok=?, note=?, escalated_to=? WHERE id=?",
                  (ok, note, escalate_to, item_id))
        row = c.execute("SELECT batch_id, label FROM checklist WHERE id=?", (item_id,)).fetchone()
        audit(c, user, "checklist.update",
              {"item": row["label"], "ok": bool(ok), "escalated_to": escalate_to},
              row["batch_id"])
        if not ok:
            open_deviation(c, row["batch_id"], "line_clearance", "major",
                           f"Vide de ligne non conforme: {row['label']}",
                           note or "Point de vide de ligne declare non conforme.", user)
    anchor_now()


def record_dispense(line_id: int, dispensed: float, loss: float, user: str) -> None:
    with _write_conn() as c:
        row = c.execute("SELECT batch_id, material, qty_target FROM dispense WHERE id=?",
                        (line_id,)).fetchone()
        if not row:
            raise ValueError("ligne de pesee introuvable")
        c.execute("UPDATE dispense SET qty_dispensed=?, qty_loss=?, at=? WHERE id=?",
                  (dispensed, loss, _now(), line_id))
        audit(c, user, "dispense.record",
              {"material": row["material"], "target": row["qty_target"],
               "dispensed": dispensed, "loss": loss}, row["batch_id"])
    anchor_now()


def add_qc_sample(batch_id: int, measurements: list[float], user: str) -> dict:
    """Record one contenance sample. A FAIL opens a deviation automatically."""
    b = get_batch(batch_id)
    if not b:
        raise ValueError("lot introuvable")
    lo = (b["target_fill_g"] or 0) - (b["fill_tol_g"] or 0)
    hi = (b["target_fill_g"] or 0) + (b["fill_tol_g"] or 0)
    mean = sum(measurements) / len(measurements)
    rng = max(measurements) - min(measurements)
    out = [m for m in measurements if not lo <= m <= hi]
    verdict = "PASS" if not out else "FAIL"
    unit = b.get("fill_unit") or "mL"
    with _write_conn() as c:
        c.execute("INSERT INTO qc_sample(batch_id, taken_at, measurements, mean, rng, verdict)"
                  " VALUES(?,?,?,?,?,?)",
                  (batch_id, _now(), json.dumps(measurements), mean, rng, verdict))
        audit(c, user, "qc.sample",
              {"n": len(measurements), "mean": round(mean, 2), "verdict": verdict}, batch_id)
        if verdict == "FAIL":
            open_deviation(
                c, batch_id, "qc_fail", "critical",
                "Controle contenance hors specification",
                f"{len(out)}/{len(measurements)} unites hors tolerance "
                f"[{lo:.1f}-{hi:.1f} {unit}]: {', '.join(f'{m:.1f}' for m in out)}. "
                f"Moyenne {mean:.2f} {unit}, etendue {rng:.2f} {unit}.", user)
    anchor_now()
    return {"mean": round(mean, 2), "range": round(rng, 2), "verdict": verdict,
            "out_of_spec": len(out)}


def set_good_units(batch_id: int, units: int, user: str) -> None:
    with _write_conn() as c:
        c.execute("UPDATE batch SET good_units=? WHERE id=?", (units, batch_id))
        audit(c, user, "packaging.count", {"good_units": units}, batch_id)
    anchor_now()


def record_energy(batch_id: int, stage: str, machine: str, kwh: float,
                  source: str, user: str) -> None:
    with _write_conn() as c:
        c.execute("INSERT INTO energy(batch_id, stage, machine, kwh, source, at)"
                  " VALUES(?,?,?,?,?,?)", (batch_id, stage, machine, kwh, source, _now()))
        audit(c, user, "energy.reading",
              {"stage": stage, "machine": machine, "kwh": round(kwh, 3), "source": source}, batch_id)
    anchor_now()


def simulate_energy(batch_id: int, user: str) -> int:
    """Populate realistic per-machine energy for the batch, as if IoT clamps had
    metered each workstation for the batch run. Returns number of readings."""
    import random
    b = get_batch(batch_id)
    units = b["qty_target"] or 500
    # rough run hours scaled to batch size
    hours = {"fabrication": 1.2, "cond_primaire": units / 300.0,
             "cond_secondaire": units / 450.0, "qualite": 0.8, "liberation": 0.0}
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

