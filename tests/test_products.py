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
            p = products.by_barcode(c, "6194000994019")
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


class MigrationTests(unittest.TestCase):
    """Parallel run: you cannot stop a GMP line to change record systems, and you
    cannot let an unvalidated system be the legal record. Both hold at once."""

    CREDS = {"r_prod": ("prod.karim", "Fabrication#26"),
             "r_cq": ("cq.sana", "Controle#26"),
             "smq": ("smq.leila", "Qualite#26"),
             "prt": ("prt.mona", "Pharma#26")}

    def setUp(self):
        _fresh()
        self.odoo = MockOdoo()
        self.of, self.oc = _orders(self.odoo)
        with store._conn() as c:
            self.spec = products.active(c, "PF201")

    def _sign(self, bid, stage, role):
        user, pw = self.CREDS[role]
        return store.sign_stage(bid, stage, user, role, "ok", pw)

    def _complete(self, bid):
        for code, vals in (("PK-FLA-200", (792, 4, 4)), ("PK-GOB", (792, 4, 4)),
                           ("PK-ETIQ", (795, 3, 2)), ("PK-ETUI", (795, 3, 2))):
            for field, v in zip(("used", "returned", "waste"), vals):
                store.set_packaging_recon(bid, code, field, v, "prod.karim")
        for stage, role in (("fabrication", "r_prod"), ("cond_primaire", "r_prod"),
                            ("cond_secondaire", "r_prod")):
            self._sign(bid, stage, role)
        store.add_qc_sample(bid, [200.0] * 10, "cq.sana")
        self._sign(bid, "qualite", "r_cq")
        self._sign(bid, "liberation", "prt")
        return store.get_batch(bid)

    def _new(self):
        return store.create_batch_for_product(self.odoo, self.spec["id"],
                                              self.of, self.oc, "system")

    def test_batches_are_live_by_default(self):
        self.assertEqual(store.get_batch(self._new())["run_mode"], "live")

    def test_only_quality_assurance_moves_the_legal_record(self):
        bid = self._new()
        with self.assertRaises(PermissionError):
            store.set_run_mode(bid, "parallel", "prod.karim", "r_prod", "DL-1")
        with self.assertRaises(PermissionError):
            store.set_run_mode(bid, "parallel", "cq.sana", "r_cq", "DL-1")
        out = store.set_run_mode(bid, "parallel", "smq.leila", "smq", "DL-1")
        self.assertEqual(out["run_mode"], "parallel")

    def test_a_parallel_lot_must_name_the_paper_dossier_it_shadows(self):
        bid = self._new()
        with self.assertRaises(ValueError):
            store.set_run_mode(bid, "parallel", "smq.leila", "smq", "   ")

    def test_a_parallel_lot_is_qualified_never_released(self):
        """The digital record must not claim legal release while paper is master."""
        bid = self._new()
        store.set_run_mode(bid, "parallel", "smq.leila", "smq", "DL-2026-0412")
        b = self._complete(bid)
        self.assertEqual(b["state"], "qualified")
        self.assertNotEqual(b["state"], "released")

    def test_a_live_lot_is_released_normally(self):
        self.assertEqual(self._complete(self._new())["state"], "released")

    def test_the_pdf_says_which_record_is_binding(self):
        from backend import report
        bid = self._new()
        store.set_run_mode(bid, "parallel", "smq.leila", "smq", "DL-2026-0412")
        pdf, _ = report.build_batch_pdf(bid)
        import fitz
        tmp = Path(tempfile.mkdtemp()) / "p.pdf"
        tmp.write_bytes(pdf)
        text = "".join(page.get_text() for page in fitz.open(tmp))
        self.assertIn("QUALIFICATION", text)
        self.assertIn("NE FAIT PAS FOI", text)
        self.assertIn("DL-2026-0412", text, "the paper dossier must be named")

    def test_a_released_lot_cannot_change_record_mode(self):
        bid = self._new()
        self._complete(bid)
        with self.assertRaises(PermissionError):
            store.set_run_mode(bid, "parallel", "smq.leila", "smq", "DL-9")

    def test_a_line_needs_clean_qualification_lots_before_cutover(self):
        for i in range(store.QUALIFICATION_LOTS):
            bid = self._new()
            store.set_run_mode(bid, "parallel", "smq.leila", "smq", f"DL-{i}")
            self._complete(bid)
        line = next(x for x in store.migration_status()["lines"] if x["code"] == "PF201")
        self.assertEqual(line["qualified"], store.QUALIFICATION_LOTS)
        self.assertTrue(line["ready_to_cut_over"])
        self.assertEqual(line["stage"], "ready")

    def test_an_open_deviation_holds_the_line_back(self):
        bid = self._new()
        store.set_run_mode(bid, "parallel", "smq.leila", "smq", "DL-X")
        store.add_qc_sample(bid, [200, 200, 200, 200, 200, 200, 150, 200, 200, 200],
                            "cq.sana")
        line = next(x for x in store.migration_status()["lines"] if x["code"] == "PF201")
        self.assertFalse(line["ready_to_cut_over"])
        self.assertTrue(line["blocking"], "a lot with an open deviation must be named")


if __name__ == "__main__":
    unittest.main()
