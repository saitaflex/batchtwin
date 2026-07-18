"""
Evidence for the compliance claims.

Each test here exists because a reviewer would otherwise be right to ask
"prove it". They are deliberately behavioural: they drive the real store
against a real SQLite file, not mocks.
"""
import sqlite3
import hashlib
import tempfile
import threading
import unittest
from pathlib import Path

from backend import store, auth, anchor, analytics
from backend.odoo_adapter import MockOdoo

CREDS = {
    "r_prod": ("prod.karim", "Fabrication#26"),
    "r_cq":   ("cq.sana",    "Controle#26"),
    "smq":    ("smq.leila",  "Qualite#26"),
    "prt":    ("prt.mona",   "Pharma#26"),
}


def _fresh_batch(n=0):
    """Reset the store onto a temp DB + anchor log, and seed one batch."""
    tmp = Path(tempfile.mkdtemp())
    store.DB_PATH = tmp / "t.db"
    anchor.ANCHOR_PATH = tmp / "anchor.log"
    store.init_db(reset=True)
    odoo = MockOdoo()
    ofs = odoo.search_read("mrp.production", [("order_kind", "=", "fabrication")], ["id"])
    ocs = odoo.search_read("mrp.production", [("order_kind", "=", "conditionnement")], ["id"])
    return store.create_batch_from_odoo(odoo, ofs[n]["id"], ocs[n]["id"], user="system")


def _sign(bid, stage, role, password=None):
    user, pw = CREDS[role]
    return store.sign_stage(bid, stage, user, role, "ok",
                            pw if password is None else password)


# --------------------------------------------------------------------------
# Gap 1 -- authentication and Part 11 signatures
# --------------------------------------------------------------------------
class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.bid = _fresh_batch()

    def test_password_is_required_for_every_signature(self):
        with self.assertRaises(auth.AuthError):
            store.sign_stage(self.bid, "fabrication", "prod.karim", "r_prod", "ok", "")
        with self.assertRaises(auth.AuthError):
            store.sign_stage(self.bid, "fabrication", "prod.karim", "r_prod", "ok", "wrong")
        self.assertEqual(_sign(self.bid, "fabrication", "r_prod")["stage"], "fabrication")

    def test_claimed_role_must_match_the_account(self):
        """You cannot sign as the Pharmacien by picking that role in a dropdown."""
        with self.assertRaises(PermissionError):
            store.sign_stage(self.bid, "liberation", "prod.karim", "prt", "ok",
                             "Fabrication#26")

    def test_a_stage_cannot_be_signed_twice(self):
        _sign(self.bid, "fabrication", "r_prod")
        with self.assertRaises(PermissionError):
            _sign(self.bid, "fabrication", "r_prod")

    def test_password_hashes_are_salted_and_never_reversible(self):
        a, b = auth.hash_password("SamePass#1"), auth.hash_password("SamePass#1")
        self.assertNotEqual(a, b, "equal passwords must not produce equal hashes")
        self.assertTrue(auth.verify_password("SamePass#1", a))
        self.assertFalse(auth.verify_password("SamePass#2", a))
        self.assertNotIn("SamePass", a)

    def test_short_passwords_are_refused(self):
        with self.assertRaises(ValueError):
            auth.hash_password("short")

    def test_account_locks_after_repeated_failures(self):
        with store._write_conn() as c:
            for _ in range(auth.MAX_FAILED):
                with self.assertRaises(auth.AuthError):
                    auth.check_credentials(c, "prod.karim", "nope")
            with self.assertRaises(auth.AuthError) as ctx:
                auth.check_credentials(c, "prod.karim", "Fabrication#26")
        self.assertIn("verrouille", str(ctx.exception))

    def test_signature_binds_user_role_meaning_and_record_hash(self):
        _sign(self.bid, "fabrication", "r_prod")
        sig = store.get_batch(self.bid)["signatures"][0]
        self.assertEqual(sig["user"], "prod.karim")
        self.assertEqual(sig["role"], "r_prod")
        self.assertEqual(len(sig["record_hash"]), 64)


# --------------------------------------------------------------------------
# Gap 2 -- the audit chain must be provable from outside the database
# --------------------------------------------------------------------------
class AuditAnchorTests(unittest.TestCase):
    def setUp(self):
        self.bid = _fresh_batch()

    def test_editing_one_row_breaks_the_internal_chain(self):
        self.assertTrue(store.verify_chain()["valid"])
        with sqlite3.connect(store.DB_PATH) as cx:
            cx.execute("UPDATE audit SET detail='{\"forged\":1}' WHERE id=1")
        v = store.verify_chain()
        self.assertFalse(v["valid"])
        self.assertEqual(v["broken_at"], 1)

    def test_a_full_rewrite_still_fails_against_the_external_anchor(self):
        """The attack the hash chain alone cannot survive: recompute every link
        so the DB is self-consistent. Only the outside witness catches it."""
        _sign(self.bid, "fabrication", "r_prod")
        with sqlite3.connect(store.DB_PATH) as cx:
            cx.row_factory = sqlite3.Row
            cx.execute("UPDATE audit SET detail='{\"lot\":\"FORGE\"}' WHERE id=1")
            prev = store.GENESIS
            for r in cx.execute("SELECT * FROM audit ORDER BY id").fetchall():
                h = hashlib.sha256(
                    f"{prev}|{r['at']}|{r['user']}|{r['action']}|{r['detail']}|{r['batch_id']}"
                    .encode()).hexdigest()
                cx.execute("UPDATE audit SET prev_hash=?, hash=? WHERE id=?", (prev, h, r["id"]))
                prev = h
        v = store.verify_chain()
        self.assertTrue(v["internal"], "the forgery is internally consistent, as designed")
        self.assertFalse(v["valid"], "but the external anchor must reject it")
        self.assertFalse(v["anchor"]["valid"])

    def test_the_anchor_log_detects_tampering_with_itself(self):
        self.assertTrue(anchor.verify_log(anchor.ANCHOR_PATH)["valid"])
        with anchor.ANCHOR_PATH.open("a", encoding="utf-8") as fh:
            fh.write("2026-01-01T00:00:00 99 deadbeef fake\n")
        self.assertFalse(anchor.verify_log(anchor.ANCHOR_PATH)["valid"])

    def test_removing_an_anchor_line_is_detected(self):
        _sign(self.bid, "fabrication", "r_prod")
        for i in range(3):
            store.record_energy(self.bid, "fabrication", f"M{i}", 1.0, "iot", "prod.karim")
        lines = anchor.ANCHOR_PATH.read_text(encoding="utf-8").splitlines()
        self.assertGreater(len(lines), 2)
        anchor.ANCHOR_PATH.write_text("\n".join(lines[:1] + lines[2:]) + "\n", encoding="utf-8")
        self.assertFalse(anchor.verify_log(anchor.ANCHOR_PATH)["valid"])


# --------------------------------------------------------------------------
# Gap 4 -- packaging is two dossiers, and the articles must balance
# --------------------------------------------------------------------------
class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.bid = _fresh_batch()

    def test_primary_and_secondary_are_separate_signed_stages(self):
        names = [s["name"] for s in store.get_batch(self.bid)["stages"]]
        self.assertEqual(names, ["fabrication", "cond_primaire", "cond_secondaire",
                                 "qualite", "liberation"])

    def test_a_batch_with_no_stage_rows_repairs_itself(self):
        """A crashed reset or an interrupted migration used to leave a batch with
        no stages, and the dashboard died on `undefined.status`."""
        with store._write_conn() as c:
            c.execute("DELETE FROM stage WHERE batch_id=?", (self.bid,))
        names = [s["name"] for s in store.get_batch(self.bid)["stages"]]
        self.assertEqual(names, store.STAGES)

    def test_a_legacy_four_stage_batch_is_migrated_in_place(self):
        """Batches created before the DCOI/DCOII split must stay openable."""
        with store._write_conn() as c:
            c.execute("DELETE FROM stage WHERE batch_id=?", (self.bid,))
            for n in ("fabrication", "conditionnement", "qualite", "liberation"):
                c.execute("INSERT INTO stage(batch_id, name) VALUES(?,?)", (self.bid, n))
        names = [s["name"] for s in store.get_batch(self.bid)["stages"]]
        self.assertEqual(names, store.STAGES, "repaired stages must be in lifecycle order")
        self.assertNotIn("conditionnement", names, "the obsolete stage must be dropped")

    def test_repair_never_touches_a_signed_stage(self):
        _sign(self.bid, "fabrication", "r_prod")
        with store._write_conn() as c:
            c.execute("DELETE FROM stage WHERE batch_id=? AND name='qualite'", (self.bid,))
        stages = {s["name"]: s["status"] for s in store.get_batch(self.bid)["stages"]}
        self.assertEqual(stages["fabrication"], "signed")
        self.assertEqual(stages["qualite"], "pending")

    def test_articles_are_split_across_the_two_dossiers(self):
        stages = {l["code"]: l["stage"] for l in store.packaging_balance(self.bid)["lines"]}
        self.assertEqual(stages["PK-FLA-200"], "cond_primaire")
        self.assertEqual(stages["PK-ETUI"], "cond_secondaire")

    def test_variance_is_computed_and_flagged(self):
        store.set_packaging_recon(self.bid, "PK-FLA-200", "used", 790, "prod.karim")
        store.set_packaging_recon(self.bid, "PK-FLA-200", "returned", 5, "prod.karim")
        store.set_packaging_recon(self.bid, "PK-FLA-200", "waste", 5, "prod.karim")
        line = next(l for l in store.packaging_balance(self.bid)["lines"]
                    if l["code"] == "PK-FLA-200")
        self.assertEqual(line["variance"], 0)
        self.assertTrue(line["ok"])

        store.set_packaging_recon(self.bid, "PK-GOB", "used", 700, "prod.karim")
        bad = next(l for l in store.packaging_balance(self.bid)["lines"]
                   if l["code"] == "PK-GOB")
        self.assertEqual(bad["variance"], 100)
        self.assertFalse(bad["ok"])

    def test_release_is_blocked_while_articles_do_not_balance(self):
        _sign(self.bid, "fabrication", "r_prod")
        store.set_packaging_recon(self.bid, "PK-FLA-200", "used", 700, "prod.karim")
        _sign(self.bid, "cond_primaire", "r_prod")
        _sign(self.bid, "cond_secondaire", "r_prod")
        _sign(self.bid, "qualite", "r_cq")
        with self.assertRaises(PermissionError) as ctx:
            _sign(self.bid, "liberation", "prt")
        self.assertIn("articles de conditionnement", str(ctx.exception))


# --------------------------------------------------------------------------
# Gap 5 -- deviations open by themselves and gate the release
# --------------------------------------------------------------------------
class DeviationTests(unittest.TestCase):
    def setUp(self):
        self.bid = _fresh_batch()

    def _fail_qc(self):
        return store.add_qc_sample(
            self.bid, [200, 200, 199, 201, 200, 200, 178, 200, 200, 200], "cq.sana")

    def test_a_failed_fill_check_opens_a_deviation(self):
        self.assertEqual(self._fail_qc()["verdict"], "FAIL")
        devs = store.list_deviations(self.bid)
        self.assertEqual(len(devs), 1)
        self.assertEqual(devs[0]["kind"], "qc_fail")
        self.assertEqual(devs[0]["severity"], "critical")
        self.assertIn("178", devs[0]["detail"])

    def test_a_failed_line_clearance_opens_a_deviation(self):
        item = store.get_batch(self.bid)["checklist"][0]["id"]
        store.update_checklist(item, 0, "zone non videe", "prod.karim", "resp.prod")
        self.assertEqual(store.list_deviations(self.bid)[0]["kind"], "line_clearance")

    def test_repeated_failures_do_not_duplicate_the_record(self):
        self._fail_qc()
        self._fail_qc()
        kinds = [d["kind"] for d in store.list_deviations(self.bid)]
        self.assertEqual(kinds.count("qc_fail"), 1)

    def test_only_qa_can_close_and_closure_needs_cause_and_capa(self):
        self._fail_qc()
        dev = store.list_deviations(self.bid)[0]["id"]
        with self.assertRaises(PermissionError):
            store.close_deviation(dev, "prod.karim", "r_prod", "Fabrication#26",
                                  "accept", "cause", "capa")
        with self.assertRaises(ValueError):
            store.close_deviation(dev, "smq.leila", "smq", "Qualite#26",
                                  "accept", "", "capa")
        with self.assertRaises(ValueError):
            store.close_deviation(dev, "smq.leila", "smq", "Qualite#26",
                                  "accept", "cause", "")
        with self.assertRaises(auth.AuthError):
            store.close_deviation(dev, "smq.leila", "smq", "bad-password",
                                  "accept", "cause", "capa")
        out = store.close_deviation(dev, "smq.leila", "smq", "Qualite#26",
                                    "rework", "Buse usee", "Remplacement + requalification")
        self.assertEqual(out["status"], "closed")

    def test_an_open_deviation_blocks_release(self):
        self._fail_qc()
        with self.assertRaises(PermissionError) as ctx:
            _sign(self.bid, "liberation", "prt")
        self.assertIn("deviation", str(ctx.exception))

    def test_a_rejected_disposition_rejects_the_lot(self):
        self._fail_qc()
        dev = store.list_deviations(self.bid)[0]["id"]
        store.close_deviation(dev, "prt.mona", "prt", "Pharma#26", "reject",
                              "Sous-remplissage", "Requalification remplisseuse")
        self.assertEqual(store.get_batch(self.bid)["state"], "rejected")
        with self.assertRaises(PermissionError):
            _sign(self.bid, "liberation", "prt")


# --------------------------------------------------------------------------
# Gap 6 -- offline capture replays exactly once; signing stays online-only
# --------------------------------------------------------------------------
class OfflineReplayTests(unittest.TestCase):
    def setUp(self):
        self.bid = _fresh_batch()

    def test_signing_is_not_an_offline_operation(self):
        """Deliberate: verifying a password offline would mean caching
        credentials on a shared tablet."""
        self.assertNotIn("sign", store.OFFLINE_KINDS)

    def test_a_replayed_operation_is_applied_only_once(self):
        line = store.get_batch(self.bid)["dispense"][0]
        store.record_dispense(line["id"], 100.0, 1.0, "prod.karim")
        store.mark_applied("op-1", "dispense", self.bid, "2026-07-18T09:00:00+01:00", {"ok": True})
        self.assertIsNotNone(store.already_applied("op-1"))
        # a second delivery of the same op must be recognised, not re-applied
        store.mark_applied("op-1", "dispense", self.bid, "2026-07-18T09:00:00+01:00", {"ok": True})
        with store._conn() as c:
            n = c.execute("SELECT COUNT(*) n FROM applied_op WHERE op_id='op-1'").fetchone()["n"]
        self.assertEqual(n, 1)

    def test_the_time_the_operator_acted_is_preserved(self):
        """ALCOA+ 'Contemporaneous': the record must show when work happened,
        not merely when the tablet reconnected."""
        acted = "2026-07-18T09:00:00+01:00"
        store.mark_applied("op-2", "qc", self.bid, acted, {"ok": True})
        entries = store.get_audit(self.bid)
        replay = [e for e in entries if e["action"] == "offline.replay"]
        self.assertTrue(replay)
        self.assertIn(acted, replay[-1]["detail"])


# --------------------------------------------------------------------------
# Gap 7 -- concurrency
# --------------------------------------------------------------------------
class ConcurrencyTests(unittest.TestCase):
    def test_parallel_writers_do_not_lose_or_corrupt_records(self):
        bid = _fresh_batch()
        lines = [d["id"] for d in store.get_batch(bid)["dispense"]]
        errors = []

        def worker(line_id, value):
            try:
                store.record_dispense(line_id, value, 0.5, "prod.karim")
            except Exception as e:                       # noqa: BLE001 - reported below
                errors.append(repr(e))

        threads = [threading.Thread(target=worker, args=(lid, 10.0 + i))
                   for i, lid in enumerate(lines)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], "concurrent writers must not error")
        rows = store.get_batch(bid)["dispense"]
        self.assertTrue(all(r["qty_dispensed"] is not None for r in rows))
        self.assertTrue(store.verify_chain()["valid"],
                        "the audit chain must survive concurrent appends")

    def test_concurrent_signatures_produce_exactly_one_signature(self):
        """Two tablets hitting 'sign' at the same instant must not both win."""
        bid = _fresh_batch()
        results, errors = [], []

        def worker():
            try:
                results.append(_sign(bid, "fabrication", "r_prod"))
            except Exception as e:                       # noqa: BLE001
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 1, f"expected one winner, got {len(results)}")
        self.assertEqual(len(errors), 3)
        sigs = store.get_batch(bid)["signatures"]
        self.assertEqual(len([s for s in sigs if s["stage"] == "fabrication"]), 1)

    def test_the_audit_chain_holds_under_parallel_appends(self):
        bid = _fresh_batch()
        def worker(i):
            store.record_energy(bid, "fabrication", f"M{i}", 1.5, "iot", "prod.karim")
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        v = store.verify_chain()
        self.assertTrue(v["valid"], f"chain broke at {v.get('broken_at')}")


# --------------------------------------------------------------------------
# Gap 8 -- the SPC maths, checked against published constants and known data
# --------------------------------------------------------------------------
class SPCValidationTests(unittest.TestCase):
    """X-bar/R control limits use the standard ASTM/ISO 7870 constants. If these
    drift, every control chart in the product is silently wrong."""

    def test_subgroup_constants_match_the_published_table(self):
        # ASTM STP-15D / ISO 7870-2, subgroup size n = 10
        self.assertAlmostEqual(analytics.D2[10], 3.078, places=3)
        self.assertAlmostEqual(analytics.D3_[10], 0.223, places=3)
        self.assertAlmostEqual(analytics.D4[10], 1.777, places=3)

    def test_control_limits_from_a_worked_example(self):
        """Ten subgroups, mean 200.0, mean range 6.0, n=10.
        A2 = 3/(d2*sqrt(n)) -> UCL = xbar + A2*Rbar."""
        samples = [{"taken_at": f"2026-07-18T10:{i:02d}:00", "mean": 200.0, "rng": 6.0,
                    "verdict": "PASS", "measurements": "[]"} for i in range(10)]
        out = analytics.spc(samples, 200.0, 192.0, 208.0)
        cl = out["control_limits"]
        expected = 3.0 / (analytics.D2[10] * (10 ** 0.5)) * 6.0
        self.assertAlmostEqual(cl["x_ucl"], 200.0 + expected, places=2)
        self.assertAlmostEqual(cl["x_lcl"], 200.0 - expected, places=2)
        self.assertAlmostEqual(cl["r_ucl"], analytics.D4[10] * 6.0, places=2)

    def test_a_stable_process_raises_no_signal(self):
        samples = [{"taken_at": f"2026-07-18T10:{i:02d}:00",
                    "mean": 200.0 + (0.2 if i % 2 else -0.2), "rng": 5.0,
                    "verdict": "PASS", "measurements": "[]"} for i in range(12)]
        out = analytics.spc(samples, 200.0, 192.0, 208.0)
        self.assertEqual(out["signals"], [], "an in-control process must not alarm")

    def test_a_sustained_downward_trend_is_forecast_before_it_breaches(self):
        samples = [{"taken_at": f"2026-07-18T10:{i * 30 // 60:02d}:{i * 30 % 60:02d}:00",
                    "mean": 200.0 - 0.8 * i, "rng": 5.0, "verdict": "PASS",
                    "measurements": "[]"} for i in range(10)]
        out = analytics.spc(samples, 200.0, 192.0, 208.0)
        self.assertIsNotNone(out["forecast"], "a clear drift must be forecast")
        self.assertIn("LSL", out["forecast"]["toward"])
        self.assertGreater(out["forecast"]["samples_to_spec_breach"], 0)

    def test_no_forecast_is_invented_from_too_little_data(self):
        samples = [{"taken_at": "2026-07-18T10:00:00", "mean": 200.0, "rng": 5.0,
                    "verdict": "PASS", "measurements": "[]"}]
        self.assertIsNone(analytics.spc(samples, 200.0, 192.0, 208.0)["forecast"])


# --------------------------------------------------------------------------
# Gap 9 -- the AI is structurally incapable of writing to a GMP record
# --------------------------------------------------------------------------
class AssistantReadOnlyTests(unittest.TestCase):
    def test_the_assistant_module_never_writes(self):
        """Not a promise in a doc: the module must contain no write path."""
        from backend import assistant
        src = Path(assistant.__file__).read_text(encoding="utf-8")
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "DROP ",
                          "sign_stage", "close_deviation", "record_dispense",
                          "save_form_field", "set_packaging_recon", "_write_conn"):
            self.assertNotIn(forbidden, src,
                             f"assistant.py must not reference '{forbidden}'")

    def test_the_assistant_reads_facts_through_the_read_only_path(self):
        from backend import assistant
        bid = _fresh_batch()
        facts = assistant.batch_facts(bid)
        text = facts[0] if isinstance(facts, tuple) else facts
        self.assertIsInstance(text, str)
        self.assertIn("Lot:", text)


# --------------------------------------------------------------------------
# API authorisation -- identity comes from the session, never the request body
# --------------------------------------------------------------------------
class ApiAuthorisationTests(unittest.TestCase):
    """Regression guard for the worst bug this project has had.

    Before this, 73 endpoints existed and one checked the session: an anonymous
    caller could POST {"role": "smq"} and approve a formula change, or wipe the
    database. The role checks were real; the role they checked was whatever the
    caller claimed.
    """

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend import main
        _fresh_batch()
        cls.client = TestClient(main.app)

    def _token(self, user, password):
        r = self.client.post("/api/login", json={"username": user, "password": password})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["token"]

    def test_anonymous_callers_are_refused_everywhere(self):
        attacks = [
            ("post", "/api/batch/1/dispense/1", {"user": "x", "role": "r_prod",
                                                 "dispensed": 999, "loss": 0}),
            ("post", "/api/batch/1/units", {"user": "x", "role": "r_prod", "good_units": 99999}),
            ("post", "/api/batch/1/changes", {"user": "x", "role": "smq", "kind": "add",
                                              "material": "Poison", "new_qty": 50, "reason": "x"}),
            ("post", "/api/products", {"user": "x", "role": "smq", "code": "HACK",
                                       "name": "F", "dosage_form": "gelule"}),
            ("post", "/api/seed?reset=true", {}),
            ("get", "/api/audit", None),
            ("get", "/api/batch/1", None),
            ("get", "/api/batch/1/report.pdf", None),
        ]
        for method, url, payload in attacks:
            r = (self.client.post(url, json=payload) if method == "post"
                 else self.client.get(url))
            self.assertEqual(r.status_code, 401, f"{method.upper()} {url} was not refused")

    def test_the_claimed_role_in_the_body_is_ignored(self):
        """A production operator cannot become QA by saying so."""
        tok = self._token("prod.karim", "Fabrication#26")
        h = {"Authorization": f"Bearer {tok}"}
        r = self.client.post("/api/products", headers=h,
                             json={"user": "smq.leila", "role": "smq", "code": "HACK2",
                                   "name": "F", "dosage_form": "gelule"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("r_prod", r.json()["detail"])

    def test_destructive_operations_require_quality_assurance(self):
        prod = {"Authorization": f"Bearer {self._token('prod.karim', 'Fabrication#26')}"}
        qa = {"Authorization": f"Bearer {self._token('smq.leila', 'Qualite#26')}"}
        self.assertEqual(self.client.post("/api/seed?reset=true", json={},
                                          headers=prod).status_code, 403)
        self.assertEqual(self.client.post("/api/seed?reset=true", json={},
                                          headers=qa).status_code, 200)

    def test_the_audit_trail_records_the_session_user(self):
        tok = self._token("prod.karim", "Fabrication#26")
        h = {"Authorization": f"Bearer {tok}"}
        bid = self.client.get("/api/batches", headers=h).json()[0]["id"]
        line = self.client.get(f"/api/batch/{bid}", headers=h).json()["batch"]["dispense"][0]["id"]
        # claim to be someone else in the body
        self.client.post(f"/api/batch/{bid}/dispense/{line}", headers=h,
                         json={"user": "prt.mona", "role": "prt", "dispensed": 5, "loss": 0})
        entries = self.client.get(f"/api/audit?batch_id={bid}", headers=h).json()["entries"]
        recorded = [e["user"] for e in entries if e["action"] == "dispense.record"]
        self.assertIn("prod.karim", recorded)
        self.assertNotIn("prt.mona", recorded, "the body must never set the actor")

    def test_an_invalid_token_is_refused(self):
        r = self.client.get("/api/batches", headers={"Authorization": "Bearer not-a-token"})
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
