"""
The product catalog and its versioning rules.

The point of versioning here is not tidiness: a batch released three years ago
must still read against the specification it was actually made to. If editing a
product could change an old dossier, the record would be worthless.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from backend import store, anchor, products, docx_forms
from backend.odoo_adapter import MockOdoo

DOSSIER = Path(__file__).resolve().parents[1] / "dossier"


def _fresh():
    tmp = Path(tempfile.mkdtemp())
    store.DB_PATH = tmp / "t.db"
    anchor.ANCHOR_PATH = tmp / "anchor.log"
    store.init_db(reset=True)


def _orders(odoo):
    ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
    ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
    return ofs[0]["id"], ocs[0]["id"]


class CatalogTests(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_the_catalog_seeds_from_the_real_dossiers(self):
        with store._conn() as c:
            listing = products.listing(c)
        codes = {p["code"] for p in listing}
        self.assertTrue({"PF990", "PF994", "PF954"} <= codes,
                        "the products named in the .docx dossiers must exist")
        self.assertTrue(all(p["version"] == 1 and p["status"] == "active" for p in listing))

    def test_a_product_needs_code_name_and_dosage_form(self):
        with store._write_conn() as c:
            for bad in ({"name": "X", "dosage_form": "gelule"},
                        {"code": "PFX", "dosage_form": "gelule"},
                        {"code": "PFX", "name": "X"}):
                with self.assertRaises(products.ProductError):
                    products.create(c, bad, [], "smq.leila")

    def test_a_duplicate_code_is_refused(self):
        with store._write_conn() as c:
            with self.assertRaises(products.ProductError) as ctx:
                products.create(c, {"code": "PF990", "name": "Autre",
                                    "dosage_form": "gelule"}, [], "smq.leila")
        self.assertIn("existe deja", str(ctx.exception))

    def test_nutrition_is_optional(self):
        with store._write_conn() as c:
            p = products.create(c, {"code": "PF777", "name": "Sans composition",
                                    "dosage_form": "gelule"}, [], "smq.leila")
        self.assertEqual(p["nutrients"], [])

    def test_nutrients_round_trip_with_their_source(self):
        with store._write_conn() as c:
            p = products.create(
                c, {"code": "PF778", "name": "Avec composition", "dosage_form": "comprime"},
                [{"label": "Calcium", "amount": "500", "unit": "mg",
                  "basis": "per_dose", "nrv_pct": 62.5, "source": "scan_label"}],
                "smq.leila")
        self.assertEqual(len(p["nutrients"]), 1)
        n = p["nutrients"][0]
        self.assertEqual(n["label"], "Calcium")
        self.assertEqual(n["source"], "scan_label",
                         "a scanned value must stay identifiable as scanned")

    def test_a_product_can_be_found_by_its_barcode(self):
        with store._conn() as c:
            p = products.by_barcode(c, "6194000994015")
        self.assertIsNotNone(p)
        self.assertEqual(p["code"], "PF994")


class VersioningTests(unittest.TestCase):
    def setUp(self):
        _fresh()
        with store._conn() as c:
            self.v1 = products.active(c, "PF201")

    def test_a_new_version_requires_a_reason(self):
        with store._write_conn() as c:
            with self.assertRaises(products.ProductError):
                products.new_version(c, self.v1["id"], {"strength": "x"}, None, "  ", "smq.leila")

    def test_a_new_version_supersedes_the_previous_one(self):
        with store._write_conn() as c:
            v2 = products.new_version(c, self.v1["id"], {"fill_target": 250.0},
                                      None, "Passage au flacon 250 mL", "smq.leila")
            old = products.get(c, self.v1["id"])
        self.assertEqual(v2["version"], 2)
        self.assertEqual(v2["status"], "active")
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["superseded_by"], v2["id"])
        self.assertEqual(old["fill_target"], 200.0, "the old spec must be untouched")

    def test_nutrients_carry_forward_unless_replaced(self):
        with store._write_conn() as c:
            v2 = products.new_version(c, self.v1["id"], {}, None, "Rev. packaging", "smq.leila")
        self.assertEqual(len(v2["nutrients"]), len(self.v1["nutrients"]))

    def test_specification_fields_cannot_be_edited_in_place(self):
        with store._write_conn() as c:
            with self.assertRaises(products.ProductError):
                products.update_in_place(c, self.v1["id"], {"strength": "999 mg"}, "smq.leila")
            p = products.update_in_place(c, self.v1["id"],
                                         {"storage": "15-25 °C"}, "smq.leila")
        self.assertEqual(p["storage"], "15-25 °C")
        self.assertEqual(p["version"], 1, "a note fix must not force a version")


class BatchBindingTests(unittest.TestCase):
    def setUp(self):
        _fresh()
        self.odoo = MockOdoo()
        self.of, self.oc = _orders(self.odoo)
        with store._conn() as c:
            self.v1 = products.active(c, "PF201")

    def test_a_batch_takes_its_parameters_from_the_specification(self):
        bid = store.create_batch_for_product(self.odoo, self.v1["id"], self.of, self.oc, "system")
        b = store.get_batch(bid)
        self.assertEqual(b["product_id"], self.v1["id"])
        self.assertEqual(b["target_fill_g"], self.v1["fill_target"])
        self.assertEqual(b["fill_unit"], self.v1["fill_unit"])
        self.assertTrue(b["lot_name"].startswith("PF201-"))

    def test_an_old_batch_keeps_reading_its_original_specification(self):
        old_batch = store.create_batch_for_product(self.odoo, self.v1["id"],
                                                   self.of, self.oc, "system")
        with store._write_conn() as c:
            v2 = products.new_version(c, self.v1["id"], {"fill_target": 250.0},
                                      None, "Flacon 250 mL", "smq.leila")
        new_batch = store.create_batch_for_product(self.odoo, v2["id"],
                                                   self.of, self.oc, "system")
        self.assertEqual(store.get_batch(old_batch)["target_fill_g"], 200.0)
        self.assertEqual(store.get_batch(old_batch)["product_spec"]["version"], 1)
        self.assertEqual(store.get_batch(new_batch)["target_fill_g"], 250.0)
        self.assertEqual(store.get_batch(new_batch)["product_spec"]["version"], 2)

    def test_a_superseded_specification_cannot_start_a_new_batch(self):
        with store._write_conn() as c:
            products.new_version(c, self.v1["id"], {}, None, "Rev.", "smq.leila")
        with self.assertRaises(ValueError) as ctx:
            store.create_batch_for_product(self.odoo, self.v1["id"], self.of, self.oc, "system")
        self.assertIn("superseded", str(ctx.exception))

    def test_lot_numbers_do_not_collide_for_the_same_product_and_day(self):
        a = store.create_batch_for_product(self.odoo, self.v1["id"], self.of, self.oc, "system")
        b = store.create_batch_for_product(self.odoo, self.v1["id"], self.of, self.oc, "system")
        self.assertNotEqual(store.get_batch(a)["lot_name"], store.get_batch(b)["lot_name"])


class DossierAdaptationTests(unittest.TestCase):
    """One template, every product -- which is the whole point of the feature."""

    def setUp(self):
        _fresh()

    def _dfa(self):
        return copy.deepcopy(next(f for f in docx_forms.load_all(DOSSIER)
                                  if f["doc_key"] == "DFA"))

    def _identity(self, form):
        out = {}
        for s in form["sections"]:
            for b in s["blocks"]:
                if b["kind"] != "table":
                    continue
                for row in b["rows"]:
                    if len(row) > 1 and row[0]["type"] == "label":
                        out[row[0].get("text", "")] = row[1]
        return out

    def test_the_template_ships_hardcoded_to_one_product(self):
        ident = self._identity(self._dfa())
        self.assertIn("Probio D3", ident["Nom du produit"].get("text", ""),
                      "the Word template is per-product -- that is the problem")

    def test_the_dossier_adapts_to_the_selected_product(self):
        with store._conn() as c:
            spec = products.active(c, "PF954")       # Calcimax, a tablet
        form = self._dfa()
        n = store.apply_product_to_form(form, spec)
        self.assertGreater(n, 3)
        ident = self._identity(form)
        self.assertEqual(ident["Nom du produit"]["text"], "Calcimax")
        self.assertEqual(ident["Code du produit"]["text"], "PF954")
        self.assertTrue(ident["Nom du produit"]["from_spec"])
        self.assertNotIn("Probio", ident["Forme galénique"].get("text", ""))

    def test_every_dossier_type_is_adapted_not_just_the_manufacturing_one(self):
        with store._conn() as c:
            spec = products.active(c, "PF994")
        for form in docx_forms.load_all(DOSSIER):
            adapted = store.apply_product_to_form(copy.deepcopy(form), spec)
            self.assertGreater(adapted, 0, f"{form['doc_key']} was not adapted")

    def test_adapting_does_not_mutate_the_shared_cache(self):
        """The parsed forms are process-wide; leaking one product's values into
        the cache would show them on every other batch."""
        with store._conn() as c:
            spec = products.active(c, "PF954")
        cached = docx_forms.load_all(DOSSIER)
        before = self._identity(copy.deepcopy(
            next(f for f in cached if f["doc_key"] == "DFA")))["Nom du produit"].get("text")
        store.apply_product_to_form(copy.deepcopy(
            next(f for f in cached if f["doc_key"] == "DFA")), spec)
        after = self._identity(next(f for f in cached if f["doc_key"] == "DFA")
                               )["Nom du produit"].get("text")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
