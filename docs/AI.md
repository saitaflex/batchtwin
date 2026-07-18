# What is AI here, and what is not

> Written because "AI-powered" is the easiest claim to make and the fastest one
> to lose under questioning. Below, every component is named as what it actually
> is. Two are machine-learning models. The rest is statistics, and that is a
> deliberate choice rather than a shortfall.

---

## The short version

| Component | What it really is | ML? |
|---|---|---|
| Batch copilot | `llama3.2` + `nomic-embed-text`, cosine retrieval over an SOP corpus | **Yes** — LLM + embeddings |
| Label reader | Vision-language model reading a nutrition label | **Yes** — VLM |
| SPC drift forecast | Ordinary least-squares regression on subgroup means | No — statistics |
| Western Electric rules | Shewhart control chart, published 1924 | No — statistics |
| VÉRA demand forecast | Seasonal decomposition with **configured** coefficients | No — a parameterised model |
| VÉRA reorder point | Textbook safety stock, z = 1.65 | No — inventory theory |
| Mass balance | Arithmetic |No |
| Projections page | Per-lot figures × a planning constant | No — extrapolation |

**Two components use machine learning. Everything else is deterministic maths,
and every coefficient in it is visible in the source.**

---

## Why deterministic is the right answer here, not a compromise

This is the part worth arguing rather than apologising for.

A GMP system has to be **validated**. An inspector asks how a number was
produced and the answer must be reproducible, documented, and identical every
time it runs. That requirement points away from learned models for anything
release-critical:

- **A control chart can be validated.** The constants come from ASTM STP-15D /
  ISO 7870-2, the arithmetic is one page, and
  `tests/test_compliance.py::SPCValidationTests` checks it against a worked
  example. An auditor can follow it end to end.
- **A trained model cannot be validated the same way.** You would have to
  qualify the training data, version the weights, prove it behaves identically
  after every retrain, and explain a specific prediction to someone with legal
  liability. That is a substantial regulatory programme, and it buys nothing
  here: fill-volume drift is a straight line, and a straight line is best fitted
  by a straight line.

So the design rule is:

> **Deterministic maths wherever a number touches release. Language models only
> where the task is language, and never with write access.**

That rule is enforced, not just stated:
`tests/test_compliance.py::AssistantReadOnlyTests` asserts `assistant.py`
contains no INSERT/UPDATE/DELETE and no reference to any mutating store
function. The AI physically cannot alter a batch record.

---

## The two components that genuinely are AI

### 1. The batch copilot — LLM with retrieval

Real retrieval-augmented generation, running **entirely on-premise** through
Ollama:

- `nomic-embed-text` embeds an SOP corpus; questions are matched by cosine
  similarity and the retrieved sources are returned in an `X-Sources` header, so
  every answer can be traced to the document it came from.
- `llama3.2` answers, grounded on live batch facts — stage status, mass balance,
  SPC signals, equipment state, energy — with NDJSON streaming.
- Trilingual, and **advisory only**.

Why local matters commercially: batch data and formulas never leave the site. A
QA Director hearing "your formulas stay on your server" relaxes; one hearing
"our cloud" opens an Annex 11 supplier-audit conversation.

**Honest limit:** it is not validated for GMP use, which is exactly why it is
read-only. It helps a supervisor understand a record; it never writes one.

### 2. The label reader — vision-language model

Photograph a nutrition label, a local VLM extracts product fields and the
composition table, and the result lands in a form **marked as scanned, for
review**. Nothing scanned is ever saved directly — an OCR guess is not a
specification.

**Honest limit:** with the small vision model available on this machine
(`granite3.2-vision:2b`) it returns nothing usable and takes ~23 s to do it. The
pipeline is correct — including an adaptive resolution ladder, because a
620×760 label costs ~18k tokens against a 16k context window — but the model is
too weak. The UI says so, names the model, and points at `llama3.2-vision`.
Manual entry is the primary path and always works.

---

## What is *not* AI, stated plainly

### The SPC drift forecast

Ordinary least squares over subgroup means, projected to the specification
limit:

```python
slope     = Σ(x-x̄)(y-ȳ) / Σ(x-x̄)²
intercept = ȳ - slope·x̄
samples_to_breach = (limit - intercept) / slope - (n-1)
```

That is a straight line fitted to ten points. Calling it AI would be an
overclaim, and it does not need to be one: **it warns you before you make
scrap**, which is the whole value. The X̄/R chart around it is Shewhart's, from
1924, with the standard Western Electric rules.

### VÉRA's demand forecast

Seasonal-trend decomposition — but the coefficients are **written by hand, not
learned**:

```python
FG_DEMAND = {"FG-MGB6-200": dict(base=175, trend=0.06,
    months=[1.25, 1.20, 1.10, ...])}          # winter-heavy immunity product
WEEKDAY = [1.08, 1.10, 1.06, 1.07, 1.12, 0.82, 0.68]   # Mon..Sun
RAMADAN = [(2026-02-18, 2026-03-19)]                    # a real local signal
```

Those numbers encode domain knowledge about a Tunisian supplement market. They
are a **reasonable starting model**, not a discovery. Anywhere VÉRA has been
called "AI-driven", that is corrected.

Where VÉRA *is* genuinely interesting has nothing to do with AI: it corrects the
stock data before forecasting it, using real consumption from the batch records
rather than the theoretical BOM. Forecasting accurately on wrong inputs is the
common failure, and that is a data-integrity idea, not a modelling one.

### The projections page

Per-lot figures multiplied by a planning constant (10 batches/week × 48 weeks).
Extrapolation, and it should be read as "if this lot is typical, here is the
year" — not as a prediction.

---

## Feasibility, honestly

If the question is *"could the AI parts be built in three days?"* — yes, and
they were, because the choice was deliberately boring:

- No training, no dataset collection, no labelling, no GPU budget.
- Ollama with off-the-shelf open weights, running locally.
- Retrieval over documents the customer already has.

The data was available on day one because it is the customer's own dossiers and
BOM. There is no cold-start problem, because nothing needs to be learned before
the system is useful.

**The genuinely hard part of this project was never the AI.** It was reading
Medicka's `.docx` templates into 1,205 fillable fields, and getting the GMP
lifecycle — signatures, gates, deviations, versioned specifications —
correct enough to be defensible.

---

## What we do not claim

- No trained or fine-tuned model. No proprietary dataset. No accuracy metric,
  because there is no classifier to measure.
- No AI in any release-critical decision path.
- No claim that the copilot is validated for GMP use — it is not, and the
  read-only boundary exists precisely because of that.
- "Predictive quality" means a regression warning you before a specification
  breach. It does not mean a learned quality model.

## The honest one-liner for a jury

> Two local models where language and vision are genuinely the problem, and
> documented statistics everywhere a number touches batch release — because in a
> regulated plant, an inspector can validate a control chart and cannot easily
> validate a black box. The AI is advisory and structurally read-only, and a
> test proves it.
