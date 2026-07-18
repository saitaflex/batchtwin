"""
Product catalog -- versioned, and the anchor every dossier hangs from.

A batch record is only meaningful against a specific product specification. In
GMP the specification is a controlled document: when the formula or the
packaging changes you do not edit the old one, you issue a NEW VERSION and the
previous version stays exactly as it was, because batches already made against
it must remain readable forever.

So `product` is append-only per version:

    code = "PF990"          <- stable product identity
    version = 1, 2, 3 ...   <- immutable specifications
    status  = draft | active | superseded

Exactly one version of a code is `active` at a time. A batch stores the
product_id of the precise version it was made against, never just the code.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from typing import Any

# Dosage forms Medicka actually manufactures (67 % oral liquids, then capsules,
# coated tablets, gels/creams). Free text is still allowed via "autre".
DOSAGE_FORMS = [
    ("solution_buvable", "Solution buvable / sirop"),
    ("solution_huileuse", "Solution huileuse"),
    ("capsule_molle", "Capsule molle"),
    ("gelule", "Gélule"),
    ("comprime", "Comprimé"),
    ("comprime_pellicule", "Comprimé pelliculé"),
    ("poudre", "Poudre / sachet"),
    ("gel_creme", "Gel / crème"),
    ("autre", "Autre"),
]

CATEGORIES = [
    ("complement", "Complément alimentaire"),
    ("dispositif", "Dispositif médical"),
    ("cosmetique", "Cosmétique"),
    ("veterinaire", "Vétérinaire"),
]

# What a nutrition/composition line is expressed against.
NUTRIENT_BASIS = [
    ("per_unit", "Par unité"),
    ("per_dose", "Par dose journalière"),
    ("per_100g", "Pour 100 g"),
    ("per_100ml", "Pour 100 mL"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,                   -- PF990 -- stable across versions
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',-- draft | active | superseded
    name TEXT NOT NULL,
    sku TEXT,
    category TEXT,
    dosage_form TEXT,
    strength TEXT,                        -- "50 000 UI", "500 mg"
    packaging TEXT,                       -- "Boîte de 15 capsules molles"
    units_per_pack INTEGER,
    manufacturer TEXT DEFAULT 'Laboratoires MEDICKA',
    licensor TEXT,                        -- "Sous licence de GREEN CASTEL"
    barcode TEXT,                         -- EAN/GTIN, used to re-find a product
    shelf_life_months INTEGER DEFAULT 24,
    fill_target REAL, fill_tolerance REAL, fill_unit TEXT DEFAULT 'mL',
    storage TEXT, notes TEXT,
    change_reason TEXT,                   -- why THIS version exists
    created_by TEXT NOT NULL, created_at TEXT NOT NULL,
    superseded_by INTEGER REFERENCES product(id),
    UNIQUE(code, version)
);
CREATE TABLE IF NOT EXISTS product_nutrient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES product(id),
    label TEXT NOT NULL,
    amount TEXT,
    unit TEXT,
    basis TEXT DEFAULT 'per_dose',
    nrv_pct REAL,                         -- % of nutrient reference value
    source TEXT DEFAULT 'manual',         -- manual | scan_label | scan_barcode
    position INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_product_code ON product(code, version);
CREATE INDEX IF NOT EXISTS idx_product_barcode ON product(barcode);
"""

# Seeded from the real dossiers so the demo opens with a populated catalog.
SEED = [
    dict(code="PF990", name="Probio D3 Green Castel", sku="FG-PROBIOD3-30",
         category="complement", dosage_form="solution_huileuse",
         strength="2 mg vit. D3 / mL", packaging="Boîte de 1 flacon de 30 mL",
         units_per_pack=1, licensor="GREEN CASTEL", shelf_life_months=24,
         fill_target=30.0, fill_tolerance=1.5, fill_unit="mL",
         storage="À conserver à l'abri de la lumière, < 25 °C",
         barcode="6194000990017",
         nutrients=[("Vitamine D3", "2", "mg", "per_unit", 100.0),
                    ("Vitamine E", "1.8", "mg", "per_unit", 15.0),
                    ("Probio-Tech® Bifidobacterium lactis", "3.3334", "mg", "per_unit", None)]),
    dict(code="PF994", name="Vitamine D3 50 000 UI Green Castel",
         sku="FG-VITD3-15", category="complement", dosage_form="capsule_molle",
         strength="50 000 UI", packaging="Boîte de 15 capsules molles",
         units_per_pack=15, licensor="GREEN CASTEL", shelf_life_months=24,
         fill_target=500.0, fill_tolerance=25.0, fill_unit="mg",
         storage="Température ambiante, < 25 °C", barcode="6194000994015",
         nutrients=[("Vitamine D3 (cholécalciférol)", "50000", "UI", "per_unit", 25000.0)]),
    dict(code="PF954", name="Calcimax", sku="FG-CALCIMAX-30",
         category="complement", dosage_form="comprime",
         strength="500 mg calcium", packaging="Boîte de 30 comprimés",
         units_per_pack=30, licensor="LEEN PHARMA", shelf_life_months=24,
         fill_target=1200.0, fill_tolerance=60.0, fill_unit="mg",
         storage="Température ambiante, < 25 °C", barcode="6194000954019",
         nutrients=[("Calcium", "500", "mg", "per_dose", 62.5),
                    ("Vitamine D3", "200", "UI", "per_dose", 100.0)]),
    dict(code="PF201", name="Sirop Magnésium + Vitamine B6 200 mL",
         sku="FG-MGB6-200", category="complement", dosage_form="solution_buvable",
         strength="300 mg Mg / 15 mL", packaging="Flacon PET 200 mL + gobelet doseur",
         units_per_pack=1, shelf_life_months=24,
         fill_target=200.0, fill_tolerance=8.0, fill_unit="mL",
         storage="Après ouverture, conserver au réfrigérateur", barcode="6194000201014",
         nutrients=[("Magnésium (citrate)", "300", "mg", "per_dose", 80.0),
                    ("Vitamine B6", "2", "mg", "per_dose", 143.0)]),
    dict(code="PF310", name="Gélules Spiruline 500 mg", sku="FG-SPIR-60",
         category="complement", dosage_form="gelule", strength="500 mg",
         packaging="Pilulier de 60 gélules", units_per_pack=60,
         shelf_life_months=30, fill_target=500.0, fill_tolerance=25.0, fill_unit="mg",
         storage="À l'abri de l'humidité", barcode="6194000310013",
         nutrients=[("Spiruline (Arthrospira platensis)", "500", "mg", "per_unit", None),
                    ("Protéines", "300", "mg", "per_unit", None)]),
]

# Fields that define the specification. Changing any of them requires a new
# version rather than an edit -- that is the whole point of version control.
SPEC_FIELDS = ("name", "category", "dosage_form", "strength", "packaging",
               "units_per_pack", "fill_target", "fill_tolerance", "fill_unit",
               "shelf_life_months", "licensor", "manufacturer")

EDITABLE_IN_PLACE = ("sku", "barcode", "storage", "notes")


class ProductError(ValueError):
    pass


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def init(c: sqlite3.Connection) -> None:
    c.executescript(SCHEMA)


def seed(c: sqlite3.Connection, user: str = "system") -> int:
    """Populate the catalog once. Returns how many products were created."""
    n = 0
    for spec in SEED:
        if c.execute("SELECT 1 FROM product WHERE code=?", (spec["code"],)).fetchone():
            continue
        nutrients = spec.pop("nutrients", [])
        pid = _insert(c, {**spec, "version": 1, "status": "active"}, user)
        for i, (label, amount, unit, basis, nrv) in enumerate(nutrients):
            c.execute("INSERT INTO product_nutrient(product_id, label, amount, unit,"
                      " basis, nrv_pct, source, position) VALUES(?,?,?,?,?,?,?,?)",
                      (pid, label, amount, unit, basis, nrv, "manual", i))
        spec["nutrients"] = nutrients
        n += 1
    return n


def _insert(c: sqlite3.Connection, d: dict, user: str) -> int:
    cols = ("code", "version", "status", "name", "sku", "category", "dosage_form",
            "strength", "packaging", "units_per_pack", "manufacturer", "licensor",
            "barcode", "shelf_life_months", "fill_target", "fill_tolerance",
            "fill_unit", "storage", "notes", "change_reason")
    vals = [d.get(k) for k in cols]
    vals[cols.index("manufacturer")] = d.get("manufacturer") or "Laboratoires MEDICKA"
    cur = c.execute(
        f"INSERT INTO product({','.join(cols)}, created_by, created_at)"
        f" VALUES({','.join('?' * len(cols))},?,?)", (*vals, user, _now()))
    return cur.lastrowid


def _require(d: dict) -> None:
    for field, label in (("code", "code produit"), ("name", "nom du produit"),
                         ("dosage_form", "forme galénique")):
        if not str(d.get(field) or "").strip():
            raise ProductError(f"{label} obligatoire")


def create(c: sqlite3.Connection, data: dict, nutrients: list[dict], user: str) -> dict:
    """Create version 1 of a new product code."""
    _require(data)
    code = data["code"].strip().upper()
    if c.execute("SELECT 1 FROM product WHERE code=?", (code,)).fetchone():
        raise ProductError(f"le code produit {code} existe deja -- creez une nouvelle version")
    pid = _insert(c, {**data, "code": code, "version": 1, "status": "active"}, user)
    _set_nutrients(c, pid, nutrients)
    return get(c, pid)


def new_version(c: sqlite3.Connection, product_id: int, data: dict,
                nutrients: list[dict], reason: str, user: str) -> dict:
    """Supersede a product with a new immutable version.

    The old version is never modified: batches already made against it must stay
    readable exactly as they were signed.
    """
    if not (reason or "").strip():
        raise ProductError("motif de changement obligatoire pour une nouvelle version")
    old = c.execute("SELECT * FROM product WHERE id=?", (product_id,)).fetchone()
    if not old:
        raise ProductError("produit introuvable")
    merged = {**dict(old), **{k: v for k, v in data.items() if v is not None}}
    _require(merged)
    nxt = c.execute("SELECT MAX(version) v FROM product WHERE code=?",
                    (old["code"],)).fetchone()["v"] + 1
    pid = _insert(c, {**merged, "code": old["code"], "version": nxt,
                      "status": "active", "change_reason": reason.strip()}, user)
    _set_nutrients(c, pid, nutrients if nutrients is not None else
                   [dict(r) for r in _nutrients(c, product_id)])
    # Only the previous ACTIVE version is superseded; older ones already are.
    c.execute("UPDATE product SET status='superseded', superseded_by=?"
              " WHERE code=? AND id<>? AND status='active'", (pid, old["code"], pid))
    return get(c, pid)


def update_in_place(c: sqlite3.Connection, product_id: int, data: dict, user: str) -> dict:
    """Edit only the fields that are not part of the specification.

    Fixing a typo in a storage note must not force a new version; changing the
    strength must.
    """
    changed = {k: v for k, v in data.items() if k in EDITABLE_IN_PLACE}
    if not changed:
        raise ProductError(
            "ces champs definissent la specification: creez une nouvelle version")
    sets = ", ".join(f"{k}=?" for k in changed)
    c.execute(f"UPDATE product SET {sets} WHERE id=?", (*changed.values(), product_id))
    return get(c, product_id)


def _set_nutrients(c: sqlite3.Connection, product_id: int, rows: list[dict] | None) -> None:
    if rows is None:
        return
    c.execute("DELETE FROM product_nutrient WHERE product_id=?", (product_id,))
    for i, r in enumerate(rows):
        label = str(r.get("label") or "").strip()
        if not label:
            continue
        c.execute("INSERT INTO product_nutrient(product_id, label, amount, unit,"
                  " basis, nrv_pct, source, position) VALUES(?,?,?,?,?,?,?,?)",
                  (product_id, label, r.get("amount"), r.get("unit"),
                   r.get("basis") or "per_dose", r.get("nrv_pct"),
                   r.get("source") or "manual", i))


def _nutrients(c: sqlite3.Connection, product_id: int) -> list[dict]:
    return [dict(r) for r in c.execute(
        "SELECT label, amount, unit, basis, nrv_pct, source FROM product_nutrient"
        " WHERE product_id=? ORDER BY position, id", (product_id,))]


def get(c: sqlite3.Connection, product_id: int) -> dict | None:
    r = c.execute("SELECT * FROM product WHERE id=?", (product_id,)).fetchone()
    if not r:
        return None
    p = dict(r)
    p["nutrients"] = _nutrients(c, product_id)
    p["versions"] = [dict(x) for x in c.execute(
        "SELECT id, version, status, created_at, change_reason FROM product"
        " WHERE code=? ORDER BY version DESC", (r["code"],))]
    return p


def active(c: sqlite3.Connection, code: str) -> dict | None:
    r = c.execute("SELECT id FROM product WHERE code=? AND status='active'",
                  (code,)).fetchone()
    return get(c, r["id"]) if r else None


def by_barcode(c: sqlite3.Connection, barcode: str) -> dict | None:
    """Scanning your own product finds it -- no external lookup service."""
    r = c.execute("SELECT id FROM product WHERE barcode=? AND status='active'"
                  " ORDER BY version DESC LIMIT 1", (barcode or "",)).fetchone()
    return get(c, r["id"]) if r else None


def listing(c: sqlite3.Connection, include_superseded: bool = False) -> list[dict]:
    q = ("SELECT id, code, version, status, name, sku, category, dosage_form,"
         " strength, packaging, barcode, fill_target, fill_tolerance, fill_unit"
         " FROM product")
    if not include_superseded:
        q += " WHERE status='active'"
    q += " ORDER BY code, version DESC"
    rows = [dict(r) for r in c.execute(q)]
    for r in rows:
        r["nutrient_count"] = c.execute(
            "SELECT COUNT(*) n FROM product_nutrient WHERE product_id=?",
            (r["id"],)).fetchone()["n"]
    return rows


def label(p: dict) -> str:
    """One-line identity used on dossiers and lot names."""
    bits = [p.get("name") or ""]
    if p.get("strength"):
        bits.append(p["strength"])
    return " ".join(bits).strip() or p.get("code", "")


def dossier_prefill(p: dict) -> dict[str, str]:
    """The product identification block every Medicka dossier opens with.

    Keys mirror the labels printed on DFA / DCOI / DCOII / DCT, so the same map
    fills all four.
    """
    forms = dict(DOSAGE_FORMS)
    return {
        "Nom du produit": p.get("name") or "",
        "Forme galénique": forms.get(p.get("dosage_form"), p.get("dosage_form") or ""),
        "Présentation": p.get("packaging") or "",
        "Code du produit": p.get("code") or "",
        "Dosage": p.get("strength") or "",
        "Fabriqué par": p.get("manufacturer") or "Laboratoires MEDICKA",
        "Sous licence de": p.get("licensor") or "NA",
        "Validité": f"{(p.get('shelf_life_months') or 24) // 12:02d} ans",
        "Conditions de conservation": p.get("storage") or "",
        "Version de la spécification": f"v{p.get('version', 1)}",
    }
