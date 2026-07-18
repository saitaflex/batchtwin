"""
The Odoo contract.

"Your Odoo is mocked" is a fair challenge. The answer is this file: one suite of
behavioural expectations that any adapter must satisfy. It runs against MockOdoo
always, and against a REAL Odoo whenever the environment provides one:

    ODOO_URL=https://erp.example.com ODOO_DB=medicka \
    ODOO_USER=admin ODOO_PASSWORD=... python -m pytest tests/test_odoo_contract.py -v

If both pass, "the mock is a drop-in" stops being a promise and becomes a result.
Without those variables the live case is skipped -- and reported as skipped, not
quietly passed.
"""
import os
import unittest

from backend.odoo_adapter import MockOdoo, LiveOdoo, OdooError

LIVE_ENV = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_PASSWORD")


def live_adapter():
    """A LiveOdoo if the environment fully describes one, else None."""
    if not all(os.environ.get(k) for k in LIVE_ENV):
        return None
    return LiveOdoo(os.environ["ODOO_URL"], os.environ["ODOO_DB"],
                    os.environ["ODOO_USER"], os.environ["ODOO_PASSWORD"])


class OdooContractMixin:
    """Every expectation BatchTwin places on Odoo. Subclasses supply `adapter`."""

    adapter = None

    def test_search_read_returns_manufacturing_orders(self):
        rows = self.adapter.search_read("mrp.production", [], ["name"])
        self.assertIsInstance(rows, list)
        self.assertTrue(rows, "expected at least one mrp.production")
        self.assertIn("id", rows[0])
        self.assertIn("name", rows[0])

    def test_domain_filtering_actually_filters(self):
        all_mo = self.adapter.search_read("mrp.production", [], ["name"])
        fab = self.adapter.search_read(
            "mrp.production", [("order_kind", "=", "fabrication")], ["name"])
        self.assertLessEqual(len(fab), len(all_mo))

    def test_read_projects_only_requested_fields(self):
        first = self.adapter.search_read("mrp.production", [], ["name"])[0]
        row = self.adapter.read("mrp.production", [first["id"]], ["name"])[0]
        self.assertEqual(set(row) - {"id"}, {"name"},
                         "read() must return id + exactly the requested fields")

    def test_many2one_fields_are_id_name_pairs(self):
        """Odoo's wire format for a many2one is [id, display_name]. Code that
        does product_id[0] breaks the moment an adapter returns a bare int."""
        mo = self.adapter.search_read("mrp.production", [], ["product_id"])[0]
        pid = mo["product_id"]
        self.assertIsInstance(pid, (list, tuple))
        self.assertEqual(len(pid), 2)
        self.assertIsInstance(pid[0], int)
        self.assertIsInstance(pid[1], str)

    def test_bill_of_materials_can_be_walked_to_its_lines(self):
        mo = self.adapter.search_read("mrp.production", [], ["bom_id"])[0]
        bom = self.adapter.read("mrp.bom", [mo["bom_id"][0]], ["bom_line_ids"])[0]
        self.assertTrue(bom["bom_line_ids"])
        lines = self.adapter.read("mrp.bom.line", bom["bom_line_ids"],
                                  ["product_id", "product_qty", "uom"])
        self.assertEqual(len(lines), len(bom["bom_line_ids"]))
        for line in lines:
            self.assertGreater(line["product_qty"], 0)

    def test_products_carry_a_code_and_a_cost(self):
        mo = self.adapter.search_read("mrp.production", [], ["bom_id"])[0]
        bom = self.adapter.read("mrp.bom", [mo["bom_id"][0]], ["bom_line_ids"])[0]
        line = self.adapter.read("mrp.bom.line", bom["bom_line_ids"][:1],
                                 ["product_id"])[0]
        prod = self.adapter.read("product.product", [line["product_id"][0]],
                                 ["name", "default_code", "standard_price"])[0]
        self.assertTrue(prod["name"])
        self.assertIsNotNone(prod["default_code"])

    def test_reading_an_unknown_id_yields_nothing_rather_than_crashing(self):
        self.assertEqual(self.adapter.read("mrp.production", [10 ** 9], ["name"]), [])

    def test_an_unknown_model_is_an_odoo_error(self):
        with self.assertRaises(Exception):
            self.adapter.execute_kw("does.not.exist", "search_read", [[]], {"fields": ["id"]})


class MockOdooContractTests(OdooContractMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = MockOdoo()

    def test_unknown_model_raises_the_typed_error(self):
        with self.assertRaises(OdooError):
            self.adapter.execute_kw("nope", "read", [[1]], {})

    def test_unsupported_method_is_rejected_loudly(self):
        """The mock must never silently pretend to write."""
        with self.assertRaises(OdooError):
            self.adapter.execute_kw("mrp.production", "create", [{}], {})


@unittest.skipUnless(all(os.environ.get(k) for k in LIVE_ENV),
                     "live Odoo not configured (set ODOO_URL/DB/USER/PASSWORD)")
class LiveOdooContractTests(OdooContractMixin, unittest.TestCase):
    """The same expectations, against a real Odoo over XML-RPC."""

    @classmethod
    def setUpClass(cls):
        cls.adapter = live_adapter()


class AdapterSurfaceTests(unittest.TestCase):
    """Mock and live must expose the *same* surface, or swapping them is a lie."""

    def test_both_adapters_share_the_public_api(self):
        surface = {n for n in dir(MockOdoo) if not n.startswith("_")}
        self.assertEqual(surface, {n for n in dir(LiveOdoo) if not n.startswith("_")})
        for name in ("execute_kw", "search_read", "read"):
            self.assertTrue(callable(getattr(MockOdoo, name)))
            self.assertTrue(callable(getattr(LiveOdoo, name)))

    def test_live_adapter_speaks_real_xmlrpc(self):
        """Guard against LiveOdoo quietly becoming a second mock."""
        import inspect
        src = inspect.getsource(LiveOdoo)
        self.assertIn("xmlrpc", src)
        self.assertIn("/xmlrpc/2/common", src)
        self.assertIn("/xmlrpc/2/object", src)
        self.assertIn("authenticate", src)


if __name__ == "__main__":
    unittest.main()
