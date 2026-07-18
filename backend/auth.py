"""
Identity and electronic signature credentials.

21 CFR Part 11.200(a) requires an electronic signature to use **two distinct
identification components** (here: user ID + password), and 11.200(a)(1)(ii)
requires *each* signing in a continuous session after the first to use at least
one of them. BatchTwin therefore asks for the password again at every signature
-- picking a name from a dropdown is not a signature.

Passwords are stored as PBKDF2-HMAC-SHA256 with a per-user salt: stdlib-only
(no bcrypt/argon2 dependency) and the algorithm NIST SP 800-132 describes for
password storage.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import datetime as _dt

PBKDF2_ROUNDS = 240_000          # ~0.15 s on a laptop; raise as hardware improves
SESSION_TTL_MIN = 30             # inactivity window before re-login
MAX_FAILED = 5                   # lock the account after this many bad passwords
LOCKOUT_MIN = 15


def hash_password(password: str, salt: bytes | None = None) -> str:
    """-> 'pbkdf2_sha256$rounds$salt_hex$hash_hex' (self-describing, upgradable)."""
    if not password or len(password) < 8:
        raise ValueError("mot de passe: 8 caracteres minimum")
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison, so a wrong password cannot be found by timing."""
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", (password or "").encode(),
                                 bytes.fromhex(salt_hex), int(rounds))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


def _now() -> _dt.datetime:
    return _dt.datetime.now().astimezone()


def _iso(t: _dt.datetime) -> str:
    return t.isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS app_user (
    username TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,                   -- r_prod | r_cq | smq | prt
    pw_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    failed_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL REFERENCES app_user(username),
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);
"""

# Demo staff. The passwords are deliberately visible in the repo because this is
# a competition demo; a real deployment seeds them from the customer directory.
DEMO_USERS = [
    ("prod.karim", "Karim Ben Salah", "r_prod", "Fabrication#26"),
    ("cq.sana",    "Sana Gharbi",     "r_cq",   "Controle#26"),
    ("smq.leila",  "Leila Trabelsi",  "smq",    "Qualite#26"),
    ("prt.mona",   "Mona Cherif",     "prt",    "Pharma#26"),
]


class AuthError(PermissionError):
    """Bad credentials, locked account, or expired session."""


def init_users(c: sqlite3.Connection, users=DEMO_USERS) -> None:
    c.executescript(SCHEMA)
    for username, full_name, role, password in users:
        c.execute(
            "INSERT INTO app_user(username, full_name, role, pw_hash, created_at)"
            " VALUES(?,?,?,?,?) ON CONFLICT(username) DO NOTHING",
            (username, full_name, role, hash_password(password), _iso(_now())))


def get_user(c: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return c.execute("SELECT * FROM app_user WHERE username=?", (username,)).fetchone()


def check_credentials(c: sqlite3.Connection, username: str, password: str) -> sqlite3.Row:
    """The single place a password is ever verified. Raises AuthError otherwise."""
    u = get_user(c, username)
    if u is None or not u["active"]:
        # Same message either way: never reveal which usernames exist.
        raise AuthError("identifiants invalides")
    now = _now()
    if u["locked_until"] and _dt.datetime.fromisoformat(u["locked_until"]) > now:
        raise AuthError(f"compte verrouille jusqu'a {u['locked_until'][11:16]}")

    if not verify_password(password, u["pw_hash"]):
        failed = (u["failed_count"] or 0) + 1
        lock = _iso(now + _dt.timedelta(minutes=LOCKOUT_MIN)) if failed >= MAX_FAILED else None
        c.execute("UPDATE app_user SET failed_count=?, locked_until=? WHERE username=?",
                  (failed, lock, username))
        raise AuthError("compte verrouille: trop de tentatives" if lock
                        else "identifiants invalides")

    c.execute("UPDATE app_user SET failed_count=0, locked_until=NULL WHERE username=?",
              (username,))
    return u


def login(c: sqlite3.Connection, username: str, password: str) -> dict:
    u = check_credentials(c, username, password)
    token = secrets.token_urlsafe(32)
    now = _iso(_now())
    c.execute("INSERT INTO session(token, username, created_at, last_seen) VALUES(?,?,?,?)",
              (token, username, now, now))
    return {"token": token, "username": u["username"],
            "full_name": u["full_name"], "role": u["role"]}


def resolve_session(c: sqlite3.Connection, token: str) -> sqlite3.Row:
    """Validate a session token and slide its inactivity window."""
    s = c.execute("SELECT * FROM session WHERE token=? AND revoked=0",
                  (token or "",)).fetchone()
    if s is None:
        raise AuthError("session invalide, reconnectez-vous")
    now = _now()
    if _dt.datetime.fromisoformat(s["last_seen"]) + _dt.timedelta(minutes=SESSION_TTL_MIN) < now:
        c.execute("UPDATE session SET revoked=1 WHERE token=?", (token,))
        raise AuthError("session expiree, reconnectez-vous")
    c.execute("UPDATE session SET last_seen=? WHERE token=?", (_iso(now), token))
    u = get_user(c, s["username"])
    if u is None or not u["active"]:
        raise AuthError("compte desactive")
    return u


def logout(c: sqlite3.Connection, token: str) -> None:
    c.execute("UPDATE session SET revoked=1 WHERE token=?", (token or "",))


def list_users(c: sqlite3.Connection) -> list[dict]:
    """Directory for the login screen. Never exposes password hashes."""
    return [{"username": r["username"], "full_name": r["full_name"], "role": r["role"]}
            for r in c.execute(
                "SELECT username, full_name, role FROM app_user WHERE active=1"
                " ORDER BY username")]
