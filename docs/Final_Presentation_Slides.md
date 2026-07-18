# BatchTwin — Final Presentation (Guy Kawasaki / Enactus)

**Source:** `README.md` + `docs/BatchTwin_Idea_Document.md`  
**Template:** `logo/Template.pdf` (10 slides + conclusion)  
**Data Room:** *not found in this repository* — slides 5, 9 and 10 use only what exists in the docs; mark those figures as *estimates to validate* until a Data Room is added.

**How to use:** copy each block into your Enactus template (white slide, enactus logo top-left). Keep text short; prefer diagrams on slide 4.

---

## SLIDE 1 — Title

| Field | Content |
|---|---|
| **Project** | **BatchTwin** — *the living batch record* |
| **Tagline** | Paperless GMP electronic Batch Record (eBR) on Odoo |
| **Team** | Oussama Labidi (leader) · Salem Amara · Ahmed Hammami |
| **Client / partner** | Laboratoires Medicka, Nabeul, Tunisia |
| **Contact** | *[add team email + phone]* |

**Line under the title:**  
*Odoo says what **should** happen. BatchTwin captures what **actually** happens — and produces a compliant, costed batch record automatically.*

---

## SLIDE 2 — Problem / Opportunity

**Slide title:** The batch record is still on paper

**The pain (Medicka & SME pharma / supplements):**
- Manufacturing already runs on **Odoo**, but the **Batch Record** (DFA, DCOI, DCOII, DCT) still lives in **4 Word / paper documents**
- **Real cost is invisible** — Odoo knows the theoretical BOM, never the weighing losses
- **Quality is retrospective** — drift is found at end of shift, too late
- **Release is slow** — QA leafs through pages; a batch can wait days
- **Integrity is fragile** — paper can be lost, back-dated, or filled in afterwards

**Hook number:** cost of poor quality ≈ **15% of revenue** (industry benchmark)

**Goal of this slide:** make everyone believe a living eBR is useful — not just a scanned PDF.

---

## SLIDE 3 — Value Proposition

**Slide title:** BatchTwin = the **living** batch record

**What you sell:**  
An **Odoo-native** digital layer: operators work *inside* the dossier; the system computes as they fill it.

**How we relieve the pain:**

| Before (paper) | With BatchTwin |
|---|---|
| 4 Word dossiers | Production → Primary Pack → Secondary Pack → Quality → Release (e-sign) |
| Theoretical BOM | **True cost**: real consumption + losses vs BOM |
| Checks die in a binder | **Predictive SPC** + alert before breach |
| No integrity proof | **Hash-chained** audit + external anchor (21 CFR Part 11) |
| Unknown kWh / CO₂ | **Energy / carbon passport** per batch |

**One-liner:**  
*Pharma-grade traceability, real cost, predictive quality, and carbon — at SME price, without replacing Odoo.*

---

## SLIDE 4 — Underlying Magic *(little text, lots of diagram)*

**Slide title:** The technical magic

**Diagram to draw (flow):**
```
Odoo (MO/BOM) → Production → Pack I → Pack II → Quality → Release
                      ↓           ↓        ↓        ↓
                 SHA-256 hash-chained audit → External anchor outside DB → Batch Record PDF
```

**4 “secret ingredients” (icons / chips):**
1. **Part 11 e-signatures** — login + password re-entered at every signature
2. **Live mass balance** — measured losses → true unit cost
3. **SPC + Western Electric** — drift forecast before scrap
4. **Digitized Medicka dossiers** — real `.docx` → tablet forms (110–660 fields)

**Demo (show here):**
- Sign in `prod.karim` → Simulate weighing → SPC “+ with drift” → signature → PDF
- Falsify a DB row → integrity badge turns red (external anchor)

**Stack:** FastAPI · SQLite · Odoo XML-RPC · tablet PWA · ReportLab PDF

---

## SLIDE 5 — Business Model

> **Data Room:** missing — model proposed from product positioning (to validate).

**Who pays:** SME food-supplement / small pharma / cosmetics makers **on Odoo** (design partner: Medicka)

**Channels:**
- Pilot at Medicka → GMP reference
- **Odoo** integrator partners (Tunisia / MENA / EU)
- Direct B2B (plant → QA / Responsible Pharmacist / management)

**Pricing model (proposal):**

| Offer | Logic |
|---|---|
| **Setup + IQ/OQ** | Deployment, Odoo mapping, training |
| **Licence / site / year** | eBR + audit + PDF access |
| **VÉRA module** (optional) | Raw-material forecast / FEFO |
| **Support & validation** | Maintenance, periodic review |

**Price position:** a fraction of enterprise MES (Tulip, MasterControl, PAS-X = six figures + 6–18 months) — *the essential 20% → 80% of the value, in days, on Odoo.*

---

## SLIDE 6 — Go-to-Market Strategy (4Ps)

| P | Levers |
|---|---|
| **Product** | Odoo-native eBR + VÉRA + carbon passport (EU DPP) |
| **Price** | SME-affordable vs enterprise MES; demo hardware &lt; €50 |
| **Place** | Plant floor (tablet /floor) + QA office; installable PWA |
| **Promotion** | Live 3-min demo · Medicka design partner · Enactus / hackathons · Odoo partners · ROI (QA hours + material loss) |

**Key message:** **low-cost, high-trust** — one pilot plant speaks louder than an ad campaign.

**Acquisition:**
1. Medicka pilot (GMP proof)
2. Case study + generated batch-record PDF
3. Co-selling with Odoo integrators

---

## SLIDE 7 — Competitive Analysis

| Alternative | Limit | Why customers choose BatchTwin |
|---|---|---|
| **Paper + Excel** | Slow, error-prone, no integrity, no cost/energy | Same low entry cost, without the pain |
| **Enterprise MES / eBR** (Tulip, MasterControl, Körber, Werum PAS-X) | Six figures, 6–18 months, **not Odoo-native** | Essential eBR in days, on the ERP already there |
| **Odoo Quality / MRP alone** | No true GMP batch record, no gated e-sign, no mass-balance / SPC / CO₂ | We **extend** Odoo — we don’t compete with it |

**Position:** *the missing layer between paper and enterprise MES* — Odoo-native, IoT-ready, carbon-aware, SME-priced.

---

## SLIDE 8 — Management Team

| Role | Person |
|---|---|
| **Leader / Product** | Oussama Labidi |
| **Member** | Salem Amara |
| **Member** | Ahmed Hammami |
| **Design partner** | Laboratoires Medicka (GMP since 2010, ~100 staff, 309 products) |

**Add if relevant:** Enactus mentor, QA/pharma advisor, Odoo partner.

---

## SLIDE 9 — Financial Forecasts & Key Figures

> **Data Room:** missing — no 5-year revenue / IRR in the repo. The figures below
> come from `docs/BUSINESS_MODEL.md`, which computes them from the repository's
> own BOM rather than estimating. Do not quote a number that is not in that file.

### Operational impact (240 lots / year — 5 lines × ~4 lots / month)

| Lever | Basis | Annual |
|---|---|---|
| QA review 3 h → 1.5 h / lot | published 40–60 % reduction, taken at the **low** end | **€6,480** |
| Material loss made visible | 0.4 % of €400/lot material spend | **€384** |
| Expiry write-off avoided | 30 % of VÉRA's €3,035 exposure | **€911** |
| Deviations avoided | 2 / yr × €1,200 | **€2,400** |
| **Total** | | **≈ €10,200 / yr** |

**Say this plainly:** against a €14,400 subscription, **efficiency alone does not
pay it back at this volume** — it turns positive near 400 lots/year. The purchase
is justified by risk, not efficiency: a regulatory finding on batch records, a
recall from undetected drift, or a failed customer audit each cost more than a
decade of subscription. That is exactly why the buyer is the person who signs
release.

> An earlier version of this slide claimed €20–45k/year from material loss alone.
> That was ~22× the repository's own numbers (520 lots × €400 = €208k of material
> spend; 1 % of it is €2,080, not €45k) and it contradicted BUSINESS_MODEL.md.
> Corrected — an investor who checks the arithmetic will check this one.

### To complete (Data Room)

| KPI | Fill in |
|---|---|
| Target customers &lt; 3 years | *[e.g. Medicka + N Odoo SMEs]* |
| Services sold Y1–Y5 | *[pilots / licences / sites]* |
| Projected annual revenue Y1–Y5 | *[—]* |
| **IRR** | *[—]* |

---

## SLIDE 10 — Current Status, Traction, Plan & Use of Funds

### Where the product is today
**Working** prototype:
- Full GMP lifecycle + e-signatures + hash audit + external anchor
- 4 digitized Medicka dossiers (DFA / DCOI / DCOII / DCT)
- Mass balance, SPC, equipment twin, Batch Record PDF
- VÉRA (RM forecast) · AI copilot (read-only) · PWA EN/FR/AR
- **53 tests** passed (compliance + workflow + Odoo contract)

### Traction / momentum
- Real design partner: **Medicka**
- Testable Odoo contract (`MockOdoo` ⇄ `LiveOdoo`)
- Scripted 3-minute demo

### Near future (roadmap)
| Horizon | Focus |
|---|---|
| Short | Live Odoo connection · 1-line pilot · IQ/OQ |
| Medium | Multi-batch · GMP validation · VÉRA on the floor |
| Long | Odoo SME network · EU product passport |

### Use of funds *(scheme — quantify with Data Room)*
1. Plant pilot + sensors (energy / scale)
2. Validation / compliance (IQ OQ PQ)
3. Live Odoo integration + training
4. Go-to-market (Odoo partners)

---

## SLIDE — Conclusion (action-oriented)

**Title:** Replace the binder. Keep Odoo.

**CTA (pick 1–2):**
1. **Live 3-min demo** — weighing → SPC → signature → PDF → integrity proof  
2. **Medicka pilot** — 1 product, 1 line, 1 fully digital batch record  
3. **Next step** — connect `LiveOdoo` + scope IQ/OQ

**Closing line:**  
*Every batch deserves a digital twin — self-documenting, self-costing, self-auditing, carbon-aware.*

---

## Notes for building the slides

1. Keep **≤ 6 lines** of text per slide (Kawasaki rule).
2. Slide 4 = **diagram + demo**, not a wall of text.
3. Slides 5 / 9 / 10: once a **Data Room** exists, replace *[—]* cells (price, revenue, IRR, raise amount).
4. Project logo: `logo/batchtwin.png` · optional VÉRA: `logo/vera.png`.
5. Language: this file is ready to paste in **English**.

---

# VIDEO PROMPT — BatchTwin (frame-by-frame for AI)

> Paste this whole section into an AI video tool (Runway / Kling / Sora / Veo / CapCut AI).  
> Goal: a **~90–120 second** product story that matches the pitch + the live demo.  
> Aspect: **16:9** (presentation) or **9:16** (social — same shots, vertical crop).  
> Language on screen: **EN** (primary).  
> Brand: dark industrial SaaS — `#05070B` background, accents `#6C63FF → #A855F7 → #38BDF8`, glass panels, Inter-like UI, **no purple-glow spam**, clean pharma / factory realism.

---

## MASTER PROMPT (copy once at the top of any generation)

```text
Cinematic but clean industrial tech film for BatchTwin — "the living batch record".
Setting: modern pharmaceutical / food-supplement factory (Laboratoires Medicka style, Nabeul Tunisia), GMP cleanroom whites + stainless steel, tablets on the line, paper binders contrast with a dark premium SaaS UI.
Tone: serious, trustworthy, precise — not sci-fi, not cartoon.
Camera: smooth steadicam + subtle UI screen recordings; shallow DOF on hands/paper; sharp UI close-ups.
Motion: slow push-ins, gentle pans, UI cursor/touch with purpose. No chaotic cuts.
Text overlays: short English titles, large, centered or lower-third, high contrast white on dark.
Never invent fake medical claims. Product is an electronic Batch Record (eBR) on Odoo: captures real weighing, checks, signatures; produces compliant costed batch PDF.
Logo: BatchTwin wordmark + optional VÉRA for inventory scenes.
End with clear CTA: "3-min demo · Medicka pilot · Replace the binder. Keep Odoo."
```

---

## GLOBAL STYLE LOCK

| Element | Spec |
|---|---|
| Duration | 100 seconds total (±10s) |
| FPS | 24 or 30 |
| Resolution | 1920×1080 |
| Color grade | Cool steel blues + soft violet accent on UI only; factory neutrals warm-white |
| Music | Low pulse electronic / documentary bed, rising at reveal (0:35), resolve at CTA |
| VO (optional EN) | Calm male or female voice, mid tempo, clear diction |
| UI fidelity | Dark dashboard, KPI tiles, SPC chart, signature modal, PDF preview, integrity badge green→red |
| Forbidden | Blood, gore, fake FDA logos, stock “hacker green terminal”, emoji, neon cyberpunk city |

---

## FRAME-BY-FRAME / SHOT LIST

Timecode = start. Each shot lists: **visual · camera · on-screen text · VO · SFX**.

### SHOT 01 — Cold open / paper pain  
**0:00 – 0:08**

- **Visual:** Close-up of a thick paper “Batch Record” binder on a stainless table. Gloved hands flip pages: handwritten weights, empty signature boxes, coffee stain near a fill-check table. Four labeled tabs visible: **DFA · DCOI · DCOII · DCT**.
- **Camera:** Slow push-in from binder cover to a blank signature line.
- **On-screen:** `The batch record is still on paper`
- **VO:** “SME pharma and supplement makers already run manufacturing on Odoo… but the legal batch record still lives in a binder.”
- **SFX:** Paper rustle, distant cleanroom HVAC hum.

### SHOT 02 — Four consequences (montage)  
**0:08 – 0:18**

- **Visual (4 quick beats, ~2.5s each):**
  1. Scale spilling powder → subtitle `Invisible losses`
  2. Clock / end-of-shift clipboard → `Quality too late`
  3. QA desk with stack of binders → `Slow release`
  4. Binder edge torn / page loose → `Fragile integrity`
- **Camera:** Hard cuts, each beat a locked close-up then micro zoom.
- **On-screen (center, last beat):** `Cost of poor quality ≈ 15% of revenue`
- **VO:** “Fictional cost. Drift seen too late. Release in days. Paper you can lose or back-date.”
- **SFX:** Soft whoosh per cut.

### SHOT 03 — Title card / brand  
**0:18 – 0:24**

- **Visual:** Dark void `#05070B`. BatchTwin logo fades in (from `logo/batchtwin.png`). Thin gradient line violet→cyan under the wordmark. Factory silhouette faintly in depth of field behind glass.
- **Camera:** Static, logo scale 100%→105% very slow.
- **On-screen:**  
  `BATCHTWIN`  
  `the living batch record`  
  `Odoo says what should happen. BatchTwin captures what actually happens.`
- **VO:** “BatchTwin — the living batch record.”
- **SFX:** Soft bass hit + UI chime.

### SHOT 04 — Value proposition split screen  
**0:24 – 0:34**

- **Visual:** Split screen. LEFT: paper binder + pen. RIGHT: industrial tablet showing BatchTwin dark UI with workflow strip:  
  `Production → Primary Pack → Secondary Pack → Quality → Release`  
  Roles under stages: `R. PROD · R. PROD · R. PROD · R. CQ · PRT`
- **Camera:** Slow horizontal wipe left→right as paper dissolves into UI.
- **On-screen lower-third:** `Odoo-native eBR · true cost · SPC · Part 11 · carbon`
- **VO:** “A digital layer on Odoo: the operator works inside the record. The system computes live.”
- **SFX:** Digital dissolve.

### SHOT 05 — Magic: live mass balance (demo UI)  
**0:34 – 0:44**

- **Visual:** Tablet / desktop UI **Production** tab. Finger taps button labeled `⚡ Simulate weighing`. KPI tiles animate: theoretical cost vs real cost, loss in €, yield %. Material row edits: small change ≤5% applies instantly; large change shows badge `Pending QA`.
- **Camera:** Screen recording style, slight handheld parallax, cursor/touch highlight.
- **On-screen:** `True cost — real consumption + losses vs Odoo BOM`
- **VO:** “Every gram lost shows up. Unit cost becomes real — not theoretical.”
- **SFX:** Soft tap, number tick-up.

### SHOT 06 — Magic: predictive SPC  
**0:44 – 0:54**

- **Visual:** **Quality** tab. X̄/R control chart. Button `+ with drift` pressed 3 times. Points drift up; chart turns red; forecast line projects toward limit; toast: `breach in ~22 min — adjust filler`. Deviation card auto-opens: `Deviation opened automatically`.
- **Camera:** Chart fills frame, mild zoom on red zone.
- **On-screen:** `Predictive SPC · Western Electric · alert before scrap`
- **VO:** “Fill checks no longer die in a binder. Drift is anticipated.”
- **SFX:** Alert tone (short, professional, not siren).

### SHOT 07 — Magic: e-signature + gate  
**0:54 – 1:04**

- **Visual:** Operator tries to sign **Production**. Modal: password re-entry (Part 11). Hands type. Stage locks with green check + timestamp + role `R. PROD`. Then attempt **Release** → red banner listing blockers (open deviation, unsigned stages). Cut to second login `smq.leila` closing deviation with root cause + CAPA, password again.
- **Camera:** Tight on modal → pull back to workflow gates lighting green one by one.
- **On-screen:** `21 CFR Part 11 · password at every signature · gated release`
- **VO:** “No identity dropdown. Password at every signature. No release until everything is signed and compliant.”
- **SFX:** Lock click, then blocked buzz, then success chime.

### SHOT 08 — Integrity proof  
**1:04 – 1:12**

- **Visual:** Integrity badge **green** `Chain OK`. Quick stylized “DB row edit” (abstract, not real exploit UI). Badge flips **red**. Overlay diagram: internal hash chain vs external `audit_anchor.log` still rejecting forgery. PDF footer showing chain head.
- **Camera:** Fast cut badge → schematic arrows → PDF zoom.
- **On-screen:** `Hash-chained audit + external anchor outside the DB`
- **VO:** “Even if someone rewrites the database, the external anchor exposes the fraud.”
- **SFX:** Glitch + solid reject thud.

### SHOT 09 — PDF + carbon passport  
**1:12 – 1:20**

- **Visual:** Click `⬇ Batch Record (PDF)`. Pages flip: weighing table, packaging balances, SPC, signatures, energy strip `kWh / gCO₂ per unit`. Optional flash of VÉRA screen (FEFO / stock alert) with `logo/vera.png`.
- **Camera:** Elegant page-turn 3D, then soft pull-out to tablet on the line next to bottles (product example: Magnesium + Vitamin B6 syrup 200 mL).
- **On-screen:** `One click · the binder · carbon passport`
- **VO:** “The paper binder, generated from the same records — plus kWh and CO₂ per unit.”
- **SFX:** Printer-light whoosh (digital).

### SHOT 10 — Positioning / competition (flat graphic)  
**1:20 – 1:28**

- **Visual:** Clean motion graphic on dark bg. Three columns fade: `Paper+Excel` | `Enterprise MES` | `Odoo alone` — then BatchTwin bar slides under as bridge labeled `the missing layer`.
- **Camera:** 2D motion graphics only.
- **On-screen:** `Odoo-native · SME price · 80% of the value without 18 months of MES`
- **VO:** “Between paper and six-figure MES — BatchTwin.”
- **SFX:** Soft UI ticks.

### SHOT 11 — Team + traction  
**1:28 – 1:36**

- **Visual:** Three portrait placeholders / silhouettes with names: **Oussama Labidi** (leader), **Salem Amara**, **Ahmed Hammami**. Badge: `Design partner — Laboratoires Medicka · GMP 2010 · ~100 staff · 309 products`. Small chips: `53 tests` · `working prototype` · `PWA EN/FR/AR`.
- **Camera:** Slow pan across name cards.
- **On-screen:** `Team · real partner · product that runs`
- **VO:** “Prototyped, tested, anchored in a real GMP laboratory.”
- **SFX:** Soft piano accent.

### SHOT 12 — CTA / conclusion  
**1:36 – 1:40** *(hold last frame 1s)*

- **Visual:** Full-bleed dark. Logo center. Three CTA pills:
  1. `Live 3-min demo`
  2. `Medicka pilot — 1 line`
  3. `LiveOdoo + IQ/OQ`
- **Camera:** Static, logo subtle pulse once.
- **On-screen:**  
  `Replace the binder. Keep Odoo.`  
  `Every batch deserves a digital twin.`
- **VO:** “Replace the binder. Keep Odoo.”
- **SFX:** Final resolve chord + silence.

---

## NARRATION SCRIPT (full VO, EN, ~155 words)

```text
SME pharma and supplement makers already run manufacturing on Odoo —
but the legal batch record still lives on paper.
Invisible losses. Late quality. Slow release. Fragile integrity.

BatchTwin — the living batch record.
An Odoo-native digital layer: every gram, every check, every signature.

True cost versus the BOM. SPC that forecasts drift before scrap.
Part 11 signatures. Release gated until everything is signed and clean.
Hash-chained audit, externally anchored. One PDF that replaces the binder —
plus kWh and CO2 per unit.

Between paper and enterprise MES: BatchTwin.
Enactus team. Design partner Medicka. Working prototype.

Three-minute demo. One-line pilot.
Replace the binder. Keep Odoo.
```

---

## PER-SHOT AI GENERATION PROMPTS (if generating clip-by-clip)

Use these as standalone prompts; stitch in an editor to the timecodes above.

### Clip A (Shot 01–02)
```text
Photoreal pharma cleanroom table, thick paper batch record binder labeled Batch Record with tabs DFA DCOI DCOII DCT, gloved hands flipping handwritten fill-check pages, shallow depth of field, cool fluorescent light, documentary style, 8 seconds, then montage of spilled powder on scale, clipboard at end of shift, QA desk stacked binders, torn binder page — English labels Invisible losses / Quality too late / Slow release / Fragile integrity, no logos of real regulators, 16:9
```

### Clip B (Shot 03)
```text
Dark premium tech title card background #05070B, centered BatchTwin logo, thin violet-to-cyan gradient underline, subtle factory bokeh behind glass, minimal text "the living batch record", cinematic slow scale, 6 seconds, 16:9
```

### Clip C (Shot 04)
```text
Split screen: left paper binder and pen, right industrial tablet showing dark SaaS manufacturing workflow bar Production to Release with purple-cyan accents, paper side dissolves into digital UI, clean industrial film look, 10 seconds, 16:9
```

### Clip D (Shot 05–06) — prefer real screen capture
```text
IMPORTANT: Prefer real BatchTwin UI screen recording over AI fake UI.
If AI: dark dashboard Production tab, KPI tiles updating cost and loss in euros after weigh simulation, then Quality SPC X-bar chart drifting red with forecast line, professional SaaS UI, Inter font, no clutter, 20 seconds
```

### Clip E (Shot 07–08)
```text
Close-up of password signature modal on dark UI, stage lock animation green check, red release blocked banner, then integrity badge flipping from green to red, abstract hash-chain diagram with external anchor log, serious compliance tone, 18 seconds, 16:9
```

### Clip F (Shot 09)
```text
Digital PDF batch record pages flipping: weighing table, packaging balance, signatures, energy passport kWh and gCO2 per unit, then tablet beside magnesium syrup bottles 200mL on packaging line, photoreal factory, 8 seconds, 16:9
```

### Clip G (Shot 10–12)
```text
Motion graphics dark background three columns Paper MES Enterprise Odoo-only then BatchTwin bridging bar labeled the missing layer, then team name cards Oussama Labidi Salem Amara Ahmed Hammami Medicka partner badge, end card CTA Replace the binder Keep Odoo, minimal Enactus-pitch aesthetic, 20 seconds, 16:9
```

---

## EDITING & COMPLIANCE NOTES FOR THE AI / EDITOR

1. Prefer **real app screen recordings** for Shots 05–09 (demo authenticity > generative UI).
2. Product example on screen: `FG-MGB6-200` Magnesium + Vitamin B6 syrup 200 mL (800 units) — optional second beat `FG-SPIR-60` spirulina capsules.
3. Do **not** show real passwords; blur modal input; demo accounts are for live pitch only.
4. Do **not** claim “FDA validated” / “GMP certified software” — say *aligned with 21 CFR Part 11 principles* / *prototype for pilot*.
5. Keep total text on screen ≤ **8 words** per overlay.
6. Subtitles: burn-in **English**.
7. End card hold **≥ 2 seconds** for audience to read CTAs.
8. If shortening to **60s**: keep Shots 01, 03, 05, 06, 07, 09, 12 only.
9. If lengthening to **3 min**: insert full live demo between Shot 05 and Shot 09 using README demo script order (login → Documents → weighing → SPC → sign → blocked release → close deviation → PDF → integrity).
10. Assets: `logo/batchtwin.png`, `logo/vera.png`, app at `http://127.0.0.1:8000`.

**Spoken pitch:** see `docs/BatchTwin_4min_Pitch.md`.
