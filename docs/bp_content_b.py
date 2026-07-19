"""Business plan content, part B: chapters 4-9 (product, moat, pricing, finance)."""
from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

import finance_model as FM
from build_business_plan import (M, UE, BE, SENS, MK, SVC, SS, bullets, callout,
                                 heading, kpibox, money, para, rule, srcbox, table)


def ch4():
    s = [heading("4 &nbsp; The product, and the evidence it exists", 0),
         para("A business plan that describes software which has not been written is a "
              "pitch. This chapter is a description of running code, and every claim in it "
              "is reproducible by a command listed in Appendix B."),

         heading("4.1 &nbsp; What BatchTwin is", 1),
         para("A digital layer over the customer's existing Odoo ERP that runs a batch as it "
              "actually happens &mdash; every gram, every check, every signature, every "
              "kilowatt-hour &mdash; and emits a compliant, paperless batch record."),
         Spacer(1, 3),
         table(["Layer", "What it does", "Status"],
               [["Dossier engine", "Parses the customer's own `.docx` templates into fillable "
                 "digital forms; the product specification overlays the identification block "
                 "so identity is never retyped.", "Built, 1,205 fields [MEASURED]"],
                ["Lifecycle &amp; gating", "Five stages (DFA, DCOI, DCOII, DCT, release) with "
                 "role-based signature gates. Release is blocked until every stage is signed "
                 "and every check passed.", "Built"],
                ["Identity &amp; signatures", "PBKDF2-HMAC-SHA256, 240,000 rounds, per-user "
                 "salt, constant-time compare. Password re-entered at every signature per "
                 "21 CFR 11.200 [SOURCED] Ref [20].", "Built"],
                ["Audit trail", "Hash-chained records plus an external append-only anchor "
                 "file, so a full-database rewrite is still detectable.", "Built"],
                ["Cost &amp; mass balance", "True consumed quantity versus theoretical BOM; "
                 "yield, loss and real cost per unit.", "Built; magnitude needs real weighing"],
                ["SPC", "X&#772;/R control chart, Western Electric rules, OLS drift forecast "
                 "against specification limits.", "Built and validated against a worked example"],
                ["V&Eacute;RA", "Raw-material forecasting, FEFO with shelf-life projection, "
                 "reorder point with safety stock.", "Built on seeded data"],
                ["Recovery advisor", "Case-based recommendation from the site's own closed "
                 "deviations, ranking fixes that held above fixes that recurred.", "Built"],
                ["Odoo integration", "XML-RPC `execute_kw`; **read-only by construction**.",
                 "Mock and live adapters; live untested against a production Odoo"]],
               [34 * mm, 90 * mm, 46 * mm]),

         Spacer(1, 6),
         heading("4.2 &nbsp; Measured evidence", 1),
         para("Numbers produced by running the code, not by describing it:"),
         Spacer(1, 3),
         table(["Metric", "Value", "How it is produced"],
               [["Dossier fields digitalised", "1,205", "`docx_forms.load_all('dossier')` across four real templates"],
                ["Tappable conformity checks", "135", "adjacent S/NS and C/NC cells merged into one control"],
                ["Blank paper rows eliminated", "570", "runs of &ge;3 identical empty rows collapsed to a growable block"],
                ["Repeatable blocks", "27", "tables that grow on demand instead of being pre-printed"],
                ["Dossier templates &rarr; one adaptive form", "4 &rarr; 1", "the product spec overlays the identification block"],
                ["Manual retyping of product identity", "4 &rarr; 0", "identity comes from the versioned specification"],
                ["API routes", "84", "`backend/main.py`"],
                ["Backend source lines", "6,609", "`find backend -name '*.py' | xargs wc -l`"],
                ["Automated tests passing", "143 (8 skipped)", "`python -m pytest -q`"],
                ["Industry profiles supported", "4", "pharma GMP, cosmetics, food HACCP, medical device"]],
               [56 * mm, 26 * mm, 88 * mm], align_right=(1,)),

         Spacer(1, 6),
         heading("4.3 &nbsp; Unit economics of a real lot", 1),
         para(f"Computed from Medicka's actual bill of materials for the demonstration "
              f"product &mdash; magnesium citrate and vitamin B6 oral syrup, 200 mL, "
              f"{UE['units']}-unit lot:"),
         Spacer(1, 3),
         table(["Measure", "Value (TND)", "Value (EUR)", "Note"],
               [["Theoretical material cost per lot", f"{UE['bom_tnd']:,.2f}", f"{UE['bom_eur']:,.2f}",
                 "what Odoo believes [MEASURED]"],
                ["Material cost per unit", f"{UE['cost_per_unit_tnd']:.4f}", f"{UE['cost_per_unit_eur']:.4f}",
                 "11 BOM lines, real supplier costs"],
                ["Actual consumed", "unknown", "unknown", "no site measures this today"],
                ["Material loss", "unknown", "unknown", "**the number BatchTwin creates**"]],
               [58 * mm, 28 * mm, 26 * mm, 58 * mm], align_right=(1, 2)),
         Spacer(1, 5),
         para("The full 11-line bill of materials is reproduced in Appendix C. We show it "
              "because it is the difference between a plan asserting that material loss "
              "exists and a plan demonstrating the mechanism that will measure it."),

         heading("4.4 &nbsp; What is deliberately not claimed", 1)]
    s += bullets([
        "**No live Odoo connection has been tested** against a customer's production "
        "instance. The XML-RPC contract has a mock and a live adapter and a contract test, "
        "but the live path is unproven. This is the largest technical risk and appears in "
        "the Chapter 12 register.",
        "**Material-loss magnitude is unmeasured.** The mechanism is real code on a real "
        "BOM; the figure it produced in the demo came from simulated weighing.",
        "**V&Eacute;RA's figures are synthetic.** Stock-truth gap, expiry exposure and dead "
        "stock are computed deterministically from a seeded dataset, not from Medicka's "
        "warehouse.",
        "**Label OCR is not usable with the installed model.** The pipeline is correct, "
        "including an adaptive resolution ladder; the 2-billion-parameter vision model on "
        "the development machine is too weak to read a nutrition label. Manual entry is the "
        "primary path and always works.",
        "**Validation deliverables are not templated.** URS, IQ, OQ and PQ are sold as a "
        "service in the price list but exist today as a scope, not as documents.",
    ])
    s += [Spacer(1, 5),
          kpibox("Chapter 4 &mdash; product KPIs", [
              ("Dossier fields", "1,205", "MEASURED", "docx_forms parser"),
              ("Conformity checks", "135", "MEASURED", "S/NS + C/NC merge"),
              ("Blank rows eliminated", "570", "MEASURED", "repeatable-block collapse"),
              ("API routes", "84", "MEASURED", "backend/main.py"),
              ("Tests passing", "143", "MEASURED", "pytest"),
              ("Backend LOC", "6,609", "MEASURED", "wc -l"),
              ("Material cost per lot", money(UE["bom_tnd"]), "MEASURED", "analytics.mass_balance()"),
              ("Live Odoo connection", "unproven", "&mdash;", "risk R1, Ch.12"),
          ]),
          PageBreak()]
    return s


def ch5():
    s = [heading("5 &nbsp; Competitive advantage", 0),
         para("Four advantages are structural &mdash; they come from a design decision a "
              "competitor would have to reverse to copy. The rest are execution, and "
              "execution is copyable."),

         heading("5.1 &nbsp; Competitive landscape", 1),
         table(["Alternative", "What it costs", "Why the customer does not choose it"],
               [["Stay on paper", "Nothing visible", "Costing is guesswork, release is slow, "
                 "and an inspection finding is existential. The real incumbent."],
                ["MasterControl", "From $1,000/month per feature, more per site [SOURCED]",
                 "Priced for multinationals; licensing limits and per-site cost are the "
                 "specific complaints in customer reviews."],
                ["Werum PAS-X (K&ouml;rber)", "18&ndash;24 months, six-figure consulting [SOURCED]",
                 "Implementation timeline alone disqualifies an SME; tight coupling to the "
                 "vendor ecosystem."],
                ["Odoo Quality module", "Included in Odoo", "Records checks. Does not produce "
                 "a compliant dossier de lot and has no Part 11 signatures."],
                ["Build in-house", "18 months of engineering", "No validation experience, and "
                 "the maintenance burden never ends."]],
               [34 * mm, 44 * mm, 92 * mm]),

         Spacer(1, 6),
         heading("5.2 &nbsp; The four structural advantages", 1),

         heading("5.2.1 &nbsp; We read the customer's own documents", 2),
         para("Every competing eBR requires the customer to re-implement their dossiers inside "
              "the vendor's data model. That work &mdash; not the licence &mdash; is where most "
              "of an eBR project's cost and nearly all of its schedule risk lives; integration "
              "causes more delay than any other part of these projects [SOURCED]."),
         para("BatchTwin parses the `.docx` files the customer already has. Four of Medicka's "
              "real dossiers became **1,205 fillable fields with zero transcription** "
              "[MEASURED]. Commercially this is the demonstration that closes the sale: a "
              "prospect emails a dossier and sees it running as a tablet form in the same "
              "meeting. No competitor can answer that in a meeting."),

         heading("5.2.2 &nbsp; On-premise by default", 2),
         para("The AI runs on a local Ollama model and the database is the customer's. Batch "
              "data and formulas never leave the site. A QA Director who hears \"your formulas "
              "stay on your server\" relaxes; one who hears \"our cloud\" opens an Annex 11 "
              "supplier-audit conversation that can add months."),
         para("There is a second, quieter benefit that shows up in Chapter 7: **we carry no "
              "per-customer cloud cost.** The largest variable cost line a SaaS competitor "
              "carries is absent from our P&amp;L by construction, which is why gross margin "
              "on licence revenue is close to total."),

         heading("5.2.3 &nbsp; The Odoo integration cannot corrupt the ERP", 2),
         para("BatchTwin reads from Odoo over XML-RPC and never writes to it. This began as "
              "caution and turned out to be the strongest sentence in the sales conversation: "
              "the customer cannot be harmed by the integration, so the IT objection &mdash; "
              "usually the slowest one to clear &mdash; never forms. It also means an evaluator "
              "asking \"what happens when your sensor data clutters their ERP?\" has an answer "
              "in the architecture rather than in a policy."),

         heading("5.2.4 &nbsp; Adaptive intelligence that cites its evidence", 2),
         para("Every deviation QA closes carries a root cause, a CAPA and a disposition. That "
              "is a case base the plant writes itself. When a new problem appears &mdash; or "
              "when SPC forecasts a breach and nothing has failed yet &mdash; the advisor "
              "retrieves matching closed cases and reports what was done and **whether it "
              "held**. A CAPA that recurred afterwards ranks below one that did not."),
         para("It is deliberately not a trained model. Every recommendation names the lot, the "
              "date and the person who signed it, so an operator can go and read that dossier. "
              "A probability score gives them nothing to act on, and a GMP operator cannot sign "
              "against 0.83. It also works from lot one, with no dataset to collect."),

         Spacer(1, 4),
         callout("The honest limit of the moat",
                 "The `.docx` parser is the defensible asset, and it is defensible for perhaps "
                 "two years rather than forever &mdash; a well-resourced competitor could build "
                 "one. The durable moat is not the parser; it is the accumulated dossier "
                 "templates, industry profiles, and closed-deviation case bases of installed "
                 "customers, all of which get more valuable per customer and none of which "
                 "transfer to a competitor. That is why the plan prioritises reference "
                 "customers over margin in year 1.", "info"),

         Spacer(1, 5),
         heading("5.3 &nbsp; Positioning against AI claims", 1),
         para("A word on discipline, because it is a competitive advantage in a regulated "
              "market. Only two components of BatchTwin use machine learning: the retrieval "
              "copilot and the vision label reader. The SPC forecast is ordinary least "
              "squares; V&Eacute;RA's seasonal coefficients are written by hand. We say so in "
              "the documentation and in the pitch."),
         para("The reason is regulatory rather than modest. An inspector can validate a control "
              "chart &mdash; the constants come from ASTM STP-15D / ISO 7870-2 and the "
              "arithmetic is one page. Validating a trained model means qualifying its "
              "training data, versioning weights and re-proving behaviour after every retrain. "
              "**No learned model sits in a release-critical path**, and a test asserts the "
              "assistant module contains no write path at all."),

         Spacer(1, 4),
         kpibox("Chapter 5 &mdash; advantage KPIs", [
             ("Transcription required to onboard a dossier", "zero", "MEASURED", "parser reads customer .docx"),
             ("Fields onboarded from 4 real dossiers", "1,205", "MEASURED", "docx_forms"),
             ("Per-customer cloud cost", "0 TND", "DERIVED", "on-premise deployment, Ch.7"),
             ("Write operations against customer Odoo", "0", "MEASURED", "read-only adapter + contract test"),
             ("ML components in release-critical path", "0", "MEASURED", "AssistantReadOnlyTests"),
             ("Advisor cold-start requirement", "none", "MEASURED", "case base from lot one"),
         ]),
         Spacer(1, 4),
         srcbox(["[1] Capterra &mdash; MasterControl", "[12] BatchLine &mdash; PAS-X",
                 "[13] A3P &mdash; eBR opportunities and pitfalls",
                 "[14] Vimachem &mdash; eBR in MES"]),
         PageBreak()]
    return s


def ch6():
    p = FM.PLANS
    s = [heading("6 &nbsp; Business model and pricing", 0),
         callout("No price in this chapter has been tested with a customer",
                 "What follows is the reasoning first and the number second, so the figure can "
                 "be argued with rather than merely quoted. Every price is an **opening "
                 "position derived from public anchors**, not a validated rate card. What "
                 "would change it: three customer conversations.", "warn"),

         Spacer(1, 5),
         heading("6.1 &nbsp; Who actually buys", 1),
         para("**Not** the operator who uses it, and not the IT department. The buyer is the "
              "**Pharmacien Responsable or QA Director** &mdash; the person who personally "
              "signs release and personally carries the regulatory risk. The production manager "
              "is the champion because it removes their paperwork, finance approves it because "
              "it exposes real cost per lot, and IT only has to not object &mdash; which is "
              "why read-only integration matters commercially."),
         para("This shapes the pitch: **risk and traceability first, efficiency second**. A QA "
              "Director does not buy time savings. They buy the ability to answer an inspector."),

         heading("6.2 &nbsp; The two public anchors", 1),
         table(["Anchor", "Figure", "Source"],
               [["Enterprise eBR", "MasterControl from **$1,000/month per feature**, additional "
                 "cost per site", "[SOURCED] Ref [1]"],
                ["What the customer already pays for software", "Odoo Enterprise "
                 "**$8.95&ndash;$76.20 per user per month**, Middle East at the bottom of the "
                 "band", "[SOURCED] Ref [2]"]],
               [42 * mm, 78 * mm, 50 * mm]),
         Spacer(1, 5),
         para("**The rule those anchors produce:** price *above* what the customer already pays "
              "for their ERP &mdash; BatchTwin carries more regulatory risk than Odoo does "
              "&mdash; and *an order of magnitude below* enterprise MES, because being "
              "affordable to a 100-person site is the entire reason the product exists."),

         heading("6.3 &nbsp; Per site, and this one is not negotiable", 1),
         para("Operators are shift workers on shared tablets. Per-user pricing punishes exactly "
              "the behaviour the product depends on &mdash; every person recording their own "
              "actions under their own identity &mdash; and pushes customers toward shared "
              "logins, which destroys the Part 11 identity model the whole compliance story "
              "rests on. **A pricing model that undermines the product's core claim is the "
              "wrong model at any price.**"),

         heading("6.4 &nbsp; The opening price list", 1),
         table(["Plan", "Scope", "Annual per site"],
               [["Essential", p["Essential"]["scope"], f"**{money(p['Essential']['annual_tnd'])}**"],
                ["Standard", p["Standard"]["scope"], f"**{money(p['Standard']['annual_tnd'])}**"],
                ["Enterprise", "Multi-site, hybrid dashboard, SSO, priority SLA",
                 f"**{money(p['Enterprise']['annual_tnd'])}** + "
                 f"{money(p['Enterprise']['group_fee_tnd'])} group"]],
               [26 * mm, 92 * mm, 52 * mm], align_right=(2,)),
         Spacer(1, 5),
         para("**How Standard was derived, so it can be argued with:**"),
         ] + bullets([
        f"A ~100-person site pays roughly **34,000&ndash;84,000 TND per year** for Odoo "
        f"Enterprise at Maghreb rates [DERIVED from Ref [2] at 40 users]. "
        f"{money(p['Standard']['annual_tnd'])} sits inside that band &mdash; defensible, "
        f"because BatchTwin carries the regulatory record and Odoo does not.",
        f"MasterControl opens at $1,000 per month for one feature and charges again per "
        f"site; a comparable eBR deployment lands in six figures USD. "
        f"{money(p['Standard']['annual_tnd'])} is roughly a tenth, which is the entire "
        f"reason this product can exist for this segment.",
        f"At about {money(p['Standard']['annual_tnd'] / 12)} per month it is a line item a "
        f"QA Director can approve without a board paper. Above roughly 65,000 TND it becomes "
        f"a capital decision with a committee, and the sales cycle doubles.",
    ]) + [
        Spacer(1, 5),
        heading("6.5 &nbsp; Services &mdash; where early revenue actually comes from", 1),
        para(f"Priced from a derived day rate rather than invented. A loaded senior engineer "
             f"costs about **{money(FM.ENG_MONTHLY_TND)} per month** in Tunis [SOURCED range "
             f"3,500&ndash;7,000+]. Over {FM.WORKING_DAYS_PER_MONTH} working days at a "
             f"{FM.BILL_MULTIPLIER:.0f}&times; services multiplier that gives "
             f"**{money(FM.DAY_RATE_TND)} per day** [DERIVED]."),
        Spacer(1, 3),
        table(["Service", "Days", "Price", "What it covers"],
              [[r["name"], str(r["days"]), money(r["price_tnd"]), r["note"]] for r in SVC]
              + [["**Total, first year**", f"**{sum(r['days'] for r in SVC)}**",
                  f"**{money(FM.services_total())}**", "one-off, not recurring"]],
              [52 * mm, 14 * mm, 28 * mm, 76 * mm], align_right=(1, 2),
              bold_rows=(len(SVC),)),
        Spacer(1, 5),
        callout("Benchmark this before quoting it",
                "The customer's mental comparable is not MasterControl &mdash; it is what a "
                "local Odoo integrator charges per day in Tunisia. That is a number obtainable "
                "in a week and it should be obtained before the first quote goes out. Our day "
                "rate is derived from salary data, which is a reasonable proxy and not the "
                "same thing as a market rate.", "warn"),

        Spacer(1, 5),
        heading("6.6 &nbsp; Licensing and support", 1),
        para("**Commercial licence, source available to the customer.** Each customer receives "
             "the source for their deployment under a non-redistribution licence. This is "
             "unusual and deliberate: a GMP customer must be able to satisfy an inspector "
             "about what the system does, and \"trust us, it is a black box\" is a weak answer "
             "under Annex 11. Escrow is offered for Enterprise."),
        para("Not open source &mdash; the `.docx` parser is the defensible asset and giving it "
             "away removes the moat. [ASSUMPTION] Worth revisiting if adoption stalls; an open "
             "core with commercial compliance modules is a credible fallback."),
        para("**Support is bundled into the subscription, not sold separately, and "
             "regulatory-change updates are included.** A customer must never face a bill to "
             "stay compliant, and saying so removes the main objection to subscription pricing "
             "in a regulated industry."),

        Spacer(1, 4),
        kpibox("Chapter 6 &mdash; pricing KPIs", [
            ("Essential", money(p["Essential"]["annual_tnd"]), "DERIVED", "anchor band, Ref [1][2]"),
            ("Standard", money(p["Standard"]["annual_tnd"]), "DERIVED", "just above Odoo bill"),
            ("Enterprise per site", money(p["Enterprise"]["annual_tnd"]), "DERIVED", "+ group fee"),
            ("Services day rate", money(FM.DAY_RATE_TND), "DERIVED",
             f"{money(FM.ENG_MONTHLY_TND)}/{FM.WORKING_DAYS_PER_MONTH}d &times; {FM.BILL_MULTIPLIER:.0f}"),
            ("First-year services", money(FM.services_total()), "DERIVED", "47 days total"),
            ("Average first-year contract", money(MK["avg_first_year_contract_tnd"]), "DERIVED",
             "Standard + services"),
            ("Prices validated with customers", "0", "&mdash;", "open question #3"),
        ]),
        Spacer(1, 4),
        srcbox(["[1] Capterra &mdash; MasterControl pricing", "[2] OEC.sh &mdash; Odoo pricing by country",
                "[3] Odoo official pricing", "[15] Glassdoor / levels.fyi &mdash; Tunis engineer salary"]),
        PageBreak()]
    return s


def ch7():
    y1, y2, y3 = M[1], M[2], M[3]
    s = [heading("7 &nbsp; Cost structure and unit economics", 0),
         para("What it costs to run this company, and what one customer is worth."),

         heading("7.1 &nbsp; Cost base", 1),
         para("Payroll dominates, as it should in a software company. Three founders in year "
              "one, stepping up pay as revenue allows and adding delivery capacity rather than "
              "sales headcount &mdash; in a market with a 6&ndash;12 month sales cycle, "
              "delivery quality generates the next reference, and the reference generates the "
              "next sale."),
         Spacer(1, 3),
         table(["Cost line", "Year 1", "Year 2", "Year 3", "Basis"],
               [["Headcount", str(FM.HEADCOUNT[1]), str(FM.HEADCOUNT[2]), str(FM.HEADCOUNT[3]),
                 "[ASSUMPTION] +1 support Y2, +2 delivery Y3"],
                ["Monthly pay per head", money(FM.FOUNDER_MONTHLY_TND[1]),
                 money(FM.FOUNDER_MONTHLY_TND[2]), money(FM.FOUNDER_MONTHLY_TND[3]),
                 "[ASSUMPTION] below market in Y1, at market by Y3"],
                ["Payroll", money(y1["payroll_tnd"]), money(y2["payroll_tnd"]),
                 money(y3["payroll_tnd"]), "headcount &times; pay &times; 12"],
                ["Other operating cost", money(y1["opex_tnd"]), money(y2["opex_tnd"]),
                 money(y3["opex_tnd"]), "infrastructure, legal, travel, marketing"],
                ["**Total cost**", f"**{money(y1['cost_tnd'])}**", f"**{money(y2['cost_tnd'])}**",
                 f"**{money(y3['cost_tnd'])}**", ""]],
               [38 * mm, 28 * mm, 28 * mm, 28 * mm, 48 * mm],
               align_right=(1, 2, 3), bold_rows=(4,)),

         Spacer(1, 6),
         heading("7.2 &nbsp; Operating cost detail", 1),
         table(["Line", "Year 1", "Year 2", "Year 3", "Note"],
               [[k, money(FM.OPEX_TND[1][k]), money(FM.OPEX_TND[2][k]), money(FM.OPEX_TND[3][k]),
                 note] for k, note in [
                    ("Infrastructure & tooling", "development and CI only &mdash; no customer hosting"),
                    ("Legal, accounting, company", "company formation, annual filings"),
                    ("Travel & GMP events", "the buyer attends pharma-quality conferences, not software ones"),
                    ("Marketing & collateral", "case studies and validation documentation, not advertising")]],
               [40 * mm, 25 * mm, 25 * mm, 25 * mm, 55 * mm], align_right=(1, 2, 3)),

         Spacer(1, 6),
         callout("The structural margin advantage: no per-customer cloud bill",
                 "BatchTwin deploys on the customer's own server. Infrastructure spend stays "
                 "flat as customers are added, because it covers our development and CI only. "
                 "A SaaS competitor's largest variable cost line &mdash; per-tenant hosting "
                 "&mdash; is absent from this P&amp;L by construction. That is why gross margin "
                 "on licence revenue is effectively total, and why the marginal cost of the "
                 "next customer is support time rather than infrastructure.", "good"),

         Spacer(1, 6),
         heading("7.3 &nbsp; What one customer is worth", 1),
         table(["Measure", "Value", "How"],
               [["First-year contract value", money(MK["avg_first_year_contract_tnd"]),
                 "Standard plan + first-year services [DERIVED]"],
                ["Recurring annual value thereafter", money(FM.PLANS["Standard"]["annual_tnd"]),
                 "licence only [DERIVED]"],
                ["Year-3 average revenue per account", money(y3["arpa_tnd"]),
                 "licence revenue &divide; active sites [DERIVED]"],
                ["Assumed annual churn", "1&ndash;2 sites per year",
                 "[ASSUMPTION] no evidence; regulated customers are sticky once validated"],
                ["Marginal cost of an additional site", "support time only",
                 "no hosting cost; see &sect;7.2 [DERIVED]"]],
               [56 * mm, 38 * mm, 76 * mm], align_right=(1,)),

         Spacer(1, 6),
         heading("7.4 &nbsp; The services-dependence problem", 1),
         para(f"In year 1, **{y1['services_tnd'] / y1['revenue_tnd'] * 100:.0f}%** of revenue "
              f"is one-off services. By year 3 that falls to "
              f"**{y3['services_tnd'] / y3['revenue_tnd'] * 100:.0f}%** [DERIVED]. The "
              f"direction is right, but the year-1 figure means BatchTwin begins life as a "
              f"consultancy that happens to own software."),
         para("This is normal for early enterprise software and it is still a risk, because "
              "services revenue does not compound and does not survive the founders' time "
              "being fully committed. The mitigation is explicit: **every hour of "
              "implementation work should reduce the hours the next implementation needs.** "
              "The `.docx` parser already embodies that principle &mdash; it is the reason "
              "onboarding is 20 days rather than months &mdash; and the target is to templatise "
              "the validation pack next, because it is the largest remaining manual "
              "deliverable."),

         Spacer(1, 4),
         kpibox("Chapter 7 &mdash; economics KPIs", [
             ("Year-1 total cost", money(y1["cost_tnd"]), "DERIVED", "payroll + opex"),
             ("Year-3 total cost", money(y3["cost_tnd"]), "DERIVED", "6 heads"),
             ("First-year contract value", money(MK["avg_first_year_contract_tnd"]), "DERIVED",
              "Standard + services"),
             ("Year-3 ARPA", money(y3["arpa_tnd"]), "DERIVED", "licence &divide; sites"),
             ("Per-customer infrastructure cost", "0 TND", "DERIVED", "on-premise"),
             ("Services share of revenue, Y1 &rarr; Y3",
              f"{y1['services_tnd'] / y1['revenue_tnd'] * 100:.0f}% &rarr; "
              f"{y3['services_tnd'] / y3['revenue_tnd'] * 100:.0f}%", "DERIVED", "declining, by design"),
         ]),
         Spacer(1, 4),
         srcbox(["[15] Glassdoor / levels.fyi / worldsalaries &mdash; Tunisia engineer salary"]),
         PageBreak()]
    return s


def ch8():
    y1, y2, y3 = M[1], M[2], M[3]
    s = [heading("8 &nbsp; Three-year financial projection", 0),
         para("Everything in this chapter is [DERIVED] from the assumptions in Appendix D via "
              "`docs/finance_model.py`. Change an assumption, rerun the model, and every figure "
              "moves together &mdash; including the ones that make the plan look worse."),

         heading("8.1 &nbsp; Customer ramp", 1),
         para("Deliberately slow. The sales cycle in regulated manufacturing is 6&ndash;12 "
              "months and requires QA sign-off; any plan assuming fast bottom-up adoption in "
              "GMP is wrong."),
         Spacer(1, 3),
         table(["Year", "New", "Churn", "Active", "Tunisia / Maghreb", "What happens"],
               [[str(y), str(FM.RAMP[y]["new"]), str(FM.RAMP[y]["churn"]),
                 str(M[y]["active_sites"]), f"{FM.RAMP[y]['tn']} / {FM.RAMP[y]['mg']}",
                 FM.RAMP[y]["note"]] for y in (1, 2, 3)],
               [14 * mm, 14 * mm, 15 * mm, 16 * mm, 28 * mm, 83 * mm],
               align_right=(1, 2, 3)),

         Spacer(1, 6),
         heading("8.2 &nbsp; Plan mix", 1),
         table(["Year", "Essential", "Standard", "Enterprise", "Total sites"],
               [[str(y), str(FM.MIX[y]["Essential"]), str(FM.MIX[y]["Standard"]),
                 str(FM.MIX[y]["Enterprise"]), str(M[y]["active_sites"])] for y in (1, 2, 3)],
               [26 * mm, 34 * mm, 34 * mm, 34 * mm, 42 * mm], align_right=(1, 2, 3, 4)),
         Spacer(1, 4),
         para("The model asserts that the mix sums to the active site count for every year and "
              "fails loudly if it does not. A plan whose customer mix disagrees with its own "
              "customer count is a plan nobody should read past."),

         Spacer(1, 5),
         heading("8.3 &nbsp; Profit and loss", 1),
         table(["", "Year 1", "Year 2", "Year 3"],
               [["Active sites", y1["active_sites"], y2["active_sites"], y3["active_sites"]],
                ["Licence revenue", money(y1["licence_tnd"]), money(y2["licence_tnd"]),
                 money(y3["licence_tnd"])],
                ["Services revenue", money(y1["services_tnd"]), money(y2["services_tnd"]),
                 money(y3["services_tnd"])],
                ["**Total revenue**", f"**{money(y1['revenue_tnd'])}**",
                 f"**{money(y2['revenue_tnd'])}**", f"**{money(y3['revenue_tnd'])}**"],
                ["Payroll", money(y1["payroll_tnd"]), money(y2["payroll_tnd"]), money(y3["payroll_tnd"])],
                ["Other operating cost", money(y1["opex_tnd"]), money(y2["opex_tnd"]), money(y3["opex_tnd"])],
                ["**Total cost**", f"**{money(y1['cost_tnd'])}**", f"**{money(y2['cost_tnd'])}**",
                 f"**{money(y3['cost_tnd'])}**"],
                ["**Profit**", f"**{money(y1['profit_tnd'])}**", f"**{money(y2['profit_tnd'])}**",
                 f"**{money(y3['profit_tnd'])}**"],
                ["Net margin", f"{y1['margin_pct']}%", f"{y2['margin_pct']}%", f"{y3['margin_pct']}%"],
                ["Cumulative cash", money(y1["cumulative_cash_tnd"]), money(y2["cumulative_cash_tnd"]),
                 money(y3["cumulative_cash_tnd"])],
                ["Exit ARR (licence)", money(y1["arr_exit_tnd"]), money(y2["arr_exit_tnd"]),
                 money(y3["arr_exit_tnd"])]],
               [46 * mm, 41 * mm, 41 * mm, 42 * mm], align_right=(1, 2, 3),
               bold_rows=(3, 6, 7)),

         Spacer(1, 6),
         callout("Three things to notice before believing this table",
                 f"**One.** Profitability in year 1 depends on founders accepting "
                 f"{money(FM.FOUNDER_MONTHLY_TND[1])} per month. Pay market salaries from day "
                 f"one and year 1 is a loss. **Two.** Exit ARR of "
                 f"{money(y3['arr_exit_tnd'])} is the number that matters for a software "
                 f"business, not the {money(y3['revenue_tnd'])} total &mdash; services revenue "
                 f"does not compound. **Three.** Every customer number in this table is an "
                 f"[ASSUMPTION]. The revenue arithmetic is sound; the customer count is a "
                 f"forecast, and Chapter 9 shows what happens when it is wrong.", "warn"),

         Spacer(1, 5),
         heading("8.4 &nbsp; Revenue quality over time", 1),
         table(["Year", "Licence (recurring)", "Services (one-off)", "Recurring share"],
               [[str(y), money(M[y]["licence_tnd"]), money(M[y]["services_tnd"]),
                 f"{M[y]['licence_tnd'] / M[y]['revenue_tnd'] * 100:.0f}%"] for y in (1, 2, 3)],
               [26 * mm, 48 * mm, 48 * mm, 48 * mm], align_right=(1, 2, 3)),
         Spacer(1, 4),
         para("Recurring share rising from "
              f"{y1['licence_tnd'] / y1['revenue_tnd'] * 100:.0f}% to "
              f"{y3['licence_tnd'] / y3['revenue_tnd'] * 100:.0f}% is the single most "
              "important trend in this chapter. It is the difference between building a "
              "software company and running a consultancy."),

         Spacer(1, 4),
         kpibox("Chapter 8 &mdash; projection KPIs", [
             ("Year-1 revenue", money(y1["revenue_tnd"]), "DERIVED", "3 sites + services"),
             ("Year-2 revenue", money(y2["revenue_tnd"]), "DERIVED", "7 sites"),
             ("Year-3 revenue", money(y3["revenue_tnd"]), "DERIVED", "15 sites"),
             ("Year-3 exit ARR", money(y3["arr_exit_tnd"]), "DERIVED", "licence only"),
             ("Year-3 net margin", f"{y3['margin_pct']}%", "DERIVED", "profit &divide; revenue"),
             ("Cumulative 3-year cash", money(y3["cumulative_cash_tnd"]), "DERIVED", "no external funding"),
             ("Recurring revenue share, Y3", f"{y3['licence_tnd'] / y3['revenue_tnd'] * 100:.0f}%",
              "DERIVED", "licence &divide; total"),
         ]),
         PageBreak()]
    return s


def ch9():
    y2, y3 = M[2], M[3]
    s = [heading("9 &nbsp; Break-even and sensitivity", 0),
         para("A projection is worth reading only alongside the conditions that break it. This "
              "chapter is where the plan tries to falsify itself."),

         heading("9.1 &nbsp; Break-even on recurring revenue", 1),
         para("Services revenue can carry the company early, but it does not recur. The "
              "meaningful question is how many sites are needed for **licence revenue alone** "
              "to cover the cost base."),
         Spacer(1, 3),
         table(["Input", "Value", "Source"],
               [["Annual cost base (year 2)", money(BE["annual_cost_tnd"]), "[DERIVED] payroll + opex"],
                ["Average licence per site", money(BE["avg_licence_tnd"]), "[DERIVED] year-2 plan mix"],
                ["**Sites required to break even**",
                 f"**{BE['sites_for_breakeven_on_licence_alone']}**",
                 "cost &divide; average licence"]],
               [58 * mm, 40 * mm, 72 * mm], align_right=(1,), bold_rows=(2,)),
         Spacer(1, 5),
         para(f"The plan reaches {BE['sites_for_breakeven_on_licence_alone']} sites during "
              f"**year 3**. Before that point the company is solvent because of services and "
              f"below-market founder pay, not because the product business works yet. Stating "
              f"it that way is the difference between a plan and a pitch."),

         Spacer(1, 5),
         heading("9.2 &nbsp; Sensitivity", 1),
         para("Each row varies one driver and holds everything else constant, against year 3:"),
         Spacer(1, 3),
         table(["Scenario", "Year-3 revenue", "Year-3 profit", "vs base"],
               [[r["scenario"], money(r["y3_revenue_tnd"]), money(r["y3_profit_tnd"]),
                 f"{r['delta_vs_base_pct']:+.1f}%"] for r in SENS],
               [50 * mm, 40 * mm, 40 * mm, 40 * mm], align_right=(1, 2, 3),
               bold_rows=(1,)),

         Spacer(1, 6),
         callout("The finding that matters",
                 f"Price is not the sensitive variable &mdash; a 25% price cut costs "
                 f"{abs(SENS[0]['delta_vs_base_pct']):.0f}% of revenue and the business stays "
                 f"profitable. **Customer count is the sensitive variable.** Halving it turns a "
                 f"{money(y3['profit_tnd'])} profit into a "
                 f"{money(abs(SENS[3]['y3_profit_tnd']))} loss. Everything therefore depends on "
                 f"the customer ramp, which is the least evidenced part of the plan &mdash; "
                 f"which is precisely why Chapter 3 refuses to state a market share it cannot "
                 f"support, and why the go-to-market in Chapter 10 is built around a single "
                 f"reference customer rather than a marketing spend.", "bad"),

         Spacer(1, 6),
         heading("9.3 &nbsp; What would have to be true", 1),
         para("For this plan to work, all of the following must hold. Any one failing is "
              "material:"),
         ] + bullets([
        "**Medicka becomes a live reference customer.** Without a named GMP site in "
        "production, the year-2 ramp has no engine.",
        "**Roughly one new site per quarter can be closed from year 2.** At a 6&ndash;12 "
        "month cycle that implies a pipeline of 8&ndash;12 qualified prospects held "
        "continuously &mdash; which requires the market count that Chapter 3 says we do not have.",
        "**Implementation stays near 20 days.** If real onboarding takes 40 days, services "
        "stop being profitable and start consuming the delivery capacity that year-3 growth "
        "depends on.",
        "**The live Odoo integration works at a customer site.** Unproven today; risk R1.",
        "**Churn stays at or below 1&ndash;2 sites per year.** Plausible for validated "
        "systems, but entirely unevidenced &mdash; we have never had a customer to churn.",
    ]) + [
        Spacer(1, 5),
        heading("9.4 &nbsp; The downside case, stated", 1),
        para(f"If the customer ramp halves &mdash; three sites in year 2 rather than five, and "
             f"five in year 3 rather than ten &mdash; year-3 revenue lands near "
             f"**{money(SENS[3]['y3_revenue_tnd'])}** against a cost base of "
             f"**{money(y3['cost_tnd'])}**, a loss of about "
             f"**{money(abs(SENS[3]['y3_profit_tnd']))}** [DERIVED]. The company does not fail "
             f"at that point, because the cost base is mostly founder salaries that can be "
             f"reduced again, but it stops being a growth business and becomes a two-customer "
             f"consultancy."),
        para("The honest signal to watch is not revenue. It is **whether the second customer "
             "closes without a founder in the room.** Until that happens, the go-to-market is "
             "unproven regardless of what the revenue line says."),

        Spacer(1, 4),
        kpibox("Chapter 9 &mdash; risk KPIs", [
            ("Break-even sites, licence only", f"{BE['sites_for_breakeven_on_licence_alone']}",
             "DERIVED", "cost &divide; avg licence"),
            ("Year reached", "Year 3", "DERIVED", "customer ramp"),
            ("Revenue impact, &minus;25% price", f"{SENS[0]['delta_vs_base_pct']:+.1f}%", "DERIVED",
             "still profitable"),
            ("Revenue impact, half the customers", f"{SENS[3]['delta_vs_base_pct']:+.1f}%", "DERIVED",
             f"loss of {money(abs(SENS[3]['y3_profit_tnd']))}"),
            ("Most sensitive driver", "customer count", "DERIVED", "not price"),
            ("Pipeline needed from Y2", "8&ndash;12 qualified", "DERIVED", "1 close/quarter at 6&ndash;12mo cycle"),
        ]),
        PageBreak()]
    return s
