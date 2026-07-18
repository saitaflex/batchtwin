# BatchTwin — business model

> Every figure below is either **anchored** to a public reference or marked
> **[assumption]**. Assumptions are ours to defend and yours to validate before
> quoting a customer. Nothing here is presented as a measured result.

---

## 1. Who buys this

**Not** the operator who uses it, and not the IT department.

The buyer is the **Pharmacien Responsable / QA Director** — the person who
personally signs release and personally carries the regulatory risk. The
production manager is the champion (it removes their paperwork), finance
approves it (it exposes real cost per lot), and IT only has to not object.

That matters for how you sell: the pitch is **risk and traceability first**,
efficiency second. A QA Director does not buy time savings; they buy the ability
to answer an inspector.

### Target segment

| | |
|---|---|
| **Primary** | GMP manufacturers of 50–300 staff already running Odoo, still on paper batch records |
| **Sector** | Nutraceuticals, food supplements, cosmetics, small-molecule pharma, medical devices |
| **Geography** | Tunisia and Maghreb first, then francophone Africa and southern Europe |
| **Disqualified** | Sites already running a validated MES (replacement cost exceeds the pain), and sites with no ERP at all (BatchTwin assumes a BOM exists) |

**Why this segment:** enterprise MES is priced for multinationals. MasterControl's
manufacturing product starts at **$1,000/month per feature** and reviewers
specifically cite licensing limits and added cost per new site
([Capterra](https://www.capterra.com/p/148011/MasterControl/)). A hundred-person
Tunisian supplement maker cannot justify that, so they stay on paper. That gap is
the market.

### Why they choose BatchTwin over the alternatives

| Alternative | Why they don't pick it |
|---|---|
| Stay on paper | Costing is guesswork, release is slow, and an inspector finding is existential |
| Enterprise MES (Körber, MasterControl, Werum) | Priced and scoped for multinationals; 12–18 month implementations |
| Odoo Quality module alone | Records checks; does not produce a compliant Dossier de Lot, and has no Part 11 signatures |
| Build in-house | 18 months and no validation experience |

**The wedge:** BatchTwin reads the customer's *own* `.docx` dossiers. Competitors
require you to re-implement your documents in their system, which is most of the
implementation cost. We parsed Medicka's four real dossiers into 1,205 fillable
fields with no transcription. That is the demo that closes the sale.

---

## 2. Deployment: on-premise first, hybrid available

**On-premise is the default, and that is a feature, not a limitation.**

GMP customers are conservative about data residency, and the AI runs on a local
Ollama model precisely so batch data never leaves the site. A QA Director who
hears "your formulas stay on your server" relaxes; one who hears "our cloud"
starts asking about Annex 11 supplier audits.

| Model | Who it fits | What we run |
|---|---|---|
| **On-premise** (default) | Any GMP site | Customer's server or VM. We supply the appliance image and support. |
| **Hybrid** | Multi-site groups | Records stay on-site; a central read-only dashboard aggregates KPIs |
| **SaaS** | Cosmetics/food, where Part 11 pressure is lower | Managed, per-tenant isolated |

SaaS is offered but not led with. *[assumption: that GMP buyers in this segment
prefer on-premise — validate with 3 customer conversations.]*

---

## 3. What the customer gets back — KPIs and ROI

Pricing without value is just a number. This section separates three kinds of
figure, and never blurs them:

| Tag | Meaning |
|---|---|
| 📐 **Measured** | Computed by the code in this repository, from Medicka's real documents |
| 📊 **Benchmark** | Published industry figure, cited |
| 🔶 **Assumption** | Our estimate — validate before quoting |

### 3.1 Measured today

Produced by running the code against Medicka's four actual `.docx` dossiers:

| KPI | Value | How |
|---|---|---|
| Dossier fields digitalised | **1,205** | `docx_forms.load_all()` across DFA, DCOI, DCOII, DCT |
| Conformity checks made tappable | **135** | adjacent `S`/`NS`, `C`/`NC` cells merged into one control |
| Blank pre-printed paper lines eliminated | **570** | runs of ≥3 identical empty rows collapsed to a growable template |
| Dossier templates replaced by one adaptive form | **4 → 1** | the spec overlays the identification block; 7 fields per dossier |
| Manual retyping of product identity per lot | **4 → 0** | it comes from the specification |

The 570 figure is the one to say out loud. DCOI pre-prints a 92-row in-process
log and DCT a 95-row compression table, because paper cannot grow. Those rows
exist to be *mostly blank*.

### 3.2 Mechanism proven, customer data pending

The mass balance is real code on a real BOM. On the demo lot (800 units,
simulated weighing within normal tolerances) it computes:

```
theoretical cost (Odoo)   399.89 EUR
real consumed              401.06 EUR
material loss              1.56 EUR      <- invisible to Odoo entirely
true cost per unit         0.506 EUR
yield                      99.1 %
```

🔶 **The mechanism is verified; the magnitude is not.** €1.56 comes from
simulated weighing, not from Medicka's scales. The honest claim is not "we save
you €1.56 a lot" — it is **"Odoo cannot see this number at all, and after
BatchTwin you have it for every lot."** A month of real weighing turns this from
a mechanism into a business case, and it is the single most valuable thing to
collect during the parallel run.

Same status for VÉRA on the seeded dataset: stock-truth gap 1.03 % / €571,
expiry exposure €3,035, dead stock €3,457 across 19 materials. Deterministic and
reproducible, but synthetic.

### 3.3 Industry benchmarks

Not our numbers — published, and cited as such:

| Benchmark | Figure | Source |
|---|---|---|
| Batch release time reduction | **40–60 %** | [iFactory](https://ifactoryapp.com/blog/pharma-ebr-batch-record-automation) |
| QA review effort | Materially reduced via review-by-exception | [MasterControl](https://www.mastercontrol.com/gxp-lifeline/benefits-electronic-batch-records-for-batch-record-review/) |
| Error reduction, direct capture vs manual entry | up to **95 %** (one facility) | [Pharmaceutical Technology](https://www.pharmtech.com/view/electronic-batch-records-offer-advantages-beyond-automation) |

Use these to frame the *category*, never as BatchTwin's measured results.

### 3.4 ROI model for a site like Medicka

🔶 Every input is an assumption until Medicka confirms it. Shown as arithmetic
you can rerun with their real numbers, not as a conclusion.

**Inputs** — 5 product lines, ~4 lots/line/month = **240 lots/year**; QA reviewer
loaded cost €18/h; material cost €400/lot 📐 (from the demo BOM).

| Effect | Basis | Annual |
|---|---|---|
| QA review time: 3 h → 1.5 h per lot | 📊 40–60 % reduction, taken at the **low** end | 240 × 1.5 h × €18 = **€6,480** |
| Material loss made visible | 🔶 0.4 % of material spend, now measured and actionable | 240 × €400 × 0.4 % = **€384** |
| Expiry write-off avoided | 🔶 30 % of VÉRA's €3,035 exposure | **€911** |
| Deviation cost avoided | 🔶 2 fewer/yr × €1,200 | **€2,400** |
| Faster release → working capital | 🔶 excluded — real but site-specific | — |
| **Total** | | **≈ €10,200/yr** |

Against **€14,400** Standard subscription plus **€9,000** one-off implementation:

- Year 1: −€13,200 🔶
- Year 2 onward: −€4,200/yr 🔶
- **Payback: does not occur on efficiency alone.**

### 3.5 The honest conclusion

**Efficiency does not pay for this product at Medicka's scale, and pretending
otherwise would be dismantled by any investor who checks the arithmetic.**

What justifies the spend is risk:

- **A regulatory finding on batch records** is existential for a GMP site — lost
  certification, halted export, remediation costs far beyond the subscription.
  BatchTwin's answer is the hash chain with external anchoring, Part 11
  signatures, and a release gate that cannot be bypassed.
- **A recall from an undetected fill drift.** The SPC forecast warns before the
  specification is breached. One avoided recall exceeds a decade of subscription.
- **Losing a customer audit.** Producing a complete, signed, timestamped dossier
  in one click versus hunting four paper documents.

This is insurance pricing, not efficiency pricing — which is exactly why the
buyer is the person who signs release.

ROI improves sharply with scale, because QA review time is the dominant term and
it scales linearly with lots while the subscription does not:

| Lots/year | Annual benefit 🔶 | vs €14,400 subscription |
|---|---|---|
| 240 (Medicka today) | €10,200 | −€4,200 |
| **~400** | **€14,750** | **break-even** |
| 600 | €20,500 | +€6,100 |
| 700 | €23,300 | +€8,900 |

So the growth path is **larger sites, not more features** — and at Medicka's
current volume the Essential plan (€7,200) is the honest recommendation, with
Standard justified once they pass ~200 lots/year or want VÉRA.

**Say this to the jury.** "Efficiency alone doesn't pay it back at this volume;
here's the arithmetic, and here's why they buy it anyway" is a stronger answer
than a fabricated payback period.

---

## 4. Pricing

### Anchors

- Enterprise eBR: MasterControl from **$1,000/month per feature**, extra per site
  ([Capterra](https://www.capterra.com/p/148011/MasterControl/)).
- Odoo Enterprise itself: **$8.95–$76.20/user/month** depending on country, with
  the Middle East at the bottom of that range
  ([OEC.sh](https://oec.sh/odoo-pricing)). Our customers already pay this, and it
  sets their reference for what software costs.

The pricing rule that follows: **BatchTwin should cost more than the customer's
Odoo subscription and an order of magnitude less than an enterprise MES.** Above
Odoo because it carries more risk; far below MES because that is the whole point.

### Per site, per year *[assumption]*

| Plan | Scope | Price/year | Included |
|---|---|---|---|
| **Essential** | 1 line, ≤ 5 products | €7,200 | eBR, Part 11 signatures, audit trail, PDF, 10 named users |
| **Standard** | 1 site, unlimited lines | €14,400 | + SPC & drift forecast, mass balance, deviations/CAPA, VÉRA inventory, 30 users |
| **Enterprise** | Multi-site | €12,000/site + €18,000 group | + hybrid dashboard, SSO, priority SLA, unlimited users |

**Why per site and not per user:** operators are shift workers on shared tablets.
Per-user pricing punishes exactly the behaviour we want (everyone records their
own actions under their own identity), and it would push customers to share
logins — which destroys the Part 11 story we just built. Named users are capped
generously; the cap is anti-abuse, not a revenue lever.

Implied cost: at Standard, a 100-person site with 5 lines pays **€1,200/month** —
roughly €12 per employee per month, comparable to their Odoo bill.

### Services (where early revenue actually comes from)

| Item | Price | Notes |
|---|---|---|
| Implementation & dossier onboarding | €6,000–12,000 one-off | Scales with number of dossier templates |
| Validation pack (URS, IQ, OQ, PQ) | €4,500 | The deliverable QA needs to defend the system |
| Parallel-run support | €2,500/line | On-site during Phase 2 |
| Training | €900/day | |

*[assumption: all service pricing. Anchor these against what a local Odoo
integrator charges per day in Tunisia — that is the comparable the customer will
mentally use.]*

### Support and maintenance

Bundled into the subscription, not sold separately:

| Tier | Response | Included |
|---|---|---|
| Standard | Next business day | Updates, security patches, email support |
| Priority (+25%) | 4 business hours | Phone, named contact, 2 validation refreshes/year |
| Critical (Enterprise) | 1 hour, 24/7 | On-call, quarterly review |

**Regulatory-change updates are included.** A customer must never face a bill to
stay compliant — and knowing this is included removes the main objection to
subscription pricing in a regulated industry.

### Unit economics *[assumption]*

At Standard, on-premise, per site:

```
Revenue                        €14,400/yr
  Support & updates             -€2,400   (~2 days/yr engineering)
  Validation refresh            -€1,200
  Hosting                            €0   (customer's hardware)
Gross margin                    €10,800   (75%)
```

Software margins are high; the constraint is **implementation capacity**, not
cost. That shapes the growth plan: partner with existing Odoo integrators rather
than hire implementation staff, because they already have the customer
relationships and the ERP skills.

---

## 5. Licensing

**Commercial licence, source available to the customer.**

Each customer receives the source for their deployment under a non-redistribution
licence. This is unusual and deliberate: a GMP customer must be able to satisfy
an inspector about what the system does, and "trust us, it's a black box" is a
weak answer under Annex 11. Escrow is offered for Enterprise.

Not open source. The `.docx` dossier parser is the defensible asset and giving it
away removes the moat. *[assumption: worth revisiting if adoption stalls — an
open core with commercial compliance modules is a credible fallback.]*

---

## 6. Go to market

1. **Medicka as reference customer.** One named GMP site in production is worth
   more than any marketing. Negotiate a case study in exchange for favourable
   first-year pricing.
2. **Odoo integrator channel.** They already sell to the segment and are looking
   for vertical differentiation. 20–30% margin on licence, they keep services.
3. **Regulatory events.** The buyer attends GMP and pharma-quality conferences,
   not software ones.

**Honest constraint:** the sales cycle in regulated manufacturing is 6–12 months
and involves QA sign-off. This is not a self-serve product, and any plan assuming
fast bottom-up adoption is wrong.

---

## 7. What must be validated before quoting anyone

The weakest parts of this document, in order:

1. **The ROI inputs.** Lots per year, QA review hours per lot, and real material
   loss are all assumptions. One month of parallel-run data replaces every one of
   them with measurement — and the loss figure is the one Odoo cannot produce.
2. **Willingness to pay.** €14,400/year is an anchored guess, not a tested price.
   Three customer conversations would replace the whole assumption.
3. **Implementation effort.** €6,000–12,000 assumes onboarding takes 2–4 weeks.
   Medicka's real onboarding is the only way to know.
4. **On-premise preference.** Asserted from GMP conservatism, not measured.
5. **Channel margin.** No integrator has been approached.

A jury asking "how did you get to €14,400?" deserves: *"we anchored between what
they already pay for Odoo and what enterprise MES costs, and we have not yet
validated it with a customer."* That answer is respectable. A precise-sounding
number with no basis is not.

---

## Sources

- [MasterControl pricing and reviews — Capterra](https://www.capterra.com/p/148011/MasterControl/)
- [Odoo Enterprise pricing by country — OEC.sh](https://oec.sh/odoo-pricing)
- [Odoo official pricing](https://www.odoo.com/pricing)
- [Pharma MES & eBR software landscape — IntuitionLabs](https://intuitionlabs.ai/articles/pharma-mes-ebr-software-gmp-manufacturing)
- [eBR release-time reduction 40–60% — iFactory](https://ifactoryapp.com/blog/pharma-ebr-batch-record-automation)
- [Review-by-exception and QA review effort — MasterControl](https://www.mastercontrol.com/gxp-lifeline/benefits-electronic-batch-records-for-batch-record-review/)
- [Error reduction from direct capture — Pharmaceutical Technology](https://www.pharmtech.com/view/electronic-batch-records-offer-advantages-beyond-automation)
- [eBR benefits overview — EY](https://www.ey.com/en_us/insights/life-sciences/electronic-batch-records-improve-pharma-manufacturing)
