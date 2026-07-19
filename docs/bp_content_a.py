"""Business plan content, part A: cover, front matter, chapters 1-6."""
from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import (NextPageTemplate, PageBreak, Paragraph, Spacer,
                                Table, TableStyle)

import finance_model as FM
from build_business_plan import (M, UE, BE, SENS, MK, SVC, SS, bullets, callout,
                                 heading, kpibox, money, para, rule, srcbox, table)


def ch1():
    y1, y2, y3 = M[1], M[2], M[3]
    s = [heading("1 &nbsp; Executive summary", 0),
         para("**BatchTwin turns the paper batch record of a small GMP manufacturer into a "
              "digital one, on top of the Odoo ERP they already run &mdash; without replacing "
              "Odoo and without stopping production to migrate.**"),

         heading("1.1 &nbsp; The problem", 1),
         para("Every regulated manufacturer lives or dies by one document: the *dossier de "
              "lot*. It proves, batch by batch, what was made, from which raw materials, "
              "tested how, and released by whom. Our design partner &mdash; **Laboratoires "
              "Medicka**, GMP-certified since 2010, roughly 100 staff, 309 products &mdash; "
              "still keeps that entire record on paper."),
         para("Paper is not merely inconvenient. It is the single most common source of "
              "regulatory findings: FDA warning letters referenced batch-record deficiencies "
              "in **42% of pharmaceutical facility inspections** between 2020 and 2023 "
              "[SOURCED], and in fiscal year 2025 more than a third of warning letters cited "
              "documentation failures such as missing signatures and incomplete batch records "
              "[SOURCED]. Paper also hides money: the ERP deducts the *theoretical* recipe "
              "quantity, so material actually lost at weighing never appears anywhere."),

         heading("1.2 &nbsp; The product", 1),
         para("BatchTwin reads the customer's **own** `.docx` dossier templates and turns them "
              "into fillable digital forms. Against Medicka's four real dossiers this produced "
              "**1,205 fillable fields, 135 tappable conformity checks, and eliminated 570 "
              "pre-printed blank paper rows** [MEASURED]. No transcription, and no "
              "re-implementation of the customer's documents inside somebody else's data model "
              "&mdash; which is where most of the cost of a conventional eBR project goes."),
         para("On top of that sit the things paper cannot do: a hash-chained audit trail with "
              "an external anchor file, Part 11 electronic signatures, a release gate that "
              "cannot be bypassed, true cost per lot computed from what was actually weighed, "
              "and an SPC drift forecast that warns before a specification is breached."),

         heading("1.3 &nbsp; The business", 1),
         para(f"Sold per **site**, not per user. Operators are shift workers on shared tablets, "
              f"and per-user pricing would push customers toward shared logins &mdash; which "
              f"would destroy the identity model the entire compliance story rests on. Three "
              f"plans from **{money(FM.PLANS['Essential']['annual_tnd'])}** to "
              f"**{money(FM.PLANS['Standard']['annual_tnd'])}** per site per year, plus one-off "
              f"implementation services of **{money(FM.services_total())}** [DERIVED]."),
         Spacer(1, 3),
         table(["", "Year 1", "Year 2", "Year 3"],
               [["Active sites", y1["active_sites"], y2["active_sites"], y3["active_sites"]],
                ["Licence revenue", money(y1["licence_tnd"]), money(y2["licence_tnd"]),
                 money(y3["licence_tnd"])],
                ["Services revenue", money(y1["services_tnd"]), money(y2["services_tnd"]),
                 money(y3["services_tnd"])],
                ["Total revenue", money(y1["revenue_tnd"]), money(y2["revenue_tnd"]),
                 money(y3["revenue_tnd"])],
                ["Total cost", money(y1["cost_tnd"]), money(y2["cost_tnd"]), money(y3["cost_tnd"])],
                ["Profit", money(y1["profit_tnd"]), money(y2["profit_tnd"]), money(y3["profit_tnd"])],
                ["Net margin", f"{y1['margin_pct']}%", f"{y2['margin_pct']}%", f"{y3['margin_pct']}%"]],
               [46 * mm, 41 * mm, 41 * mm, 42 * mm], align_right=(1, 2, 3), bold_rows=(3, 5)),
         Spacer(1, 6),
         callout("Read the profit line sceptically &mdash; we do",
                 f"BatchTwin shows a profit in year 1, which for a software company is unusual "
                 f"enough to deserve suspicion rather than applause. Two things cause it and "
                 f"neither is a triumph. First, the three founders are paid "
                 f"{money(FM.FOUNDER_MONTHLY_TND[1])} per month [ASSUMPTION], well below the "
                 f"Tunis market rate for a software engineer. Second, "
                 f"{y1['services_tnd'] / y1['revenue_tnd'] * 100:.0f}% of year-1 revenue is "
                 f"one-off services rather than recurring licence. On licence revenue alone the "
                 f"business does not cover its cost base until roughly "
                 f"**{BE['sites_for_breakeven_on_licence_alone']} sites**, which the plan "
                 f"reaches during year 3. Chapter 9 works through it properly.", "warn"),

         heading("1.4 &nbsp; Why this segment can be won", 1)]
    s += bullets([
        "**Enterprise eBR is priced for multinationals.** MasterControl starts at "
        "$1,000 per month per feature with additional cost per site [SOURCED]; Werum PAS-X "
        "carries an 18&ndash;24 month implementation and six-figure consulting spend "
        "[SOURCED]. A 100-person Tunisian site can justify neither, so it stays on paper. "
        "That gap is the market.",
        "**We extend Odoo rather than replace it.** Odoo is what SMEs in this segment "
        "actually run; competitors ask them to abandon it.",
        "**We read the customer's own documents.** The `.docx` parser is the defensible "
        "asset, and parsing a prospect's real dossier in front of them is the demonstration "
        "that closes the sale.",
        "**On-premise by default.** Batch data and formulas never leave the site, which "
        "removes the Annex 11 supplier-audit objection entirely &mdash; and commercially "
        "removes the per-customer cloud bill that would otherwise be our largest variable "
        "cost. Chapter 7 shows what that does to gross margin.",
        "**The Odoo integration is read-only by construction.** We cannot corrupt the "
        "customer's ERP, because we never write to it.",
    ])
    s += [Spacer(1, 5),
          heading("1.5 &nbsp; What is honestly unproven", 1),
          para("The largest unvalidated input in this plan is **the size of our own "
               "addressable market**, and it is unvalidated for a specific and instructive "
               "reason: our design partner is a food-supplement maker, and food-supplement "
               "makers do not appear in any published Tunisian manufacturer register. "
               "Chapter 3 states that problem rather than estimating around it. Chapter 12 "
               "lists what would fix it, and Appendix D collects every assumption in this "
               "document into a single table so a reader can attack them as a group."),
          Spacer(1, 4),
          kpibox("Chapter 1 &mdash; headline KPIs", [
              ("Dossier fields digitalised", "1,205", "MEASURED",
               "docx_forms.load_all('dossier')"),
              ("Automated tests passing", "143", "MEASURED", "python -m pytest -q"),
              ("Year-3 revenue", money(y3["revenue_tnd"]), "DERIVED",
               "finance_model.build_model()"),
              ("Break-even, licence only", f"{BE['sites_for_breakeven_on_licence_alone']} sites",
               "DERIVED", "finance_model.breakeven()"),
              ("Batch-record findings in FDA inspections", "42%", "SOURCED",
               "Ref [6], 2020&ndash;2023"),
          ]),
          Spacer(1, 4),
          srcbox(["[1] Capterra &mdash; MasterControl pricing",
                  "[6] GMP Pros &mdash; paper-to-eBR transition",
                  "[7] Pharmaceutical Online &mdash; 2025 FDA warning letters",
                  "[12] BatchLine &mdash; PAS-X implementation profile"]),
          PageBreak()]
    return s


def ch2():
    s = [heading("2 &nbsp; The problem, quantified", 0),
         para("This chapter establishes that the problem is real, expensive and regulated "
              "&mdash; using published evidence rather than our own assertions. It is "
              "deliberately the most heavily cited chapter in the document."),

         heading("2.1 &nbsp; Paper batch records are the leading source of GMP findings", 1),
         para("The regulatory record is unambiguous. Between 2020 and 2023, FDA warning "
              "letters referenced batch-record deficiencies in **42% of pharmaceutical "
              "facility inspections** [SOURCED]. In fiscal year 2025 the agency issued "
              "**303 drug and biologics warning letters, a 59% increase** on the prior year, "
              "and **more than a third cited documentation failures** &mdash; missing "
              "signatures, incomplete batch records, inconsistent procedures [SOURCED]. Data "
              "integrity specifically appeared in **15% of all FY2025 warning letters** "
              "[SOURCED]."),
         para("Two observations matter commercially. The first is that these are precisely "
              "the failure modes a paper record cannot defend against: a paper form cannot "
              "refuse an unsigned release, cannot timestamp itself, and cannot prove it was "
              "not rewritten. The second is that enforcement is intensifying, not easing, "
              "which moves this from an efficiency purchase to a risk purchase &mdash; and "
              "risk purchases survive budget cuts that efficiency purchases do not."),

         heading("2.2 &nbsp; What paper costs at a site like Medicka", 1),
         para("Medicka runs 309 products, roughly two-thirds oral liquids, across four "
              "mandatory dossier stages: fabrication (DFA), primary packaging (DCOI), "
              "secondary packaging (DCOII) and quality control (DCT). Every lot generates a "
              "complete paper set. Parsing those four real templates gives the shape of the "
              "burden:"),
         Spacer(1, 3),
         table(["Dossier", "Stage", "Fields", "Conformity checks", "Blank paper rows removed"],
               [["DFA", "Fabrication", "110", "3", "6"],
                ["DCOI", "Cond. primaire", "217", "13", "223"],
                ["DCOII", "Cond. secondaire", "218", "6", "120"],
                ["DCT", "Contr&ocirc;le qualit&eacute;", "660", "113", "221"],
                ["Total", "&mdash;", "1,205", "135", "570"]],
               [26 * mm, 34 * mm, 22 * mm, 36 * mm, 52 * mm],
               align_right=(2, 3, 4), bold_rows=(4,)),
         Spacer(1, 5),
         para("**The 570 figure is the one worth saying aloud** [MEASURED]. DCOI pre-prints a "
              "92-row in-process log and DCT a 95-row compression table &mdash; because paper "
              "cannot grow. Those rows exist in order to be mostly blank. A digital form grows "
              "on demand, so they simply disappear. That is not a productivity claim requiring "
              "a study; it is arithmetic on the customer's own documents."),

         heading("2.3 &nbsp; The invisible money: material loss", 1),
         para("At weighing, raw material is lost to dust, spillage and residue in the vessel. "
              "The ERP deducts the theoretical BOM quantity, so the loss never appears in any "
              "system. It silently inflates true cost and corrupts stock."),
         para(f"Medicka's real formula for the demonstration product &mdash; a magnesium and "
              f"vitamin-B6 oral syrup, 200 mL, lot size {UE['units']} units &mdash; costs "
              f"**{money(UE['bom_tnd'])}** in materials, or "
              f"**{UE['cost_per_unit_tnd']:.3f} TND per unit** [MEASURED]. That is what Odoo "
              f"believes. What was actually consumed is a different number, and today nobody "
              f"anywhere knows what it is."),
         Spacer(1, 3),
         callout("The most valuable measurement in this entire plan",
                 "We deliberately do not claim a material-loss percentage, because we do not "
                 "have one and neither does the customer &mdash; Odoo structurally cannot "
                 "produce it. The honest claim is not \"we will save you X\". It is: "
                 "**Odoo cannot see this number at all, and after BatchTwin you have it for "
                 "every lot.** One month of parallel-run data creates that figure for the "
                 "first time. It is worth more to this business case than any projection in "
                 "this document, and Chapter 11 is built around capturing it.", "good"),

         heading("2.4 &nbsp; In-process quality data is thrown away", 1),
         para("Every thirty minutes an operator measures the fill volume of ten bottles and "
              "writes the results on paper. That data could show an underfill trend developing "
              "an hour before it breaches specification. Instead it dies in a binder. If a "
              "sample drifts low at 3pm, nobody sees the trend until bottles are already "
              "underfilled and scrapped."),
         para("BatchTwin plots those same measurements on an X&#772;/R control chart with "
              "Western Electric rules and fits an ordinary-least-squares trend to forecast the "
              "breach. This is presented as statistics rather than AI, deliberately &mdash; "
              "see Chapter 5."),

         heading("2.5 &nbsp; Why they have not already solved it", 1),
         para("Not ignorance. Price and disruption:"),
         ] + bullets([
        "**Enterprise MES/eBR is out of reach.** MasterControl begins at $1,000 per month "
        "per feature and charges again per site [SOURCED]. Werum PAS-X runs 18&ndash;24 "
        "months to implement with six-figure consulting spend [SOURCED].",
        "**Implementation risk is existential.** Integration work causes more delays than "
        "any other part of an eBR project [SOURCED]. A GMP site cannot stop producing while "
        "an IT project finds its feet.",
        "**Odoo's own Quality module is not a batch record.** It records checks. It does "
        "not produce a compliant dossier de lot and has no Part 11 signatures.",
        "**Building in-house means 18 months and no validation experience.**",
    ]) + [
        Spacer(1, 5),
        kpibox("Chapter 2 &mdash; problem KPIs", [
            ("FDA inspections citing batch-record issues", "42%", "SOURCED", "Ref [6], 2020&ndash;2023"),
            ("FY2025 FDA drug warning letters", "303 (+59%)", "SOURCED", "Ref [7]"),
            ("FY2025 letters citing data integrity", "15%", "SOURCED", "Ref [8]"),
            ("Dossier fields on paper today", "1,205", "MEASURED", "docx_forms parser"),
            ("Blank pre-printed rows eliminated", "570", "MEASURED", "repeatable-block collapse"),
            ("Material cost per demo lot", money(UE["bom_tnd"]), "MEASURED", "analytics.mass_balance()"),
            ("True material loss", "not yet known", "&mdash;", "requires parallel run; see Ch.11"),
        ]),
        Spacer(1, 4),
        srcbox(["[1] Capterra", "[6] GMP Pros", "[7] Pharmaceutical Online",
                "[8] QBench &mdash; 470 FDA warning letters", "[12] BatchLine", "[13] A3P &mdash; eBR pitfalls"]),
        PageBreak()]
    return s


def ch3():
    s = [heading("3 &nbsp; Market analysis", 0),
         para("This is the weakest chapter in the document and it is written to be read that "
              "way. We can source a denominator; we cannot source the *right* denominator."),

         heading("3.1 &nbsp; Total addressable market &mdash; a floor, not an estimate", 1),
         para(f"Licensed pharmaceutical manufacturing sites in the Maghreb, counting only "
              f"countries that publish a figure:"),
         Spacer(1, 3),
         table(["Country", "Licensed pharma manufacturing sites", "Evidence"],
               [["Algeria", "218", "[SOURCED] Ref [9] &mdash; 30% of Africa's pharma industry"],
                ["Tunisia", "55", "[SOURCED] Ref [10] &mdash; plus 40+ laboratories, exports to ~35 countries"],
                ["Morocco", "not published", "Ranked 2nd in Africa by volume; no site count found"],
                ["Floor total", f"{MK['tam_maghreb_pharma_floor_sites']}", "Excludes Morocco entirely"]],
               [30 * mm, 52 * mm, 88 * mm], bold_rows=(3,)),
         Spacer(1, 5),
         para("We report this as a **floor** rather than an estimate because Morocco is "
              "genuinely missing, and inflating the total with a guessed Moroccan figure would "
              "make the number less useful, not more."),

         heading("3.2 &nbsp; Serviceable market &mdash; Tunisia", 1),
         para(f"Of Tunisia's {FM.PHARMA_SITES['Tunisia']} pharmaceutical sites, our band is "
              f"50&ndash;300 staff, already running an ERP, still keeping batch records on "
              f"paper. We assume **{FM.ADDRESSABLE_SHARE:.0%}** qualify [ASSUMPTION], giving "
              f"**{MK['sam_tunisia_pharma_sites']} sites**, worth "
              f"**{money(MK['sam_tunisia_value_tnd'])} per year** at the Standard plan."),
         para("Sites already running a validated MES are disqualified &mdash; replacement cost "
              "exceeds the pain. So are sites with no ERP at all, because BatchTwin assumes a "
              "BOM exists."),

         heading("3.3 &nbsp; The denominator problem, stated plainly", 1),
         callout("Our own market-share figure does not survive scrutiny, and here is why",
                 MK["denominator_problem"], "bad"),
         Spacer(1, 5),
         para("We could have hidden this by quietly inflating the addressable share until the "
              "share looked modest. Instead: the numerator is defensible, the denominator is "
              "wrong, and the fix is a counting exercise rather than a modelling one. "
              "**Counting the Tunisian nutraceutical, supplement, cosmetics and device "
              "manufacturing population is open question #1** &mdash; Chapter 12 gives the "
              "method and the cost."),
         para("What can be said with confidence is directional: Medicka is one such site, it "
              "is not in the 55, and the trade associations, ANCSEP registrations and ISO "
              "22716 certificate lists that would enumerate its peers exist &mdash; they have "
              "simply not been aggregated by anyone, including us."),

         heading("3.4 &nbsp; Market tailwind", 1),
         para("The Tunisian pharmaceutical market was valued at **USD 2.74 billion in 2025** "
              "with a projected **12.9% CAGR to 2032** [SOURCED]. Domestic production stands "
              "at roughly **52%**, and government policy targets **70% by 2030** [SOURCED]. "
              "Tunisia was ranked the **9th most competitive pharmaceutical market in Africa "
              "in 2025** [SOURCED]."),
         para("The relevant implication is narrow and worth stating precisely: a policy push "
              "toward domestic production means more locally manufactured lots, more dossiers, "
              "and more exposure to inspection &mdash; and export ambition raises the "
              "documentation bar, because an importing regulator audits the batch record. "
              "Growth in the market is not automatically growth for us; growth in *regulated "
              "domestic output* is."),

         heading("3.5 &nbsp; Segment priority", 1),
         table(["Segment", "Why now", "Priority"],
               [["Food supplements &amp; nutraceuticals",
                 "Medicka is the reference. ISO 22716 / HACCP pressure without full pharma "
                 "cost tolerance &mdash; the affordability gap is widest here.", "**First**"],
                ["Small-molecule pharma (SME)",
                 "Highest regulatory pressure and clearest willingness to pay; longest sales "
                 "cycle and heaviest validation burden.", "Second"],
                ["Cosmetics",
                 "ISO 22716 applies; batch records are lighter, so plan value is lower.", "Third"],
                ["Medical devices",
                 "ISO 13485 supported by an industry profile in code, but no design partner.",
                 "Opportunistic"]],
               [46 * mm, 96 * mm, 28 * mm]),
         Spacer(1, 5),
         kpibox("Chapter 3 &mdash; market KPIs", [
             ("TAM, Maghreb pharma sites (floor)", f"{MK['tam_maghreb_pharma_floor_sites']}",
              "SOURCED", "Tunisia 55 + Algeria 218; Morocco excluded"),
             ("SAM, Tunisia pharma sites", f"{MK['sam_tunisia_pharma_sites']}", "ASSUMPTION",
              f"{FM.ADDRESSABLE_SHARE:.0%} of 55 qualify"),
             ("SAM annual value", money(MK["sam_tunisia_value_tnd"]), "DERIVED",
              "SAM sites &times; Standard plan"),
             ("Year-3 sites, total", f"{MK['som_y3_total_sites']}", "ASSUMPTION", "customer ramp, Ch.8"),
             ("Year-3 sites, Tunisia", f"{MK['som_y3_tunisia_sites']}", "ASSUMPTION", "geography split"),
             ("Implied share of pharma-only SAM", f"{MK['som_y3_share_of_tunisia_pharma_sam_pct']}%",
              "DERIVED", "&#9888; implausible &mdash; see &sect;3.3"),
             ("Tunisian pharma market, 2025", "USD 2.74 bn", "SOURCED", "Ref [11], 12.9% CAGR"),
             ("Supplement/cosmetics site count", "unknown", "&mdash;", "open question #1"),
         ]),
         Spacer(1, 4),
         srcbox(["[9] Maghreb Pharma &mdash; Algeria 218 plants",
                 "[10] African Manager &mdash; Tunisia competitiveness",
                 "[11] Maximize Market Research &mdash; Tunisia pharma market"]),
         PageBreak()]
    return s
