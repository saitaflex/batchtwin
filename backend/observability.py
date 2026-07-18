"""
Structured logging, request correlation and basic hardening.

Two things an experienced reviewer looks for and this project did not have:

  * **Logs you can actually search.** print() and stack traces in a terminal are
    not operations. Every request gets a correlation id, and every line is JSON
    so it can be shipped to anything (journald, Loki, an ELK stack) without a
    parser.

  * **Abuse resistance at the edge.** The account lockout in auth.py stops
    guessing one account; it does nothing against someone spraying a thousand
    usernames, and nothing against a client hammering an expensive endpoint.

Deliberately dependency-free: a GMP site should not need an outbound network to
install a logging agent, and adding one more thing to validate is a real cost.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from contextvars import ContextVar

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
CURRENT_USER: ContextVar[str] = ContextVar("current_user", default="-")

LOG_LEVEL = os.environ.get("BATCHTWIN_LOG_LEVEL", "INFO").upper()
# Anything that could carry a secret never reaches a log line.
REDACT = ("password", "token", "authorization", "pw_hash", "secret", "image")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the request and user carried along."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
                  + f".{int(record.msecs):03d}",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": REQUEST_ID.get(),
            "user": CURRENT_USER.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for k, v in getattr(record, "extra_fields", {}).items():
            payload[k] = v
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup(level: str | None = None) -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(level or LOG_LEVEL)
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    # uvicorn's own access log duplicates ours in a different format
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger("batchtwin")


log = logging.getLogger("batchtwin")


def event(name: str, **fields) -> None:
    """A named, searchable business event: log.event('batch.released', lot=...)."""
    safe = {k: ("***" if any(r in k.lower() for r in REDACT) else v)
            for k, v in fields.items()}
    log.info(name, extra={"extra_fields": {"event": name, **safe}})


# ---------------------------------------------------------------------------
# Rate limiting -- a fixed-window counter per (client, bucket).
# ---------------------------------------------------------------------------
class RateLimiter:
    """In-memory limiter.

    Honest about its scope: this is per-process, so a multi-worker deployment
    needs a shared store (Redis) for a hard guarantee. For a single-site
    on-premise install -- the deployment this product actually targets -- one
    worker is the norm and this is sufficient.
    """

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)

    def check(self, key: str, bucket: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.monotonic()
        q = self._hits[(key, bucket)]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            return False, int(window_s - (now - q[0])) + 1
        q.append(now)
        return True, 0

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            for k in [k for k in self._hits if k[0] == key]:
                del self._hits[k]


limiter = RateLimiter()

# Login is the endpoint worth spraying: cheap for the attacker, expensive for us
# (PBKDF2 at 240k rounds is ~0.15 s of CPU, so it is also a DoS vector).
# Limits are per CLIENT IP. A jury or a shop floor sits behind one NAT address,
# so several people signing in look like one abusive client -- 10 attempts per
# five minutes is four people logging in twice and then a locked door. The
# account lockout in auth.py (5 failures, 15 min, per ACCOUNT) is what actually
# stops password guessing; this limit exists to stop a flood, so it is set to a
# level a real room of people cannot trip by working normally.
LIMITS = {
    "login": (60, 300),        # 60 attempts / 5 min / IP
    "scan": (20, 3600),        # vision OCR is minutes of CPU
    "ai": (60, 3600),
    "write": (600, 60),
    "read": (2000, 60),
}


def bucket_for(path: str, method: str) -> str:
    if path.endswith("/login"):
        return "login"
    if path.startswith("/api/scan"):
        return "scan"
    if path.startswith("/api/assistant") or path.startswith("/api/vera/chat"):
        return "ai"
    return "write" if method in ("POST", "PUT", "PATCH", "DELETE") else "read"


# Headers that cost nothing and close whole classes of browser attack.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",                 # the dossier must not be framed
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(self)",
    "Cross-Origin-Opener-Policy": "same-origin",
}
