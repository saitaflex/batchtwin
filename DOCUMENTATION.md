# BatchTwin — le dossier de lot vivant

**Paperless GMP electronic Batch Record (eBR) for Laboratoires Medicka, built on Odoo.**

> Team — **Oussama Labidi** (leader) · Salem Amara · Ahmed Hammami
> Client — Laboratoires Medicka, Nabeul, Tunisia. GMP-certified since 2010, ~100 staff,
> 309 products (67 % oral liquids, 23 % capsules, 7 % coated tablets, 3 % gels/creams).

---

## 1. The problem

Medicka runs manufacturing on Odoo, but the **Dossier de Lot** — the legal batch record that
decides whether a lot can be sold — lives on paper. Four separate Word documents follow every
batch around the plant:

| Code | Document | Signed by |
|---|---|---|
| **DFA** | Dossier de Fabrication | R. PROD |
| **DCOI** | Dossier de Conditionnement Primaire | R. PROD |
| **DCOII** | Dossier de Conditionnement Secondaire | R. PROD |
| **DCT** | Dossier de Contrôle Qualité | R. CQ |

Consequences the client actually lives with:

- **Costing is fiction.** Odoo knows the theoretical BOM. It never learns what was really
  weighed, or what was lost to air, drip and spillage. Margin per lot is an estimate.
- **Quality is retrospective.** A fill-volume drift is discovered when someone reads the
  sheet at the end of the shift — after the product is made.
- **Release is slow.** Reviewing a paper dossier means physically chasing four documents
  and four signatures.
- **The record is fragile.** Paper can be lost, back-dated, or filled in "to look right"
  after the fact. Nothing detects it.

## 2. What BatchTwin is

A live digital twin of the batch record. The dossier is not a document you file at the end —
it is the thing you *work in*, and it computes as you fill it.

Four sections, exactly mirroring the paper lifecycle, each role-gated:

```
Fabrication  →  Conditionnement  →  Qualité  →  Libération
  R. PROD          R. PROD          R. CQ        PRT
```

Release is **blocked** unless the first three are signed, every fill-volume check passed,
and no formula change is awaiting Quality Assurance.

---

## 3. Feature reference

### 3.1 Digitalised dossiers — the real .docx, rendered fillable

`backend/docx_forms.py` opens `word/document.xml` from Medicka's own Word files, **keeps the
table structure**, and classifies every cell as either a printed label or a typed input.
Nothing is hand-transcribed: change the .docx and the form changes with it (re-parsed on
file mtime).

| Dossier | Sections | Fillable fields | Tap-choices |
|---|---|---|---|
| DFA — Fabrication | 12 | 110 | 3 |
| DCOI — Conditionnement Primaire | 9 | 217 | 13 |
| DCOII — Conditionnement Secondaire | 17 | 218 | 6 |
| DCT — Contrôle Qualité | 9 | 660 | 113 |

Field types are inferred from the pen-guides Word uses:

| On paper | Becomes |
|---|---|
| `___ / ___ / _______` | date picker |
| `… : …` | time picker |
| `..............` | text input |
| adjacent `S` \| `NS` cells | one tappable choice |
| adjacent `C` \| `NC`, `O` \| `N` cells | one tappable choice |
| a `C/NC` column header over blank cells | choice for the whole column |

**Two transformations that matter:**

*Conformity marks are two cells, not one.* On paper `S` and `NS` are separate boxes you ring
with a pen. Rendered naively they become two dead text boxes. The parser merges adjacent
choice-token pairs into a single control — **135 conformity checks** across the four dossiers.

*Paper pre-prints blank grids because paper cannot grow.* DCOI carries a 92-row in-process
control log; DCT a 95-row compression table. Any run of ≥3 identical blank rows collapses to
**one template row plus "＋ Ajouter une ligne"**. **570 blank paper lines eliminated.**

Every field saves on change, individually audited. A correction **keeps the previous value
visible** (`form.correct` carries `was:`) — never a silent overwrite. Once a stage is signed
its dossier returns HTTP 403: the record is closed.

### 3.2 Formula change control

Materials are editable, but as a **deviation workflow** — a formula is a registered document,
and free editing is exactly what an auditor attacks.

| Role | Authority |
|---|---|
| **R. PROD** | Amend a quantity **≤ ±5 %** → applies immediately (in-range adjustment). Larger, or any add/remove → **pending QA** |
| **SMQ / PRT** | Hold QA authority; their own change applies at once; they approve or reject R. PROD's requests |
| **R. CQ** | **Refused** — Control checks the product, it never reformulates it |

Enforced and tested:

- A **reason is mandatory** — no reason, HTTP 400.
- **No self-approval** — separation of duties.
- **Release blocked** while any change is pending.
- **Record locks** once fabrication is signed — a later change needs a new lot.
- Materials come only from the **QA-approved Odoo catalog** (19 items), never free text.
- Every change is hash-chained and folded into the fabrication stage hash, so the signature
  attests to the amended formula.
- The PDF gains a **"Contrôle des changements de formule"** table: before → after, reason,
  requester, QA approver, status.

### 3.3 Live mass balance and true cost

Real consumption (including losses) versus the Odoo BOM, per line and per lot:

- true material cost per unit
- loss cost — the money that never appears in Odoo
- yield %
- gap versus theoretical

This is the headline differentiator. Körber PAS-X, Werum and MasterControl *record* the batch.
BatchTwin *prices* it, live.

### 3.4 Predictive SPC

X̄/R control chart on the 10-unit fill-volume check, with Western Electric rules and a linear
drift forecast that predicts a specification breach **before** it happens — "trending toward
LSL, breach in ~N samples (~M minutes)". Indicative, not a release criterion.

### 3.5 Tamper-evident audit trail

Append-only, SHA-256 hash-chained (`prev_hash` → `hash`). Every action — field entry, weighing,
QC sample, formula change, signature — is a link. Breaking any record breaks the chain, and the
UI shows it. Targets ALCOA+, FDA 21 CFR Part 11, EU GMP Annex 11.

Electronic signatures bind **user + role + meaning + record hash + timestamp**.

### 3.6 Equipment digital twin

Real machines with real industrial protocols, live telemetry and calibration countdown:

| Line | Machines | Protocols |
|---|---|---|
| Liquid | GEA ECOMAX 500 L, GEA Ariete NS3006, Marchesini ML630 / MC-500, HERMA 400 | OPC UA, Modbus TCP, Siemens S7/PROFINET, EtherNet/IP |
| Capsule | Diosna P100, IMA Zanasi 40E, IMA Deduster, MG2 G140, HERMA 400 | OPC UA, Modbus TCP, Siemens S7, EtherNet/IP |

Calibration due dates drive OK / ALERTE / ALARME status, and appear in the PDF.

### 3.7 Energy and carbon per lot

kWh metered per stage (IoT clamp or estimate), converted at 0.40 kg CO₂/kWh into kWh and
gCO₂ **per unit produced** — a product passport line, framed for the EU Digital Product Passport.

### 3.8 AI copilot (Ollama, local)

Runs entirely on-premise — no batch data leaves the plant.

- `llama3.2` for chat, `nomic-embed-text` for real RAG over an SOP corpus (cosine retrieval,
  cited sources returned in an `X-Sources` header)
- streams NDJSON so answers appear token by token
- grounded on live batch facts: stage status, mass balance, SPC, equipment, energy
- language-aware (EN/FR/AR)
- **advisory only — it never writes to a GMP record**

### 3.9 VÉRA — inventory brain

A second surface (`/vera`) for the raw-material side. Seasonal-trend decomposition forecasting
(trend × weekday × month × Ramadan), FEFO with shelf-life projection, reorder point with safety
stock (z = 1.65), and expiry write-off optimisation.

Computed on the seeded dataset (deterministic, seed = 42):

| KPI | Value |
|---|---|
| Stock-truth gap | 1.03 % — €571 |
| Materials tracked | 19 |
| Urgent stockouts (stockout ≤ lead time) | 1 (Spiruline, J+40 vs 50 d lead) |
| Expiry exposure | €3 035 |
| Inventory value | €13 829 |
| Dead stock | €3 457 |

### 3.10 Batch record PDF

A print-faithful Dossier de Lot via ReportLab: identification block with manufacture/expiry
dates, KPI strip, line clearance, weighing with supplier / RM lot / expiry per material, change
control, packaging, SPC table with drift warning, release block with all four signatures,
equipment table, energy passport, and an integrity section carrying the audit chain head.

---

## 4. Architecture

```
Odoo (MRP / BOM / products)          ← real execute_kw XML-RPC contract
        │
   odoo_adapter.py   MockOdoo ⇄ LiveOdoo  (drop-in swap)
        │
   store.py          SQLite · GMP lifecycle · hash-chained audit
        │
   analytics.py      mass balance · KPIs · SPC · energy
   docx_forms.py     .docx → fillable form spec
   equipment.py      machine twin + protocols
   inventory.py      VÉRA forecasting engine
   assistant.py      Ollama RAG copilot
   report.py         ReportLab PDF
        │
   main.py           FastAPI · 53 routes
        │
   frontend/         vanilla HTML/CSS/JS · React+Recharts (vendored) for /vera and /projections
```

**Why a mock Odoo.** `odoo_adapter.py` mirrors Odoo's real external API —
`execute_kw(model, method, args, kwargs)` over XML-RPC — against the standard models
(`mrp.production`, `mrp.bom`, `mrp.bom.line`, `product.product`, `stock.lot`, `quality.point`).
Going live means instantiating `LiveOdoo` instead of `MockOdoo`. Nothing else changes.

**Why SQLite.** One file, zero setup, transactional. The demo just runs, and it is still a real
relational store.

### Products modelled

| Code | Product | Batch | Fill |
|---|---|---|---|
| `FG-MGB6-200` | Sirop Magnésium + Vitamine B6 200 mL | 800 units | 200 mL ± 8 |
| `FG-SPIR-60` | Gélules Spiruline 500 mg — pilulier 60 | 100 piluliers | 500 mg ± 25 |

### Routes

| Group | Endpoints |
|---|---|
| Pages | `/`, `/app`, `/floor`, `/vera`, `/projections` |
| Batch | `/api/seed`, `/api/batches`, `/api/batch/{id}`, `/api/audit`, `/api/roles` |
| Dossier forms | `/api/forms`, `/api/batch/{id}/form/{doc_key}` (GET/POST) |
| Change control | `/api/materials`, `/api/batch/{id}/changes` (GET/POST), `/api/batch/{id}/changes/{cid}` |
| Shop floor | `/api/batch/{id}/checklist/{item}`, `/dispense/{line}`, `/qc`, `/units`, `/sign`, `/codes`, `/qr` |
| Equipment & energy | `/api/batch/{id}/equipment`, `/energy`, `/energy/simulate` |
| AI | `/api/assistant/health\|chat\|chat/stream\|report` |
| VÉRA | `/api/vera/overview\|skus\|sku\|forecast\|chat\|seed` |
| Export | `/api/batch/{id}/report.pdf` |

---

## 5. Interface

- **Premium dark SaaS aesthetic** — `#05070B` plane, `#6C63FF → #A855F7 → #38BDF8` accents,
  Inter, glassmorphism, 999 px pill buttons, radial gradients.
- **Light theme** — full token set; the toggle persists in `localStorage`. Every surface uses
  `--fill` / `--hi` / `--panel` tokens rather than hardcoded `rgba(255,255,255,…)`, so both
  themes genuinely render. *Scope: the toggle is on `/app`. `/floor` (shop-floor tablet) and
  `/vera` (its own visual identity) are single-theme by design.*
- **Tablet-first header** — hidden native `<select>`s drive rich animated dropdowns with 46 px+
  touch targets and two-line rows (name over full role). The `<select>` stays the single source
  of truth, so it degrades safely.
- **Visible nav bar** — no hidden overflow menu; every destination is a 44 px pill.
- **Trilingual EN / FR / AR** with full RTL, ~405 dictionary keys, vendored Inter + Noto Arabic
  (no external font requests).
- **PWA** — manifest, service worker, maskable icons; installs as a standalone Android app.

---

## 6. Running it

```bash
pip install fastapi uvicorn reportlab segno pillow httpx
python -m uvicorn backend.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. The demo seeds itself on first load.

For the AI copilot:

```bash
ollama serve
ollama pull llama3.2
ollama pull nomic-embed-text
```

The app works without Ollama — the copilot simply reports offline.

### Tests

```bash
python -m pytest tests/ -q     # 7 passed
```

Covering docx text extraction, dossier recognition, field typing and key uniqueness, choice
merging, blank-row collapsing, and the workflow summary.

---

## 7. Honest assessment — what a judge will attack

Engineering is ahead of *evidence*. These are the real gaps, ranked.

**1. There is no authentication.** An operator picks a name from a dropdown. 21 CFR Part 11
requires two distinct identification components and re-authentication at each signing. Today
anyone can sign as the Pharmacien Responsable. Highest-impact, cheapest fix — add a password
challenge on the sign action.

**2. The audit chain lives in the database it protects.** A hash chain is only tamper-*evident*
against a verifier the attacker cannot reach. Anyone with DB access can recompute every hash.
Fix: anchor the chain head somewhere append-only — a daily log, an email to QA, the PDF footer
archived separately.

**3. Odoo is mocked.** The `LiveOdoo` adapter speaks the genuine XML-RPC contract and is a
drop-in swap, which is a good answer — but one screenshot of a real Odoo instance responding
would end the question entirely.

**4. DCOI / DCOII are not separate lifecycle stages.** Both dossiers parse and fill correctly,
but the app models a single `conditionnement` stage with one signature, where Medicka's reality
is two documents signed separately. Packaging-article reconciliation (CAPS005 / ALU001 / PVC001
counts) is not modelled.

**5. No deviation / CAPA record on QC failure.** Formula change control exists; a failed fill
check does not open a deviation.

**6. Offline signing is not supported.** The PWA caches the shell, but signing needs the server.

**7. Concurrency is untested.** One line, a handful of lots. Forty lots and three simultaneous
operators is unproven — do not claim it.

**8. The SPC forecast is not validated.** Linear regression over subgroup means with Western
Electric rules — standard and defensible, but present it as indicative.

**9. The AI is unvalidated** — which is precisely why it is advisory-only and never writes.

### Where BatchTwin genuinely differs

Against Körber PAS-X, Werum, MasterControl, Veeva and Tulip — all mature eBR platforms — the
defensible claims are narrow and real:

- **live cost and loss reconciliation per lot** — those systems record the batch, this one
  prices it as it happens
- **predictive SPC** — a drift warning before the specification is breached, not after
- **the dossier is parsed from the client's own .docx** — no re-implementation project, and
  570 pre-printed blank lines disappear on day one
- **energy and CO₂ per unit** attached to the batch record
- **fully local AI** — no batch data leaves the plant

Lead with those. Do not lead with "paperless".

---

## 8. Repository layout

```
backend/
  main.py            FastAPI app, 53 routes
  store.py           SQLite, GMP lifecycle, audit chain, change control, form entries
  odoo_adapter.py    MockOdoo / LiveOdoo behind one contract
  docx_forms.py      .docx → fillable form spec
  docx_parser.py     plain-text extraction + task hints
  analytics.py       mass balance, KPIs, SPC, energy
  equipment.py       machine twin, protocols, calibration
  inventory.py       VÉRA forecasting engine
  assistant.py       Ollama RAG copilot
  report.py          ReportLab batch record PDF
frontend/
  index.html         dashboard (/app)
  landing.html       marketing landing (/)
  vera.html          VÉRA command centre
  floor.html         shop-floor tablet mode
  projections.html   React + Recharts projections
  app.js  floor.js  vera.js  i18n.js
  icons/  vendor/    logos, PWA icons, vendored fonts and React
dossier/             the four real Medicka .docx dossiers
logo/                source logo lockups
docs/                idea-document generators (PDF + Markdown)
tests/               pytest suite
```

---

*This document is written to be read by a jury. Where a number appears it was computed by the
code in this repository, not estimated. Where a gap exists it is stated plainly above rather
than left for someone else to find.*
