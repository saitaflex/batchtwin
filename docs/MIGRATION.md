# Migrating off paper without stopping production

> The question every pharmaceutical customer asks first, and the one that decides
> whether they buy: *"We cannot stop the line, and we cannot let an unvalidated
> system be the legal record. So how does this actually happen?"*

The answer is that **you never switch**. You run both, product line by product
line, and the legal record changes hands only when the evidence says it can.

This is not a slide. The states below exist in the database, the release gate
enforces them, and the PDF is stamped accordingly.

---

## The principle

A GMP batch record is a legal document. Two constraints follow, and they look
contradictory:

1. You cannot pause manufacturing to change record systems.
2. You cannot make an unvalidated system the legal record.

Both are satisfied by a **parallel run**: for an agreed number of lots, the
operator fills in paper *and* BatchTwin. Paper remains legally binding. QA
compares the two. When the comparison is clean for the agreed number of lots,
that product line — and only that line — cuts over.

Nothing is migrated in bulk. Nothing is switched overnight. At no point is there
a lot without a valid legal record.

---

## The five phases

### Phase 0 — Fit and specification (2–3 weeks, no production impact)

Load the real dossiers and the product catalog. BatchTwin parses the customer's
own `.docx` templates, so this is configuration rather than development: the
identification blocks, the in-process controls and the packaging article lists
come from their documents.

Deliverables: product specifications entered and versioned, user accounts mapped
to the real signatory roles, URS and a validation plan agreed with QA.

**Exit criterion:** QA signs the validation plan.

### Phase 1 — Qualification, off-line (2 weeks, no production impact)

IQ/OQ against the customer's own data on their own hardware. Operators are
trained on lots that already closed, so mistakes cost nothing.

**Exit criterion:** IQ/OQ reports approved.

### Phase 2 — Parallel run (3 lots per product line, no production impact)

The phase that answers the question.

- The lot is created with `run_mode = 'parallel'` and **the paper dossier
  reference is mandatory** — the digital record points at the paper one it
  shadows.
- Operators complete both. Yes, this is double entry; it is temporary and it is
  the price of not stopping.
- Every digital signature is captured normally, so Part 11 behaviour is exercised
  for real.
- On completion the lot reaches state **`qualified`**, never `released`. The
  digital record cannot claim legal release while paper is the master.
- The generated PDF is stamped **QUALIFICATION** and carries a banner:
  *"DOUBLE SAISIE — CE DOCUMENT NE FAIT PAS FOI"*, naming the paper dossier that
  does.

QA reviews divergences. A divergence is a finding: either the operator entered
something differently, or the system computed something differently, and both are
worth knowing before cutover.

**Exit criterion:** `GET /api/migration` reports `ready_to_cut_over: true` — three
lots completed, fully signed, with no open deviation. Any lot with an open
deviation appears in `blocking` and holds the line back.

### Phase 3 — Cutover, one product line at a time

QA sets `run_mode = 'live'` for that line. From the next lot, BatchTwin is the
legal record and paper stops. Other product lines are untouched and stay on paper
until their own parallel run completes.

Cutting over per line rather than per site is what makes this safe: the blast
radius of a problem is one product, and the fallback — resume paper for that line
— is immediate and needs no technical intervention.

**Exit criterion:** PQ report signed for that line.

### Phase 4 — Historical records

Closed paper dossiers are **not** retyped. They stay archived exactly as they
are, for the retention period, and BatchTwin holds records from cutover onward.
Retyping historical batch records would create transcription risk for no
regulatory benefit — the paper originals remain the legal record for the lots
they cover.

---

## Timeline for a site like Medicka

Assuming 5 product lines and roughly one lot per line per week:

| Phase | Duration | Production impact |
|---|---|---|
| 0 — Fit & specification | 2–3 weeks | none |
| 1 — Qualification | 2 weeks | none |
| 2 — Parallel run (per line, 3 lots) | ~3 weeks per line, lines overlap | double entry only |
| 3 — Cutover (per line) | 1 lot | none |
| 4 — Archive | continuous | none |

**First line live in ~8 weeks. Whole site in ~4–5 months.** Zero production
stoppage at any point. The only cost to operations is double entry during each
line's parallel run.

---

## What the system enforces

| Rule | Where |
|---|---|
| A parallel lot must name the paper dossier it shadows | `set_run_mode` refuses without `paper_ref` |
| Only QA may move the legal record | `set_run_mode` is restricted to SMQ / PRT, and `/api/batch/{id}/run-mode` is role-gated server-side |
| A parallel lot can never be legally released | `sign_stage` writes state `qualified`, not `released` |
| A released lot's mode is frozen | `set_run_mode` refuses once `state = 'released'` |
| The document says which record binds | PDF stamped `QUALIFICATION` with a banner naming the paper reference |
| A line cannot cut over on bad evidence | `migration_status` requires 3 clean lots and lists blockers |

```
POST /api/batch/{id}/run-mode   {"mode": "parallel", "paper_ref": "DL-2026-0412"}
GET  /api/migration             -> per line: qualified/required, stage, blockers
```

---

## Rollback

If a problem appears after cutover, QA sets the line back to `parallel` and paper
resumes as the legal record for the next lot. No data is lost and no lot is left
without a valid record. Rollback is a role-gated field change, not a project.

---

## Odoo migration

Separate from the paper question, and simpler: BatchTwin **reads** Odoo and does
not modify it. `MockOdoo` and `LiveOdoo` implement the same `execute_kw` XML-RPC
contract, and `tests/test_odoo_contract.py` runs against either. Pointing at a
real instance is a connection string:

```bash
python -m backend.odoo_adapter --url https://erp.customer.com --db prod --user svc --password ***
```

Because the integration is read-only, connecting it cannot damage the ERP — the
worst case is that BatchTwin cannot read, and it says so.

> **Honest status:** the contract suite passes against the mock and is written to
> run against a live instance, but no live Odoo has been connected yet. That is
> the single most valuable thing to do before the defense.

---

## What this does not cover yet

Stated plainly rather than discovered later:

- **Divergence capture is manual.** QA compares paper against the digital record
  by reading both. A structured "record the paper value, show me the deltas"
  screen would make Phase 2 faster and produce a better qualification report.
  Proposed, not built.
- **No data migration tooling for other eMES systems.** The strategy above
  assumes the current record is paper. A customer coming from another electronic
  system would need an import path.
- **Validation deliverables (URS, IQ, OQ, PQ) are not templated.** They are
  named in the plan; the documents themselves are a services deliverable.
