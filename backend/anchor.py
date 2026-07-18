"""
External anchoring of the audit chain.

A hash chain proves nothing on its own: whoever can write the database can
recompute every link and produce a perfectly consistent forgery. Tamper-evidence
only exists if the expected head is recorded somewhere the attacker would also
have to reach.

So after every audited write, the chain head is appended to `audit_anchor.log`
-- a plain append-only text file outside the DB, itself chained so that removing
a middle line is detectable. Each line:

    <iso timestamp> <entry_count> <chain_head> <line_hash>

where line_hash = sha256(prev_line_hash | timestamp | count | head).

In production this file belongs on write-once storage (or is mirrored to a
syslog/S3-object-lock bucket, or emailed to QA nightly). The point is that it is
*not* in the database. The PDF also prints the head, so an archived batch record
is a third independent witness.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

GENESIS = "0" * 64
ANCHOR_PATH = Path(__file__).with_name("audit_anchor.log")


def _line_hash(prev: str, at: str, count: int, head: str) -> str:
    return hashlib.sha256(f"{prev}|{at}|{count}|{head}".encode()).hexdigest()


def last_anchor(path: Path | None = None) -> dict | None:
    path = path or ANCHOR_PATH
    if not path.exists():
        return None
    line = None
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:            # cheap: the file is one short line per write
            pass
    return _parse(line) if line and line.strip() else None


def _parse(line: str) -> dict | None:
    parts = line.strip().split()
    if len(parts) != 4:
        return None
    at, count, head, lh = parts
    return {"at": at, "entries": int(count), "head": head, "line_hash": lh}


def append(at: str, count: int, head: str, path: Path | None = None) -> dict:
    """Record one chain head. Called after each audited transaction commits."""
    path = path or ANCHOR_PATH
    prev = last_anchor(path)
    prev_hash = prev["line_hash"] if prev else GENESIS
    lh = _line_hash(prev_hash, at, count, head)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{at} {count} {head} {lh}\n")
    return {"at": at, "entries": count, "head": head, "line_hash": lh}


def verify_log(path: Path | None = None) -> dict:
    """Re-derive the anchor file's own chain: catches edited or deleted lines."""
    path = path or ANCHOR_PATH
    if not path.exists():
        return {"valid": True, "lines": 0, "head": None, "reason": "no anchor file yet"}
    prev_hash = GENESIS
    n = 0
    head = None
    with path.open("r", encoding="utf-8") as fh:
        for i, raw in enumerate(fh, 1):
            if not raw.strip():
                continue
            rec = _parse(raw)
            if rec is None:
                return {"valid": False, "lines": n, "head": head,
                        "reason": f"ligne {i} malformee"}
            expect = _line_hash(prev_hash, rec["at"], rec["entries"], rec["head"])
            if expect != rec["line_hash"]:
                return {"valid": False, "lines": n, "head": head,
                        "reason": f"ligne {i}: journal d'ancrage altere"}
            prev_hash = rec["line_hash"]
            head = rec["head"]
            n += 1
    return {"valid": True, "lines": n, "head": head, "reason": None}


def cross_check(db_head: str | None, db_entries: int, path: Path | None = None) -> dict:
    """Compare what the database claims against the external witness.

    This is the check that actually catches a rewritten database: the forged
    chain will be internally consistent but its head will not match the anchor.
    """
    log = verify_log(path)
    if not log["valid"]:
        return {"valid": False, "reason": log["reason"], "anchor_head": log["head"],
                "db_head": db_head}
    anchored = last_anchor(path)
    if anchored is None:
        return {"valid": True, "reason": "aucun ancrage enregistre",
                "anchor_head": None, "db_head": db_head, "anchored_entries": 0}
    if anchored["head"] != db_head:
        return {"valid": False,
                "reason": "la base ne correspond pas au journal d'ancrage externe "
                          "-- reecriture probable",
                "anchor_head": anchored["head"], "db_head": db_head,
                "anchored_entries": anchored["entries"], "db_entries": db_entries}
    return {"valid": True, "reason": None, "anchor_head": anchored["head"],
            "db_head": db_head, "anchored_entries": anchored["entries"],
            "db_entries": db_entries, "anchor_lines": log["lines"]}


def reset(path: Path | None = None) -> None:
    """Only for demo re-seeds and tests -- never call this in production."""
    path = path or ANCHOR_PATH
    if path.exists():
        path.unlink()
