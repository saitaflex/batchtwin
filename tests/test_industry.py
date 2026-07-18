"""
Industry profiles: the same engine under a different rulebook.

The claim being tested is that BatchTwin is not a pharma-only tool with pharma
words baked in. If a cosmetics or food manufacturer needs a code change to run
their lifecycle, the claim is false.
"""
import json
import tempfile
import unittest
from pathlib import Path

from backend import industry, store, anchor, products
from backend.odoo_adapter import MockOdoo


class ProfileValidationTests(unittest.TestCase):
    def test_every_builtin_profile_is_valid(self):
        for key in industry.BUILTIN:
            self.assertEqual(industry.load(key)["key"], key)

    def test_four_industries_ship_in_the_box(self):
        keys = {p["key"] for p in industry.available()}
        self.assertTrue({"pharma_gmp", "cosmetics", "food_haccp", "medical_device"} <= keys)

    def test_a_profile_must_end_at_release(self):
        bad = dict(industry.PHARMA_GMP)
        bad["stages"] = [s for s in bad["stages"] if s["name"] != "liberation"]
        with self.assertRaises(industry.ProfileError):
            industry.validate(bad)

    def test_a_stage_cannot_be_signed_by_an_unknown_role(self):
        bad = json.loads(json.dumps(industry.PHARMA_GMP))
        bad["stages"][0]["signer"] = "nobody"
        with self.assertRaises(industry.ProfileError):
            industry.validate(bad)

    def test_a_profile_needs_at_least_one_quality_role(self):
        bad = json.loads(json.dumps(industry.PHARMA_GMP))
        bad["qa_roles"] = []
        with self.assertRaises(industry.ProfileError):
            industry.validate(bad)

    def test_duplicate_stage_names_are_refused(self):
        bad = json.loads(json.dumps(industry.PHARMA_GMP))
        bad["stages"][1]["name"] = "fabrication"
        with self.assertRaises(industry.ProfileError):
            industry.validate(bad)

    def test_an_unknown_profile_is_an_error_not_a_silent_default(self):
        with self.assertRaises(industry.ProfileError):
            industry.load("does_not_exist")

    def test_a_customer_can_add_a_profile_without_touching_the_code(self):
        """The scalability claim in one test: a JSON file is a new industry."""
        industry.PROFILE_DIR.mkdir(exist_ok=True)
        path = industry.PROFILE_DIR / "chemicals_test.json"
        path.write_text(json.dumps({
            "key": "chemicals_test", "label": "Chimie de spécialité",
            "regulation": "REACH · ISO 9001",
            "stages": [
                {"name": "synthese", "label": "Synthèse", "doc": "DFA", "signer": "op"},
                {"name": "qualite", "label": "Analyse", "doc": "DCT", "signer": "lab"},
                {"name": "liberation", "label": "Libération", "doc": None, "signer": "qa"},
            ],
            "roles": {"op": "Opérateur", "lab": "Laboratoire", "qa": "Responsable Qualité"},
            "qa_roles": ["qa"], "change_requesters": ["op", "qa"],
            "checklist": ["Reacteur purge", "Utilites disponibles"],
            "terminology": {"batch": "Charge", "record": "Dossier de charge"},
            "rules": {"minor_tolerance_pct": 1.0, "qualification_lots": 1},
        }, ensure_ascii=False), encoding="utf-8")
        try:
            p = industry.load("chemicals_test")
            self.assertEqual(industry.stage_names(p), ["synthese", "qualite", "liberation"])
            self.assertEqual(industry.rule(p, "minor_tolerance_pct"), 1.0)
            self.assertIn("chemicals_test", {x["key"] for x in industry.available()})
        finally:
            path.unlink()


class ProfileSwitchTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        store.DB_PATH = tmp / "t.db"
        anchor.ANCHOR_PATH = tmp / "a.log"
        store.use_profile("pharma_gmp")
        store.init_db(reset=True)

    def tearDown(self):
        store.use_profile("pharma_gmp")

    def test_switching_profile_changes_the_lifecycle(self):
        self.assertEqual(len(store.STAGES), 5)
        store.use_profile("cosmetics")
        self.assertEqual(store.STAGES,
                         ["fabrication", "cond_primaire", "qualite", "liberation"])
        self.assertEqual(store.STAGE_SIGNER["liberation"], "smq",
                         "cosmetics release is signed by QA, not a pharmacist")

    def test_rules_follow_the_profile(self):
        store.use_profile("food_haccp")
        self.assertEqual(store.MINOR_TOLERANCE_PCT, 10.0)
        store.use_profile("medical_device")
        self.assertEqual(store.MINOR_TOLERANCE_PCT, 2.0)
        self.assertEqual(store.PACKAGING_VARIANCE_PCT, 0.5)

    def test_the_checklist_follows_the_profile(self):
        store.use_profile("food_haccp")
        self.assertTrue(any("CCP" in x for x in store.DEFAULT_CHECKLIST))
        store.use_profile("pharma_gmp")
        self.assertFalse(any("CCP" in x for x in store.DEFAULT_CHECKLIST))

    def test_terminology_travels_with_the_profile(self):
        store.use_profile("food_haccp")
        self.assertEqual(store.PROFILE["terminology"]["deviation"], "Non-conformité")
        store.use_profile("medical_device")
        self.assertIn("DHR", store.PROFILE["terminology"]["record"])

    def test_switching_profile_never_rewrites_an_existing_batch(self):
        """A signed record must not change because someone changed the rulebook."""
        odoo = MockOdoo()
        ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
        ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
        with store._conn() as c:
            spec = products.active(c, "PF201")
        bid = store.create_batch_for_product(odoo, spec["id"], ofs[0]["id"], ocs[0]["id"], "system")
        before = [s["name"] for s in store.get_batch(bid)["stages"]]
        self.assertEqual(len(before), 5)

        store.use_profile("cosmetics")          # 4-stage lifecycle
        after = [s["name"] for s in store.get_batch(bid)["stages"]]
        self.assertEqual(after, before,
                         "an existing batch keeps the stages it was created with")

    def test_a_new_batch_follows_the_new_profile(self):
        store.use_profile("cosmetics")
        odoo = MockOdoo()
        ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
        ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
        with store._conn() as c:
            spec = products.active(c, "PF201")
        bid = store.create_batch_for_product(odoo, spec["id"], ofs[0]["id"], ocs[0]["id"], "system")
        self.assertEqual([s["name"] for s in store.get_batch(bid)["stages"]],
                         ["fabrication", "cond_primaire", "qualite", "liberation"])


if __name__ == "__main__":
    unittest.main()
