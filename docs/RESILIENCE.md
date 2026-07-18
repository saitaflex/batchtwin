# Failure modes — what happens when the hardware doesn't cooperate

> A GMP auditor never asks whether the happy path works. They ask what happens
> when the sensor dies mid-batch, when the power drops, when the tablet goes flat
> with half a weighing entered.

One rule governs every answer below:

> **Losing an instrument must never block production, and must never let an
> unverified value enter the record silently.**

Those two constraints force the same design every time: degrade to a manual entry
that is *explicitly marked as manual*, keep going, and make the gap visible to QA
at release. A system that halts the line on a dead sensor gets unplugged within a
week. A system that quietly guesses gets a warning letter.

The table below is not prose — it is `backend/resilience.py::FAILURE_MODES`,
served at `GET /api/resilience`, with a test asserting no mode stops production.

---

## The eight failure modes

### 1. An IoT sensor dies during production

- **Detected:** no reading for 120 s → `stale`; 600 s → `dead`.
- **Behaviour:** production continues. The field switches to manual entry and the
  value is stored with `source='manual'`.
- **In the record:** the source is printed in the dossier, so QA sees exactly
  which values were metered and which were typed.
- **Recovery:** the sensor returns and readings resume as `iot`. Manual values
  are never retroactively overwritten.

**Why stale matters:** a screen showing the last known number when the sensor has
stopped is *worse* than a blank one — the operator cannot distinguish "steady"
from "stopped". So a silent channel is reported as silent.

### 2. Power cut

- **Behaviour:** SQLite in WAL with `synchronous=NORMAL`. A committed transaction
  survives; an in-flight one rolls back **entirely** — never half-written.
- **In the record:** the audit chain has no silent hole and stays verifiable.
- **Recovery:** on restart the operator resumes from the last committed state;
  the client's offline queue replays anything captured after the last sync.

### 3. Wi-Fi disappears in the workshop

- **Behaviour:** capture continues into a local idempotent queue (`op_id`).
  **Signing is refused** — verifying a password offline would mean caching
  credentials on a shared device.
- **In the record:** `client_at` preserves when the operator actually acted
  (ALCOA+ *Contemporaneous*), distinct from when it synchronised.
- **Recovery:** automatic replay; duplicates ignored.

### 4. Odoo is unavailable

- **Behaviour:** open batches continue normally. BatchTwin needs Odoo only to
  *create* a batch from a manufacturing order, and the integration is **read-only**
  — a fault on our side cannot corrupt the ERP.
- **Recovery:** immediate on reconnection, nothing to reconcile.

### 5. The barcode won't scan

- **Behaviour:** the field stays keyboard-editable. Scanning is a shortcut, never
  a gate.

### 6. The tablet battery dies mid-weighing

- **Behaviour:** every field saves on entry, not on form submit — only the
  keystroke in progress is lost.
- **Recovery:** the operator signs in on any other tablet and finds the batch
  exactly where it was.

### 7. Phones are banned in the production zone

- Not a failure, a site constraint. `/floor` runs on a fixed washable tablet
  mounted on the line; scanning is optional and every target is ≥44 px.

### 8. The BatchTwin server itself goes down

- **Behaviour:** capture continues offline, signing waits. If the outage is
  prolonged, **the site resumes paper for the batch in progress** — that is the
  documented fallback, not an improvisation.
- **In the record:** the paper dossier becomes the legal record for that lot and
  is referenced in BatchTwin on resumption. The parallel-run machinery in
  [MIGRATION.md](MIGRATION.md) already models exactly this.
- **Recovery:** restore from backup; the **external anchor log** confirms the
  restored database has not been altered — which is precisely the case a hash
  chain alone cannot cover.

---

## Data provenance at release

`GET /api/batch/{id}/provenance` reports what share of a lot was metered versus
typed. QA needs this: a lot where every reading was hand-entered is *complete*
but is not the same evidence as one metered end to end. The dossier shows both.

---

## Architecture note: telemetry is not in the batch record

One sensor at 1 Hz over an eight-hour shift is **28,800 rows**. Ten sensors on
two lines is over half a million rows a day. Keeping that in the same database as
the legal record creates three problems:

1. **Retention conflict** — a batch record is kept for years; a pressure reading
   is worthless after a week.
2. **Restore time** — you should not restore 200 million sensor rows to recover
   one dossier.
3. **Write contention** — high-frequency writes compete for the same lock as the
   signature transaction, which is the one that must never wait.

So `backend/telemetry.py` is a **separate store** with its own retention
(30 days) and `synchronous=OFF` — losing the last few readings in a crash is
acceptable, losing a signature is not, and that difference is exactly why they
do not share a database.

Only **aggregates** are promoted into the record: per machine and channel, the
min/max/mean and sample count that prove the process stayed in control. Measured:
28,800 readings occupy 4.14 MB in the telemetry store and add **one row** to the
batch record.

`TelemetryStore` is deliberately a thin seam — swapping in TimescaleDB or
InfluxDB is replacing one class, not migrating the schema of the legal record.

---

## What is still open

- **Retention is time-based only.** A regulator asking for raw data older than
  30 days on a specific lot would need it exported first. A per-lot "freeze raw
  data" flag is the obvious fix; not built.
- **The rate limiter is per-process.** Correct for the single-worker on-premise
  deployment this product targets; a multi-worker install needs a shared store.
- **No automated backup scheduling.** Restore is documented, but taking the
  backup is currently the customer's operational responsibility.
