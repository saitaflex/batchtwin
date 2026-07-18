"""
Operational concerns: failure modes, rate limiting, structured logging.

These are the questions a GMP auditor and a software architect ask that the
happy path never answers.
"""
import datetime as dt
import io
import json
import logging
import tempfile
import unittest
from pathlib import Path

from backend import resilience, observability, store, anchor


class FailureModeTests(unittest.TestCase):
    """Losing an instrument must never block production, and must never let an
    unverified value into the record silently."""

    def setUp(self):
        self.now = dt.datetime.now().astimezone()

    def _age(self, seconds):
        return (self.now - dt.timedelta(seconds=seconds)).isoformat()

    def test_a_live_sensor_is_usable(self):
        h = resilience.reading_health(self._age(5), self.now)
        self.assertEqual(h["state"], "live")
        self.assertTrue(h["usable"])
        self.assertFalse(resilience.manual_entry_required(h))

    def test_a_silent_sensor_becomes_stale_then_dead(self):
        """A frozen number on a screen is worse than a blank one: the operator
        cannot tell the difference between 'steady' and 'stopped'."""
        stale = resilience.reading_health(self._age(150), self.now)
        dead = resilience.reading_health(self._age(900), self.now)
        self.assertEqual(stale["state"], "stale")
        self.assertEqual(dead["state"], "dead")
        for h in (stale, dead):
            self.assertFalse(h["usable"])
            self.assertTrue(resilience.manual_entry_required(h),
                            "a dead channel must fall back to manual entry")

    def test_a_channel_that_never_reported_is_not_treated_as_zero(self):
        h = resilience.reading_health(None, self.now)
        self.assertEqual(h["state"], "never")
        self.assertFalse(h["usable"])

    def test_a_corrupt_timestamp_does_not_crash_the_dashboard(self):
        h = resilience.reading_health("not-a-date", self.now)
        self.assertEqual(h["state"], "never")

    def test_no_failure_mode_stops_production(self):
        """The rule that makes the system survivable on a real shop floor."""
        for mode in resilience.FAILURE_MODES:
            self.assertFalse(mode["blocks_release"],
                             f"{mode['id']} must not halt the line")

    def test_every_audited_failure_has_an_answer(self):
        ids = {m["id"] for m in resilience.FAILURE_MODES}
        self.assertTrue({"sensor_dead", "power_loss", "network_loss", "odoo_down",
                         "scan_fail", "tablet_dead", "no_phone_allowed",
                         "server_down"} <= ids)
        for m in resilience.FAILURE_MODES:
            for field in ("event", "detect", "behaviour", "record", "recovery"):
                self.assertTrue(m[field].strip(), f"{m['id']} lacks {field}")

    def test_offline_signing_stays_refused_in_the_documented_behaviour(self):
        net = next(m for m in resilience.FAILURE_MODES if m["id"] == "network_loss")
        self.assertIn("SIGNATURE EST REFUS", net["behaviour"].upper(),
                      "the offline boundary must be stated, not implied")

    def test_provenance_separates_metered_from_typed(self):
        """QA needs to know that a 'complete' lot was hand-typed."""
        now = self.now.isoformat()
        batch = {"energy": [{"source": "iot", "at": now}] * 8
                           + [{"source": "manual", "at": now}] * 2}
        p = resilience.batch_data_provenance(batch)
        self.assertEqual(p["readings"], 10)
        self.assertEqual(p["automatic_pct"], 80)
        self.assertTrue(p["manual_present"])

    def test_a_lot_with_no_telemetry_reports_none_not_zero(self):
        p = resilience.batch_data_provenance({"energy": []})
        self.assertEqual(p["readings"], 0)
        self.assertIsNone(p["automatic_pct"])


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        observability.limiter.reset()

    def test_repeated_login_attempts_are_throttled(self):
        """Account lockout stops guessing ONE account; it does nothing against
        spraying many usernames, and PBKDF2 makes each attempt costly for us."""
        limit, window = observability.LIMITS["login"]
        for _ in range(limit):
            ok, _ = observability.limiter.check("1.2.3.4", "login", limit, window)
            self.assertTrue(ok)
        ok, retry = observability.limiter.check("1.2.3.4", "login", limit, window)
        self.assertFalse(ok)
        self.assertGreater(retry, 0)

    def test_clients_are_limited_independently(self):
        limit, window = observability.LIMITS["login"]
        for _ in range(limit):
            observability.limiter.check("1.1.1.1", "login", limit, window)
        ok, _ = observability.limiter.check("2.2.2.2", "login", limit, window)
        self.assertTrue(ok, "one abusive client must not lock out everyone")

    def test_buckets_are_independent(self):
        limit, window = observability.LIMITS["login"]
        for _ in range(limit):
            observability.limiter.check("1.1.1.1", "login", limit, window)
        ok, _ = observability.limiter.check("1.1.1.1", "read", *observability.LIMITS["read"])
        self.assertTrue(ok, "exhausting login must not block reading")

    def test_expensive_endpoints_are_classified_correctly(self):
        self.assertEqual(observability.bucket_for("/api/login", "POST"), "login")
        self.assertEqual(observability.bucket_for("/api/scan/label", "POST"), "scan")
        self.assertEqual(observability.bucket_for("/api/assistant/chat", "POST"), "ai")
        self.assertEqual(observability.bucket_for("/api/batches", "GET"), "read")
        self.assertEqual(observability.bucket_for("/api/batches", "POST"), "write")


class StructuredLoggingTests(unittest.TestCase):
    def _capture(self, fn):
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(observability.JsonFormatter())
        log = logging.getLogger("batchtwin")
        old = log.handlers[:]
        log.handlers = [handler]
        log.setLevel(logging.INFO)
        try:
            fn()
        finally:
            log.handlers = old
        return [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]

    def test_every_line_is_valid_json(self):
        lines = self._capture(lambda: observability.event("test.event", lot="L1"))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["event"], "test.event")
        self.assertEqual(lines[0]["lot"], "L1")

    def test_secrets_never_reach_a_log_line(self):
        lines = self._capture(lambda: observability.event(
            "test.secret", password="hunter2", token="abc", authorization="Bearer x",
            lot="L1"))
        rec = lines[0]
        for field in ("password", "token", "authorization"):
            self.assertEqual(rec[field], "***", f"{field} was not redacted")
        self.assertEqual(rec["lot"], "L1", "non-secret fields must survive")
        self.assertNotIn("hunter2", json.dumps(rec))

    def test_the_request_id_is_carried_on_every_line(self):
        def emit():
            observability.REQUEST_ID.set("req-123")
            observability.CURRENT_USER.set("smq.leila")
            observability.event("test.correlated")
        rec = self._capture(emit)[0]
        self.assertEqual(rec["request_id"], "req-123")
        self.assertEqual(rec["user"], "smq.leila")


class SecurityHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend import main
        tmp = Path(tempfile.mkdtemp())
        store.DB_PATH = tmp / "t.db"
        anchor.ANCHOR_PATH = tmp / "a.log"
        store.init_db(reset=True)
        observability.limiter.reset()
        cls.client = TestClient(main.app)

    def test_hardening_headers_are_present(self):
        r = self.client.get("/api/batches")
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertIn("Referrer-Policy", r.headers)

    def test_every_response_is_traceable(self):
        r = self.client.get("/api/batches")
        self.assertTrue(r.headers.get("X-Request-Id"))

    def test_a_supplied_request_id_is_honoured(self):
        r = self.client.get("/api/batches", headers={"X-Request-Id": "trace-me"})
        self.assertEqual(r.headers["X-Request-Id"], "trace-me")


if __name__ == "__main__":
    unittest.main()
