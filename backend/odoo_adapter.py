"""
Odoo integration layer for BatchTwin.

Design rule: the PUBLIC contract of this module mirrors Odoo's real external API
(`execute_kw(db, uid, password, model, method, args, kwargs)` over XML-RPC).
That means the rest of BatchTwin talks to Odoo the *real* way. To go live you
delete `MockOdoo`, instantiate `LiveOdoo`, and change nothing else.

Odoo models we mirror (all real, standard Odoo MRP/Quality models):
    mrp.production      -> Ordre de Fabrication (Manufacturing Order)
    mrp.bom / .line     -> Nomenclature (Bill of Materials)
    product.product     -> Article (raw material or finished good)
    stock.lot           -> Lot / numero de lot
    quality.point       -> Declencheur de controle qualite (QC trigger)
"""
from __future__ import annotations
import datetime as _dt
from typing import Any


class OdooError(RuntimeError):
    pass


class BaseOdoo:
    """Shared surface. Both mock and live expose execute_kw + thin helpers."""

    def execute_kw(self, model: str, method: str,
                   args: list | None = None, kwargs: dict | None = None) -> Any:
        raise NotImplementedError

    # ---- convenience wrappers used by the rest of the app -----------------
    def search_read(self, model: str, domain: list, fields: list[str]) -> list[dict]:
        return self.execute_kw(model, "search_read", [domain], {"fields": fields})

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]:
        return self.execute_kw(model, "read", [ids], {"fields": fields})


class LiveOdoo(BaseOdoo):
    """Real Odoo over XML-RPC. Not used in the demo, but this is exactly how it
    would connect - proving the mock is a drop-in, not a fantasy."""

    def __init__(self, url: str, db: str, username: str, password: str):
        import xmlrpc.client  # stdlib, no extra dep
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, username, password, {})
        if not self.uid:
            raise OdooError("Odoo authentication failed")
        self.db, self.password = db, password
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def execute_kw(self, model, method, args=None, kwargs=None):
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, method,
            args or [], kwargs or {})


class MockOdoo(BaseOdoo):
    """In-memory Odoo seeded with a realistic food-supplement manufacturing
    order, so the demo runs with zero external setup."""

    def __init__(self):
        today = _dt.date.today().strftime("%y%m%d")
        # Realistic Medicka Laboratories product: an oral liquid food supplement
        # (liquids are 67% of their output). "Sirop Magnesium + Vitamine B6 200 mL",
        # Forme & Vitalite range. Fill volume (contenance) is measured in mL.
        self._db = {
            "product.product": {
                101: {"id": 101, "name": "Sirop Magnesium + Vitamine B6 200 mL", "default_code": "FG-MGB6-200",
                      "type": "product", "uom_name": "Unit", "list_price": 8.90},
                201: {"id": 201, "name": "Eau purifiee", "default_code": "RM-EAU",
                      "type": "product", "uom_name": "kg", "standard_price": 0.05},
                202: {"id": 202, "name": "Sirop de sorbitol 70%", "default_code": "RM-SORB",
                      "type": "product", "uom_name": "kg", "standard_price": 1.10},
                203: {"id": 203, "name": "Citrate de magnesium", "default_code": "RM-MGCIT",
                      "type": "product", "uom_name": "kg", "standard_price": 12.00},
                204: {"id": 204, "name": "Chlorhydrate de pyridoxine (Vit. B6)", "default_code": "RM-B6",
                      "type": "product", "uom_name": "kg", "standard_price": 180.00},
                205: {"id": 205, "name": "Sorbate de potassium (conservateur)", "default_code": "RM-SORBK",
                      "type": "product", "uom_name": "kg", "standard_price": 6.50},
                206: {"id": 206, "name": "Acide citrique (correcteur pH)", "default_code": "RM-ACID",
                      "type": "product", "uom_name": "kg", "standard_price": 1.80},
                207: {"id": 207, "name": "Arome orange", "default_code": "RM-AROM",
                      "type": "product", "uom_name": "kg", "standard_price": 22.00},
                301: {"id": 301, "name": "Flacon PET 200 mL + bouchon", "default_code": "PK-FLA-200",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.14},
                302: {"id": 302, "name": "Gobelet doseur", "default_code": "PK-GOB",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.03},
                303: {"id": 303, "name": "Etiquette + notice", "default_code": "PK-ETIQ",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.05},
                304: {"id": 304, "name": "Etui carton", "default_code": "PK-ETUI",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.09},
                # --- Product 2: capsule line (Gelules Spiruline 500 mg) ---
                102: {"id": 102, "name": "Gelules Spiruline 500 mg - pilulier 60", "default_code": "FG-SPIR-60",
                      "type": "product", "uom_name": "Unit", "list_price": 12.50},
                401: {"id": 401, "name": "Poudre de spiruline", "default_code": "RM-SPIR",
                      "type": "product", "uom_name": "kg", "standard_price": 18.00},
                402: {"id": 402, "name": "Cellulose microcristalline (diluant)", "default_code": "RM-CMC",
                      "type": "product", "uom_name": "kg", "standard_price": 3.50},
                403: {"id": 403, "name": "Stearate de magnesium (lubrifiant)", "default_code": "RM-STMG",
                      "type": "product", "uom_name": "kg", "standard_price": 5.00},
                404: {"id": 404, "name": "Silice colloidale (anti-agglomerant)", "default_code": "RM-SIL",
                      "type": "product", "uom_name": "kg", "standard_price": 8.00},
                405: {"id": 405, "name": "Gelule vide T0", "default_code": "PK-GEL-T0",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.008},
                406: {"id": 406, "name": "Pilulier PEHD + bouchon", "default_code": "PK-PIL",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.12},
                407: {"id": 407, "name": "Etiquette + notice (gelules)", "default_code": "PK-ETIQ-G",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.05},
                408: {"id": 408, "name": "Etui carton (gelules)", "default_code": "PK-ETUI-G",
                      "type": "product", "uom_name": "Unit", "standard_price": 0.09},
            },
            # BOM lines: theoretical quantities per batch of 800 flacons (~165 L bulk).
            "mrp.bom.line": {
                # -- Ordre de Fabrication (melange du sirop) --
                1: {"id": 1, "bom_id": 11, "product_id": [201, "RM-EAU"], "product_qty": 120.0, "uom": "kg"},
                2: {"id": 2, "bom_id": 11, "product_id": [202, "RM-SORB"], "product_qty": 40.0, "uom": "kg"},
                3: {"id": 3, "bom_id": 11, "product_id": [203, "RM-MGCIT"], "product_qty": 4.8, "uom": "kg"},
                4: {"id": 4, "bom_id": 11, "product_id": [204, "RM-B6"], "product_qty": 0.032, "uom": "kg"},
                5: {"id": 5, "bom_id": 11, "product_id": [205, "RM-SORBK"], "product_qty": 0.33, "uom": "kg"},
                6: {"id": 6, "bom_id": 11, "product_id": [206, "RM-ACID"], "product_qty": 0.66, "uom": "kg"},
                7: {"id": 7, "bom_id": 11, "product_id": [207, "RM-AROM"], "product_qty": 1.6, "uom": "kg"},
                # -- Ordre de Conditionnement (packaging) --
                8: {"id": 8, "bom_id": 12, "product_id": [301, "PK-FLA-200"], "product_qty": 800.0, "uom": "Unit"},
                9: {"id": 9, "bom_id": 12, "product_id": [302, "PK-GOB"], "product_qty": 800.0, "uom": "Unit"},
                10: {"id": 10, "bom_id": 12, "product_id": [303, "PK-ETIQ"], "product_qty": 800.0, "uom": "Unit"},
                11: {"id": 11, "bom_id": 12, "product_id": [304, "PK-ETUI"], "product_qty": 800.0, "uom": "Unit"},
                # -- capsule OF (melange de poudre, 6000 gelules) --
                12: {"id": 12, "bom_id": 13, "product_id": [401, "RM-SPIR"], "product_qty": 2.7, "uom": "kg"},
                13: {"id": 13, "bom_id": 13, "product_id": [402, "RM-CMC"], "product_qty": 0.25, "uom": "kg"},
                14: {"id": 14, "bom_id": 13, "product_id": [403, "RM-STMG"], "product_qty": 0.03, "uom": "kg"},
                15: {"id": 15, "bom_id": 13, "product_id": [404, "RM-SIL"], "product_qty": 0.02, "uom": "kg"},
                # -- capsule OC (encapsulation + conditionnement, 100 piluliers) --
                16: {"id": 16, "bom_id": 14, "product_id": [405, "PK-GEL-T0"], "product_qty": 6000.0, "uom": "Unit"},
                17: {"id": 17, "bom_id": 14, "product_id": [406, "PK-PIL"], "product_qty": 100.0, "uom": "Unit"},
                18: {"id": 18, "bom_id": 14, "product_id": [407, "PK-ETIQ-G"], "product_qty": 100.0, "uom": "Unit"},
                19: {"id": 19, "bom_id": 14, "product_id": [408, "PK-ETUI-G"], "product_qty": 100.0, "uom": "Unit"},
            },
            "mrp.bom": {
                11: {"id": 11, "type": "normal", "code": "OF", "product_id": [101, "FG-MGB6-200"],
                     "product_qty": 800, "bom_line_ids": [1, 2, 3, 4, 5, 6, 7]},
                12: {"id": 12, "type": "phantom", "code": "OC", "product_id": [101, "FG-MGB6-200"],
                     "product_qty": 800, "bom_line_ids": [8, 9, 10, 11]},
                13: {"id": 13, "type": "normal", "code": "OF", "product_id": [102, "FG-SPIR-60"],
                     "product_qty": 100, "bom_line_ids": [12, 13, 14, 15]},
                14: {"id": 14, "type": "phantom", "code": "OC", "product_id": [102, "FG-SPIR-60"],
                     "product_qty": 100, "bom_line_ids": [16, 17, 18, 19]},
            },
            "stock.lot": {
                1: {"id": 1, "name": f"MGB6-{today}-001", "product_id": [101, "FG-MGB6-200"]},
                2: {"id": 2, "name": f"SPIR-{today}-001", "product_id": [102, "FG-SPIR-60"]},
            },
            "mrp.production": {
                1001: {"id": 1001, "name": f"OF/{today}/0001", "order_kind": "fabrication",
                       "product_id": [101, "Sirop Magnesium + Vitamine B6 200 mL"], "product_qty": 800,
                       "bom_id": [11, "OF"], "lot_id": [1, f"MGB6-{today}-001"],
                       "state": "confirmed", "sale_order": "S00042",
                       "target_fill_g": 200.0, "fill_tolerance_g": 8.0, "fill_unit": "mL"},
                1002: {"id": 1002, "name": f"OC/{today}/0001", "order_kind": "conditionnement",
                       "product_id": [101, "Sirop Magnesium + Vitamine B6 200 mL"], "product_qty": 800,
                       "bom_id": [12, "OC"], "lot_id": [1, f"MGB6-{today}-001"],
                       "state": "confirmed", "sale_order": "S00042",
                       "target_fill_g": 200.0, "fill_tolerance_g": 8.0, "fill_unit": "mL"},
                2001: {"id": 2001, "name": f"OF/{today}/0002", "order_kind": "fabrication",
                       "product_id": [102, "Gelules Spiruline 500 mg - pilulier 60"], "product_qty": 100,
                       "bom_id": [13, "OF"], "lot_id": [2, f"SPIR-{today}-001"],
                       "state": "confirmed", "sale_order": "S00043",
                       "target_fill_g": 500.0, "fill_tolerance_g": 25.0, "fill_unit": "mg"},
                2002: {"id": 2002, "name": f"OC/{today}/0002", "order_kind": "conditionnement",
                       "product_id": [102, "Gelules Spiruline 500 mg - pilulier 60"], "product_qty": 100,
                       "bom_id": [14, "OC"], "lot_id": [2, f"SPIR-{today}-001"],
                       "state": "confirmed", "sale_order": "S00043",
                       "target_fill_g": 500.0, "fill_tolerance_g": 25.0, "fill_unit": "mg"},
            },
            # Odoo Quality control points = the "declencheur de controle qualite"
            "quality.point": {
                1: {"id": 1, "title": "Controle contenance (10 flacons / 30 min)",
                    "product_id": [101, "FG-MGB6-200"], "measure_on": "operation",
                    "norm": 200.0, "tolerance_min": 192.0, "tolerance_max": 208.0, "norm_unit": "mL"},
                2: {"id": 2, "title": "Vide de ligne avant demarrage",
                    "product_id": [101, "FG-MGB6-200"], "measure_on": "passfail"},
            },
        }

    def execute_kw(self, model, method, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        table = self._db.get(model)
        if table is None:
            raise OdooError(f"Unknown model {model}")

        if method == "search_read":
            domain = args[0] if args else []
            fields = kwargs.get("fields")
            rows = [r for r in table.values() if _match(r, domain)]
            return [_project(r, fields) for r in rows]
        if method == "read":
            ids = args[0] if args else []
            fields = kwargs.get("fields")
            return [_project(table[i], fields) for i in ids if i in table]
        if method == "search":
            domain = args[0] if args else []
            return [r["id"] for r in table.values() if _match(r, domain)]
        raise OdooError(f"Unsupported method {method}")


def _match(row: dict, domain: list) -> bool:
    """Minimal Odoo domain evaluator: supports [(field, '=', value)] tuples."""
    for clause in domain:
        if not isinstance(clause, (list, tuple)) or len(clause) != 3:
            continue
        field, op, value = clause
        cell = row.get(field)
        if isinstance(cell, list):  # many2one stored as [id, name]
            cell = cell[0]
        if op == "=" and cell != value:
            return False
        if op == "!=" and cell == value:
            return False
        if op == "in" and cell not in value:
            return False
    return True


def _project(row: dict, fields: list[str] | None) -> dict:
    if not fields:
        return dict(row)
    out = {"id": row["id"]}
    out.update({f: row.get(f) for f in fields})
    return out
