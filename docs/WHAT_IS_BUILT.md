# What BatchTwin actually contains

> A factual inventory of the software, written so you can answer "what does it
> do?" without overclaiming. Every number here was counted from the repository.
> Where something is a mechanism that has not yet met real customer data, it
> says so.

**As of this commit:** 18 backend modules · 6,332 backend lines · 5,019 frontend
lines · 85 API routes · 18 database tables · 141 tests · 744 translation keys
across 3 languages.

---

## 1. The core: an electronic batch record

The legal document that decides whether a lot can be sold, kept as live data
instead of paper.

| Stage | Dossier | Signed by |
|---|---|---|
| Fabrication | DFA | R. PROD |
| Conditionnement primaire | DCOI | R. PROD |
| Conditionnement secondaire | DCOII | R. PROD |
| Contrôle qualité | DCT | R. CQ |
| Libération | — | PRT |

Release is refused unless **every** prior stage is signed, all fill checks
passed, every packaging article balances, no formula change is awaiting QA, and
no deviation is open. Each refusal names exactly what is blocking it.

## 2. Digitalised dossiers — read from the customer's own Word files

`docx_forms.py` opens `word/document.xml` from Medicka's real `.docx` templates,
keeps the table structure, and classifies every cell as printed label or typed
input. Nothing is hand-transcribed: edit the Word file and the form follows.

| | DFA | DCOI | DCOII | DCT |
|---|---|---|---|---|
| Sections | 12 | 9 | 17 | 9 |
| Fillable fields | 110 | 217 | 218 | 660 |
| Tap-choices | 3 | 13 | 6 | 113 |

Two transformations that matter:

- **`S` and `NS` are two separate cells on paper** — boxes you ring with a pen.
  Rendered naively they become two dead text boxes. Adjacent choice pairs merge
  into one control: **135 conformity checks** across the four dossiers.
- **Paper pre-prints blank grids because paper cannot grow.** DCOI carries a
  92-row in-process log; DCT a 95-row compression table. Runs of ≥3 identical
  blank rows collapse to one growable template: **570 blank lines eliminated**.

## 3. Product catalog, versioned

Every dossier belongs to one product specification, and the product is the entry
point — you pick or create one before any dossier exists.

- Full identification: code, SKU, name, category, dosage form, strength,
  packaging, units/pack, manufacturer, licensor, barcode, shelf life, fill
  target/tolerance/unit, storage, notes.
- **Versioned and append-only.** A new version requires a reason; the previous
  one is marked superseded, never edited. A superseded spec cannot start a new
  batch, and a lot made against v1 still reads v1 forever.
- Changing a *specification* field forces a version; fixing a storage note does
  not. `SPEC_FIELDS` vs `EDITABLE_IN_PLACE` draws that line explicitly.
- **One template serves every product.** The Word files have the product printed
  into them; the selected specification overlays the identification block of all
  four dossiers and those cells become read-only — you change them by versioning
  the product, not by typing.

**Composition capture is optional**, three ways: manual rows; barcode/QR decoded
in-browser and resolved against *your own catalog* (no third-party lookup); or a
label photo OCR'd by a local vision model. Nothing scanned is ever saved
directly — values land marked as scanned, for review.

## 4. Compliance machinery

**Electronic signatures — 21 CFR Part 11.200.** Identity comes from a login,
never a dropdown. The password is re-entered at *every* signature, and signing
is refused if the claimed role does not match the account. PBKDF2-HMAC-SHA256,
240,000 rounds, per-user salt, constant-time compare, lockout after 5 failures.

**Tamper evidence, two independent checks.** The audit trail is append-only and
SHA-256 hash-chained. But a chain alone proves nothing against someone who can
rewrite the database and recompute every link — so the head is also appended to
`audit_anchor.log` outside the DB, itself chained. A test performs exactly that
forgery and asserts the internal check passes while the anchor rejects it.

**Deviations and CAPA.** A failed fill check or line clearance opens a deviation
automatically. Only QA closes one, closing is password-signed, root cause **and**
CAPA are both mandatory, and a reject disposition rejects the lot.

**Formula change control.** R. PROD may adjust ≤ ±5 % in-range; anything larger
or any add/remove goes to QA. R. CQ is refused outright — Control checks the
product, it never reformulates it. Reason mandatory, no self-approval.

**Packaging reconciliation.** Issued = used + returned + waste, per article, per
dossier. Variance above tolerance blocks release; an untouched line reads
*incomplete* rather than a false 100 % discrepancy.

## 5. Analytics

**Live mass balance** — real consumption including losses versus the Odoo BOM:
true cost per unit, loss cost (money Odoo never sees), yield, gap versus
theoretical.

**Predictive SPC** — X̄/R chart with Western Electric rules and a linear drift
forecast that warns before the specification is breached. Control limits use the
standard ASTM STP-15D / ISO 7870-2 constants, validated against a worked example.

**Site KPIs** — batches, right-first-time, median release cycle, deviations per
batch, material loss, average yield, a deviation Pareto, and per-line migration
progress. Below three closed batches it reports *insufficient data* rather than
a comforting 100 %.

**Energy and CO₂** per unit produced, from metered or estimated kWh.

**VÉRA** — raw-material forecasting: seasonal-trend decomposition, FEFO with
shelf-life projection, reorder point with safety stock (z = 1.65), expiry
write-off optimisation.

## 6. Beyond pharma — configurable industry profiles

The mechanics are the product; the rulebook is data. Four profiles ship, and a
customer adds an industry by dropping a JSON file in `backend/profiles/`.

| Profile | Stages | Release signed by | Formula tolerance |
|---|---|---|---|
| Pharma GMP (Annex 11 / Part 11) | 5 | PRT (pharmacist) | ±5 % |
| Cosmetics (ISO 22716) | 4 | QA | ±5 % |
| Food (HACCP / IFS) | 4 | HACCP lead | ±10 % |
| Medical device (ISO 13485) | 5 | Regulatory | ±2 % |

Switching profile never rewrites history: a batch stores the rulebook it was
opened under and is always displayed and repaired against *that* lifecycle.

## 7. Operations and resilience

**Eight failure modes** modelled with detection, behaviour, record impact and
recovery: dead sensor, power cut, Wi-Fi loss, Odoo down, failed scan, dead
tablet, phones banned in the zone, server down. The governing rule: *losing an
instrument must never block production, and must never let an unverified value
into the record silently.* A test asserts no mode halts the line.

**Offline capture** queues locally and replays with the operator's real
timestamp preserved, de-duplicated by client op id. **Signing is deliberately
excluded** — verifying a password offline would mean caching credentials on a
shared tablet.

**Telemetry is not in the batch record.** One sensor at 1 Hz is 28,800 rows per
shift; measured, that is 4.14 MB in a separate store and **one row** in the
record. Separate retention (30 days), and no write contention with the signature
transaction.

**Security and observability** — every endpoint behind a session, server-side
role gates, per-client rate limiting, security headers, JSON logs with request
id and resolved user, secret redaction.

## 8. Interfaces

Four surfaces on one design system (`#05070B`, `#6C63FF → #38BDF8`, Inter, dark
and light):

| Page | For |
|---|---|
| `/app` | Desk dashboard — the full dossier, KPIs, documents |
| `/floor` | Shop-floor tablet — scan-to-act, 60 px targets, 18 px type |
| `/vera` | Raw-material forecasting |
| `/projections` | Cost and quality projections |

Trilingual **EN / FR / AR** with full RTL, 744 keys, vendored fonts (no external
requests). Installable PWA. The server returns translation *keys*, never prose —
it has no business choosing which language an operator reads.

## 9. Odoo

`odoo_adapter.py` mirrors Odoo's real external API (`execute_kw` over XML-RPC)
against the standard models. Going live means instantiating `LiveOdoo` instead
of `MockOdoo`. `tests/test_odoo_contract.py` runs the same suite against either,
and reports **skipped** — never quietly passed — without a live instance.

---

## What is a mechanism, not yet a measured result

Stated here so nobody quotes it as evidence:

- **Material loss figures** come from simulated weighing, not Medicka's scales.
  The mechanism is verified; the magnitude is not. The honest claim is *"Odoo
  cannot see this number at all"*, not a euro amount.
- **VÉRA's inventory numbers** are computed on a deterministic seed — reproducible,
  but synthetic.
- **No live Odoo has been connected.** The contract suite makes the claim
  falsifiable; it has not yet been falsified or confirmed against a real server.
- **Label OCR** works end to end but the small local vision model available here
  returns nothing usable. The UI says so and points at a larger model.
- **The AI does not learn.** It is retrieval over static SOPs plus current-batch
  facts, and it is advisory only — a test asserts it contains no write path.
- **Not a validated system.** IQ/OQ/PQ, supplier qualification and periodic
  review are deployment activities, not code.

## What does not exist

- **A data room.** There is no financial model, no five-year projection, no IRR,
  no customer contracts or letters of intent. `Final_Presentation_Slides.md`
  references one five times as missing, and slides 5, 9 and 10 have blanks that
  depend on it.
- **Validation deliverables** (URS, IQ, OQ, PQ documents).
- **Divergence capture for the parallel run** — QA compares paper against the
  digital record by reading both; a structured comparison screen is proposed,
  not built.
