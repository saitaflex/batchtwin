# BatchTwin — business model

> **Every number in this document is either computed by the code in this
> repository or cited from a public source.** Where a figure would have to be
> invented — pricing, ROI, revenue — there is a blank and the formula that fills
> it, not a guess. A confident number with no origin is the fastest way to lose
> a jury that checks arithmetic.

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

### 3.4 ROI worksheet — fill this in with Medicka, do not guess it

There is no ROI figure in this document, because computing one requires four
numbers only the customer has. Inventing them would produce a confident total
that collapses the moment anyone asks where it came from.

Ask for these four, then the arithmetic is trivial:

| Input | Ask | Value |
|---|---|---|
| **L** | Lots produced per year | `____` |
| **H** | Hours QA spends reviewing one paper batch record | `____` |
| **C** | Loaded hourly cost of a QA reviewer | `____ €/h` |
| **M** | Material cost of an average lot | `____ €` |

Then:

```
QA review saved       = L × H × 0.40 × C     ← 0.40 is the LOW end of the
                                                published 40-60 % reduction
Material loss exposed = L × M × loss%        ← loss% is unknown until BatchTwin
                                                measures it; that is the point
Annual benefit        = QA review saved + material loss + deviations avoided
Payback               = (subscription + implementation) ÷ annual benefit
```

**The one input nobody can supply yet is `loss%`.** Odoo cannot produce it —
it knows the theoretical BOM and nothing about what was actually weighed. One
month of parallel-run data produces it for the first time, and that single
number is worth more to this business case than any projection in this document.

### 3.5 What the arithmetic will probably say, and why that is fine

Run the formula with any plausible inputs for a site of Medicka's size and QA
review time dominates every other term; material loss and expiry are rounding
errors beside it. That has two consequences worth saying out loud before a jury
does:

**Efficiency alone is unlikely to justify the subscription at low volume.**
Benefit scales linearly with lots; the subscription does not. Below a few
hundred lots a year the sums are marginal, and the honest recommendation is the
smallest plan.

**The purchase is justified by risk, not efficiency.** A regulatory finding on
batch records is existential for a GMP site — lost certification, halted export,
remediation far beyond any subscription. A recall from an undetected fill drift
is the same. A failed customer audit costs the account. BatchTwin's answer to
each is concrete: the hash chain with external anchoring, Part 11 signatures, a
release gate that cannot be bypassed, and an SPC forecast that warns before the
specification is breached.

This is insurance pricing, not efficiency pricing — which is exactly why the
buyer is the person who personally signs release, and why the pitch leads with
traceability.

---

## 4. Pricing

**This document does not state a price, because no price has been tested.**
What follows is the reasoning that produces one, so the number you eventually
quote can be defended.

### The anchors — both public, both verifiable

| Anchor | Figure | Source |
|---|---|---|
| Enterprise eBR | MasterControl from **$1,000/month per feature**, extra per site | [Capterra](https://www.capterra.com/p/148011/MasterControl/) |
| What the customer already pays for software | Odoo Enterprise **$8.95–$76.20/user/month**, Middle East at the bottom | [OEC.sh](https://oec.sh/odoo-pricing) |

### The rule those anchors produce

> Price **above** what the customer already pays for their ERP — BatchTwin
> carries more regulatory risk than Odoo does — and **an order of magnitude
> below** enterprise MES, because being affordable to a 100-person site is the
> entire reason this product exists.

That bounds the annual figure between roughly the customer's Odoo bill and a
tenth of a MasterControl deployment. Landing inside that band is a commercial
decision, not a calculation, and it should be made after three customer
conversations rather than in a document.

### Per site, not per user — and this one is not negotiable

Operators are shift workers on shared tablets. Per-user pricing punishes exactly
the behaviour the product depends on — every person recording their own actions
under their own identity — and pushes customers toward shared logins, which
destroys the Part 11 identity model the whole compliance story rests on.

A pricing model that undermines the product's core claim is the wrong model at
any price.

### Structure to quote, values to fill

| Plan | Scope | Annual |
|---|---|---|
| Essential | 1 line, limited product count | `____` |
| Standard | 1 site, unlimited lines, + SPC, VÉRA, deviations | `____` |
| Enterprise | Multi-site, + hybrid dashboard, SSO, priority SLA | `____ /site + ____ group` |

Services (implementation, validation pack, parallel-run support, training) are
where early revenue actually comes from, and they scale with the number of
dossier templates rather than with seats. **Benchmark these against what a local
Odoo integrator charges per day in Tunisia** — that is the comparable the
customer will use mentally, and it is a number you can obtain this week.

### Support and maintenance

Bundled into the subscription, not sold separately. **Regulatory-change updates
are included**: a customer must never face a bill to stay compliant, and saying
so removes the main objection to subscription pricing in a regulated industry.

Tiering by response time (next business day / same day / 1 hour) is standard and
costs nothing to offer; the premium multiplier is a commercial decision, not a
computed one.

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
   for vertical differentiation. Margin split on licence with services retained
   by the partner is the usual shape; the percentage is a negotiation, not a
   figure to publish before one has happened.
3. **Regulatory events.** The buyer attends GMP and pharma-quality conferences,
   not software ones.

**Honest constraint:** the sales cycle in regulated manufacturing is 6–12 months
and involves QA sign-off. This is not a self-serve product, and any plan assuming
fast bottom-up adoption is wrong.

---

## 7. What must be validated before quoting anyone

The weakest parts of this document, in order:

1. **The four ROI inputs** (§3.4): lots/year, QA review hours, reviewer cost,
   material cost per lot. Ask Medicka; all four are known to them today.
2. **Real material loss.** Nobody has this number, including Medicka — Odoo
   cannot produce it. One month of parallel-run data creates it for the first
   time, and it is the most valuable single measurement in this whole plan.
3. **Willingness to pay.** No price has been tested. Three customer
   conversations replace the entire pricing section with evidence.
4. **Implementation effort.** unknown until Medicka's onboarding is done. Price it
   at cost for the first customer and measure.
5. **On-premise preference.** Asserted from GMP conservatism, not measured.
6. **Channel margin.** No integrator has been approached.

A jury asking "what does it cost?" deserves: *"we have not set a price yet. Here
is the band it has to sit in and why — above their Odoo bill, an order of
magnitude below enterprise MES — and here are the three customer conversations
that will fix it."* That answer is respectable, and it is checkable.

A precise-sounding number with no origin is not. It invites exactly one question,
and there is no good answer to it.

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
