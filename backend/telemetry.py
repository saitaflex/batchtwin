"""
Time-series telemetry, deliberately kept OUT of the batch-record database.

The audit called this out and it is a real architectural fault: one sensor at
1 Hz over an eight-hour shift is 28,800 rows. Ten sensors on two lines is over
half a million rows a day, in the same SQLite file that holds the legal record.
Three separate problems follow:

  1. **Retention conflict.** A batch record must be kept for years. A pressure
     reading every second is worthless after a week. Putting them together means
     either keeping noise forever or vacuuming the legal record.
  2. **Backup and restore.** The record must be restorable quickly. You do not
     want to restore 200 million sensor rows to recover one dossier.
  3. **Contention.** High-frequency writes compete with signature transactions
     for the same write lock, and the signature is the one that must never wait.

So telemetry lives in its own store with its own retention, and only
**aggregates** — what the dossier actually needs to prove — are promoted into
the record. The raw series stays available for investigation until it ages out.

This module is a real separation with a deliberately small surface, so swapping
in TimescaleDB or InfluxDB later is changing one file rather than the schema of
the record. `TelemetryStore` is the seam.
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
import statistics as st
from pathlib import Path

DB_PATH = Path(__file__).with_name("telemetry.db")

# Raw readings are evidence for a few weeks, not forever. The aggregate promoted
# into the dossier is what has to survive for the retention period.
RETENTION_DAYS = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS reading (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,                     -- no FK: a different database
    machine TEXT NOT NULL,
    channel TEXT NOT NULL,                -- temperature | pressure | speed | kwh
    value REAL NOT NULL,
    unit TEXT,
    at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'iot'    -- iot | manual | estimate
);
CREATE INDEX IF NOT EXISTS idx_reading_batch ON reading(batch_id, machine, channel);
CREATE INDEX IF NOT EXISTS idx_reading_at ON reading(at);
"""


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


class TelemetryStore:
    """The seam. Swap this class for TimescaleDB and nothing else changes."""

    def __init__(self, path: Path | None = None):
        self.path = path or DB_PATH

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=10.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode = WAL")
        # Telemetry is high-volume and individually disposable: losing the last
        # few readings in a crash is acceptable, losing a signature is not.
        # That difference is precisely why they do not share a database.
        c.execute("PRAGMA synchronous = OFF")
        return c

    def init(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    def write(self, batch_id: int | None, machine: str, channel: str,
              value: float, unit: str = "", source: str = "iot",
              at: str | None = None) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO reading(batch_id, machine, channel, value, unit,"
                      " at, source) VALUES(?,?,?,?,?,?,?)",
                      (batch_id, machine, channel, value, unit, at or _now(), source))

    def write_many(self, rows: list[dict]) -> int:
        """Bulk ingest -- the path an OPC UA / Modbus collector actually uses."""
        with self._conn() as c:
            c.executemany(
                "INSERT INTO reading(batch_id, machine, channel, value, unit, at, source)"
                " VALUES(?,?,?,?,?,?,?)",
                [(r.get("batch_id"), r["machine"], r["channel"], r["value"],
                  r.get("unit", ""), r.get("at") or _now(), r.get("source", "iot"))
                 for r in rows])
        return len(rows)

    def series(self, batch_id: int, machine: str | None = None,
               channel: str | None = None, limit: int = 5000) -> list[dict]:
        q = "SELECT * FROM reading WHERE batch_id=?"
        args: list = [batch_id]
        if machine:
            q += " AND machine=?"
            args.append(machine)
        if channel:
            q += " AND channel=?"
            args.append(channel)
        q += " ORDER BY at LIMIT ?"
        args.append(limit)
        with self._conn() as c:
            return [dict(r) for r in c.execute(q, args)]

    def aggregate(self, batch_id: int) -> list[dict]:
        """What the dossier needs: per machine and channel, the statistics that
        prove the process stayed in control -- not every sample that proved it.
        """
        with self._conn() as c:
            rows = [dict(r) for r in c.execute(
                "SELECT machine, channel, unit, COUNT(*) n, MIN(value) mn,"
                " MAX(value) mx, AVG(value) avg, MIN(at) first_at, MAX(at) last_at,"
                " SUM(CASE WHEN source<>'iot' THEN 1 ELSE 0 END) manual"
                " FROM reading WHERE batch_id=? GROUP BY machine, channel",
                (batch_id,))]
        for r in rows:
            r["avg"] = round(r["avg"], 3)
            r["automatic_pct"] = round((r["n"] - r["manual"]) / r["n"] * 100) if r["n"] else None
        return rows

    def stats(self) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT COUNT(*) n, MIN(at) oldest, MAX(at) newest"
                            " FROM reading").fetchone()
            machines = c.execute("SELECT COUNT(DISTINCT machine) n FROM reading").fetchone()["n"]
        size_mb = round(self.path.stat().st_size / 1e6, 2) if self.path.exists() else 0.0
        return {"readings": row["n"], "machines": machines, "oldest": row["oldest"],
                "newest": row["newest"], "size_mb": size_mb,
                "retention_days": RETENTION_DAYS, "store": "sqlite (separate file)"}

    def prune(self, days: int = RETENTION_DAYS) -> int:
        """Age out raw readings. The dossier keeps the aggregate, so pruning
        never removes evidence the batch record depends on."""
        cutoff = (_dt.datetime.now().astimezone()
                  - _dt.timedelta(days=days)).isoformat(timespec="seconds")
        with self._conn() as c:
            cur = c.execute("DELETE FROM reading WHERE at < ? AND batch_id IS NULL"
                            " OR (at < ? AND batch_id IS NOT NULL)", (cutoff, cutoff))
            n = cur.rowcount
        return max(n, 0)


store = TelemetryStore()


def promote_to_record(batch_id: int) -> list[dict]:
    """The one-way bridge: aggregates go into the batch record, raw stays here.

    Called when a stage closes. Returns the rows the dossier should carry, so
    the record never grows with sample count.
    """
    out = []
    for a in store.aggregate(batch_id):
        out.append({
            "machine": a["machine"], "channel": a["channel"], "unit": a["unit"],
            "samples": a["n"], "min": a["mn"], "max": a["mx"], "avg": a["avg"],
            "from": a["first_at"], "to": a["last_at"],
            "automatic_pct": a["automatic_pct"],
        })
    return out
