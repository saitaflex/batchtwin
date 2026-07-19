"""Business plan content, part C: chapters 10-14, appendices, references."""
from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

import finance_model as FM
from build_business_plan import (M, UE, BE, SENS, MK, SVC, SS, bullets, callout,
                                 heading, kpibox, money, para, rule, srcbox, table)


def ch10():
    s = [heading("10 &nbsp; Go to market", 0),
         para("The constraint that shapes everything: **the sales cycle in regulated "
              "manufacturing is 6&ndash;12 months and involves QA sign-off.** This is not a "
              "self-serve product. Any plan assuming fast bottom-up adoption is wrong, and a "
              "marketing spend cannot compress a validation decision."),

         heading("10.1 &nbsp; Three channels, in priority order", 1),

         heading("10.1.1 &nbsp; Medicka as reference customer", 2),
         para("One named GMP site in production is worth more than any marketing. The trade is "
              "explicit: favourable first-year pricing &mdash; a "
              f"{FM.REFERENCE_DISCOUNT:.0%} discount is modelled [ASSUMPTION] &mdash; in "
              "exchange for a case study, a site visit for qualified prospects, and permission "
              "to use the name."),
         para("What makes the reference valuable is not the logo. It is that a prospect's QA "
              "Director can telephone Medicka's QA Director and ask the only question that "
              "matters: *did an inspector accept it?*"),

         heading("10.1.2 &nbsp; The Odoo integrator channel", 2),
         para("Integrators already sell to this exact segment and are looking for vertical "
              "differentiation. The usual shape is a margin split on licence with services "
              "retained by the partner. The percentage is a negotiation, not a figure to "
              "publish before one has happened &mdash; **no integrator has been approached "
              "yet**, and that is open question #5."),
         para("Strategically this channel matters more than its revenue share suggests: it is "
              "the only route that scales sales without founder time, and Chapter 9 identifies "
              "\"the second customer closing without a founder in the room\" as the real "
              "signal that the business works."),

         heading("10.1.3 &nbsp; Regulatory events", 2),
         para("The buyer attends GMP and pharma-quality conferences, not software ones. The "
              "travel budget in Chapter 7 is sized for this and is the fastest-growing "
              "operating line, rising from "
              f"{money(FM.OPEX_TND[1]['Travel & GMP events'])} to "
              f"{money(FM.OPEX_TND[3]['Travel & GMP events'])} [ASSUMPTION]."),

         Spacer(1, 5),
         heading("10.2 &nbsp; The sales motion", 1),
         table(["Stage", "What happens", "Duration"],
               [["Qualify", "Confirm GMP scope, ERP in place, batch records still on paper, "
                 "50&ndash;300 staff. Disqualify sites with a validated MES.", "1&ndash;2 weeks"],
                ["Parse their dossier", "The prospect emails one real `.docx` dossier. We "
                 "return it as a running tablet form. **This is the differentiator and it "
                 "should happen in the first meeting.**", "Same meeting"],
                ["Technical evaluation", "QA reviews audit trail, signatures, gating. IT "
                 "confirms read-only Odoo access.", "4&ndash;8 weeks"],
                ["Validation review", "URS agreed; IQ/OQ/PQ scope defined. The slowest stage, "
                 "and the one competitors also cannot compress.", "8&ndash;16 weeks"],
                ["Parallel run", "Both systems live; divergences captured. See Chapter 11.",
                 "4&ndash;8 weeks"],
                ["Cutover", "Paper retired stage by stage.", "2&ndash;4 weeks"]],
               [30 * mm, 106 * mm, 34 * mm]),

         Spacer(1, 6),
         heading("10.3 &nbsp; The demonstration that closes the sale", 1),
         callout("Parse the prospect's own dossier, live",
                 "Every competitor's demonstration shows *their* forms. Ours shows the "
                 "prospect's. A QA Director watching their own DCT template &mdash; the one "
                 "they wrote, with their own 95-row compression table &mdash; become a tablet "
                 "form in front of them is not evaluating a feature list any more. Against "
                 "Medicka's four dossiers this produced 1,205 fields with zero transcription "
                 "[MEASURED]. It is the single most effective thing in the entire go-to-market, "
                 "and it costs one meeting.", "good"),

         Spacer(1, 6),
         heading("10.4 &nbsp; Objection handling", 1),
         table(["Objection", "Answer", "Why it holds"],
               [["\"Is it validated?\"", "No, and no vendor can validate your process for you. "
                 "We supply URS/IQ/OQ/PQ and the source code so your validation team can "
                 "qualify it.", "Honest, and source availability is unusual enough to be "
                 "memorable"],
                ["\"What if it corrupts our Odoo?\"", "It cannot. We never write to Odoo.",
                 "Architectural, not a policy promise"],
                ["\"Our data cannot leave the country.\"", "It never leaves your server. The "
                 "AI runs locally too.", "On-premise by default"],
                ["\"We cannot stop production to migrate.\"", "You do not. Parallel run, then "
                 "stage-by-stage cutover, with QA controlling the switch.", "Enforced in code; "
                 "see Chapter 11"],
                ["\"What happens if a sensor fails?\"", "Documented failure modes, staleness "
                 "detection, and manual entry with provenance marking.", "Built; "
                 "`resilience.py`"],
                ["\"You are three people.\"", "Correct, and it is the real risk. Source escrow "
                 "for Enterprise; the source is yours regardless.", "Does not pretend the risk "
                 "away"]],
               [40 * mm, 68 * mm, 62 * mm]),

         Spacer(1, 5),
         kpibox("Chapter 10 &mdash; go-to-market KPIs", [
             ("Sales cycle", "6&ndash;12 months", "SOURCED", "regulated manufacturing norm"),
             ("Time to parse a prospect dossier", "same meeting", "MEASURED", "docx parser"),
             ("Reference-customer discount", f"{FM.REFERENCE_DISCOUNT:.0%}", "ASSUMPTION", "year 1 only"),
             ("Pipeline required from Y2", "8&ndash;12 qualified", "DERIVED", "1 close per quarter"),
             ("Integrators approached", "0", "&mdash;", "open question #5"),
             ("Travel budget, Y1 &rarr; Y3",
              f"{money(FM.OPEX_TND[1]['Travel & GMP events'])} &rarr; "
              f"{money(FM.OPEX_TND[3]['Travel & GMP events'])}", "ASSUMPTION", "GMP events"),
         ]),
         PageBreak()]
    return s


def ch11():
    s = [heading("11 &nbsp; Migration and deployment", 0),
         para("The objection that kills eBR deals is not price. It is **\"we cannot stop "
              "producing while you install software.\"** Integration work causes more delay "
              "than any other part of an eBR project [SOURCED], and a GMP site that halts "
              "production to accommodate an IT project has made an unrecoverable commercial "
              "mistake."),

         heading("11.1 &nbsp; Parallel run, then staged cutover", 1),
         para("BatchTwin never requires a big-bang switch. Each batch carries a **run mode** "
              "&mdash; paper, parallel, or digital &mdash; and only QA can change it. During "
              "parallel run both systems are live: the paper record remains the legal record, "
              "and BatchTwin runs alongside capturing the same data."),
         Spacer(1, 3),
         table(["Phase", "Legal record", "What it proves", "Typical duration"],
               [["Paper", "Paper", "Baseline. Nothing has changed yet.", "&mdash;"],
                ["Parallel", "Paper", "That the digital record agrees with the paper one, lot "
                 "by lot. Divergences are the deliverable.", "4&ndash;8 weeks"],
                ["Digital", "BatchTwin", "Cutover, stage by stage &mdash; fabrication first, "
                 "release last.", "2&ndash;4 weeks"]],
               [26 * mm, 26 * mm, 84 * mm, 34 * mm]),
         Spacer(1, 5),
         para("The run mode is enforced in code rather than described in a manual, and only a "
              "QA role can advance it. A migration policy that lives in a slide deck is a "
              "policy; one that a non-QA user physically cannot trigger is a control."),

         Spacer(1, 5),
         callout("Parallel run is also how the business case gets its missing number",
                 "The most valuable output of the parallel run is not confidence in the "
                 "software. It is **the first real measurement of material loss** &mdash; the "
                 "figure Odoo structurally cannot produce, and the one input the ROI worksheet "
                 "in &sect;11.3 cannot be completed without. Every parallel run should be "
                 "scoped to capture it deliberately rather than incidentally.", "good"),

         Spacer(1, 5),
         heading("11.2 &nbsp; Operating in a real plant", 1),
         para("A GMP shop floor is not an office. The system is built for the conditions it "
              "will actually meet:"),
         ] + bullets([
        "**Offline first.** Forms, dispensing, QC entry, checklists and packaging all work "
        "without a network and sync afterwards. **Signatures deliberately do not** &mdash; a "
        "Part 11 signature requires live identity verification, and queueing signatures "
        "offline would break the control it exists to provide.",
        "**Sensor failure is a designed-for state, not an exception.** Eight failure modes "
        "are modelled, with staleness thresholds (120 seconds stale, 600 seconds dead) and "
        "provenance marking so a reader can always tell whether a value came from an "
        "instrument, an operator, or a stale cache.",
        "**Shared tablets, individual identity.** Operators sign with their own credentials "
        "on a shared device; the pricing model is per site precisely so nobody is tempted to "
        "share a login.",
        "**Existing instruments, existing qualification.** In production BatchTwin reads the "
        "instruments the plant already owns and already qualifies, over OPC UA, Modbus TCP, "
        "S7/PROFINET and EtherNet/IP. The demonstration rig used during development is a "
        "bench, not a deployment proposal &mdash; a GMP site does not put a breadboard on a "
        "validated line.",
    ]) + [
        Spacer(1, 5),
        heading("11.3 &nbsp; The ROI worksheet &mdash; to be completed with the customer", 1),
        para("There is no ROI figure in this business plan, because computing one honestly "
             "requires four numbers only the customer has. Inventing them would produce a "
             "confident total that collapses the moment anyone asks where it came from."),
        Spacer(1, 3),
        table(["Input", "What to ask for", "Who knows it"],
               [["L", "Lots produced per year", "Production manager &mdash; known today"],
                ["H", "Hours QA spends reviewing one paper batch record", "QA &mdash; known today"],
                ["C", "Loaded hourly cost of a QA reviewer", "Finance &mdash; known today"],
                ["M", "Material cost of an average lot", "Finance &mdash; known today"],
                ["**loss%**", "**Real material loss per lot**",
                 "**Nobody. Odoo cannot produce it. The parallel run creates it.**"]],
               [18 * mm, 74 * mm, 78 * mm], bold_rows=(4,)),
        Spacer(1, 4),
        para("Then the arithmetic is trivial:"),
        Paragraph("QA review saved &nbsp;= L &times; H &times; 0.40 &times; C &nbsp;&nbsp; "
                  "<i>(0.40 is the LOW end of the published 40&ndash;60% reduction)</i><br/>"
                  "Material loss exposed = L &times; M &times; loss%<br/>"
                  "Annual benefit &nbsp;= QA review saved + material loss + deviations avoided<br/>"
                  "Payback &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= (subscription + implementation) "
                  "&divide; annual benefit", SS["Code"]),
        Spacer(1, 4),
        para("**Published benchmarks for the category** &mdash; to frame the conversation, "
             "never to be quoted as BatchTwin's measured results:"),
        Spacer(1, 3),
        table(["Benchmark", "Figure", "Source"],
              [["Batch release time reduction", "40&ndash;60%", "[SOURCED] Ref [4]"],
               ["QA review effort", "materially reduced via review-by-exception", "[SOURCED] Ref [5]"],
               ["Error reduction, direct capture vs manual entry", "up to 95% (one facility)",
                "[SOURCED] Ref [16]"],
               ["Typical time to ROI", "12&ndash;18 months", "[SOURCED] Ref [12]"]],
              [70 * mm, 44 * mm, 56 * mm]),

        Spacer(1, 6),
        heading("11.4 &nbsp; Why efficiency alone will not justify the purchase", 1),
        para("Run the formula with any plausible inputs for a site of Medicka's size and QA "
             "review time dominates every other term; material loss and expiry are rounding "
             "errors beside it. Benefit scales linearly with lots, and the subscription does "
             "not &mdash; so below a few hundred lots a year the sums are marginal and the "
             "honest recommendation is the smallest plan."),
        para("**The purchase is justified by risk, not efficiency.** A regulatory finding on "
             "batch records is existential for a GMP site: lost certification, halted export, "
             "remediation costs far beyond any subscription. A recall from an undetected fill "
             "drift is the same. A failed customer audit costs the account. BatchTwin's answer "
             "to each is concrete &mdash; the hash chain with external anchoring, Part 11 "
             "signatures, a release gate that cannot be bypassed, and an SPC forecast that "
             "warns before specification is breached."),
        para("This is insurance pricing rather than efficiency pricing, which is exactly why "
             "the buyer is the person who personally signs release, and why the pitch leads "
             "with traceability."),

        Spacer(1, 4),
        kpibox("Chapter 11 &mdash; deployment KPIs", [
            ("Production stoppage required", "none", "MEASURED", "run-mode state machine"),
            ("Parallel-run duration", "4&ndash;8 weeks", "ASSUMPTION", "no customer has run one"),
            ("Run-mode changes permitted to", "QA role only", "MEASURED", "store.set_run_mode()"),
            ("Offline-capable actions", "6 of 7 kinds", "MEASURED", "signatures excluded by design"),
            ("Sensor failure modes modelled", "8", "MEASURED", "resilience.py"),
            ("Staleness / dead thresholds", "120 s / 600 s", "MEASURED", "resilience.py"),
            ("Published release-time reduction", "40&ndash;60%", "SOURCED", "Ref [4] &mdash; category, not ours"),
            ("BatchTwin's own ROI figure", "not stated", "&mdash;", "requires customer inputs"),
        ]),
        Spacer(1, 4),
        srcbox(["[4] iFactory &mdash; eBR release time", "[5] MasterControl &mdash; review by exception",
                "[12] BatchLine", "[13] A3P", "[16] Pharmaceutical Technology &mdash; error reduction"]),
        PageBreak()]
    return s


def ch12():
    risks = [
        ("R1", "Live Odoo integration fails at a customer site", "High", "Medium",
         "Mock and live adapters share a contract test. Read-only by construction limits blast "
         "radius. **Mitigation gap: no production Odoo has been tested.** First action of the "
         "Medicka engagement."),
        ("R2", "Addressable market smaller than assumed", "High", "Medium",
         "Acknowledged openly in Chapter 3. Counting the supplement and cosmetics population "
         "is open question #1 and costs weeks, not money."),
        ("R3", "Customer ramp misses", "High", "Medium",
         "The most sensitive variable in the model (&sect;9.2). Mitigated by low fixed costs "
         "&mdash; founder pay can be reduced again &mdash; and by the integrator channel."),
        ("R4", "Implementation takes far longer than 20 days", "Medium", "Medium",
         "Services margin evaporates and delivery capacity is consumed. Mitigated by the parser "
         "and by templatising the validation pack next."),
        ("R5", "Key-person dependency on three founders", "High", "High",
         "Real and not solvable at this size. Source availability and Enterprise escrow protect "
         "the customer even in the worst case."),
        ("R6", "A competitor builds a `.docx` parser", "Medium", "Low-Medium",
         "Two-year lead at best. The durable moat is accumulated templates, profiles and "
         "deviation case bases &mdash; hence reference customers over margin in year 1."),
        ("R7", "Validation burden exceeds our capability", "High", "Medium",
         "We supply URS/IQ/OQ/PQ and source; the customer's validation team qualifies it. "
         "Templates do not exist yet &mdash; largest product gap."),
        ("R8", "Regulatory change invalidates an approach", "Medium", "Low",
         "Regulatory-change updates are bundled into the subscription, so the customer never "
         "faces a compliance bill. Cost is carried by us."),
        ("R9", "Currency and macroeconomic exposure", "Low", "Medium",
         "Costs and revenue are both TND, so there is a natural hedge. Maghreb expansion in "
         "year 3 introduces exposure."),
        ("R10", "Vision model too weak for label OCR", "Low", "Certain",
         "Already true. Manual entry is the primary path; the UI names the model and the "
         "limitation. Resolved by a larger model, not by new code."),
    ]
    s = [heading("12 &nbsp; Risk register", 0),
         para("Ordered by the product of impact and likelihood. Nothing here is presented as "
              "solved that is not solved."),
         Spacer(1, 3),
         table(["#", "Risk", "Impact", "Likelihood", "Position"],
               [[a, b, c, d, e] for a, b, c, d, e in risks],
               [10 * mm, 42 * mm, 17 * mm, 21 * mm, 80 * mm]),

         Spacer(1, 6),
         heading("12.1 &nbsp; Open questions, in priority order", 1),
         para("These are the things we would answer first, and none of them requires funding "
              "&mdash; only access and time:"),
         Spacer(1, 3),
         table(["#", "Question", "How it gets answered", "Cost"],
               [["1", "How many Tunisian supplement, cosmetics and device manufacturers are "
                 "there in our band?", "Aggregate ANCSEP registrations, ISO 22716 certificate "
                 "lists and trade-association membership.", "2&ndash;3 weeks of desk research"],
                ["2", "What is the real material loss per lot?", "One month of parallel-run "
                 "weighing at Medicka.", "Included in the pilot"],
                ["3", "What will customers actually pay?", "Three customer conversations. "
                 "Replaces the whole of Chapter 6 with evidence.", "Three meetings"],
                ["4", "What are the four ROI inputs at Medicka?", "Ask. All four are known to "
                 "them today (&sect;11.3).", "One meeting"],
                ["5", "What margin will an Odoo integrator accept?", "Approach two.",
                 "Two meetings"],
                ["6", "Does the live Odoo adapter work in production?", "Connect to Medicka's "
                 "instance, read-only.", "One day"],
                ["7", "Do GMP buyers in this segment really prefer on-premise?", "Asserted from "
                 "conservatism, never measured. Ask in the same three conversations.", "Free"]],
               [9 * mm, 52 * mm, 68 * mm, 41 * mm]),

         Spacer(1, 6),
         callout("What we would tell an evaluator who asks \"what does it cost?\"",
                 "We have not set a price yet. Here is the band it has to sit in and why "
                 "&mdash; above their Odoo bill, an order of magnitude below enterprise MES "
                 "&mdash; here is the opening position that band produces, and here are the "
                 "three customer conversations that will replace it with evidence. That answer "
                 "is respectable and it is checkable. A precise-sounding number with no origin "
                 "is neither, and it invites exactly one question there is no good answer to.",
                 "info"),

         Spacer(1, 5),
         kpibox("Chapter 12 &mdash; risk KPIs", [
             ("Risks rated high impact", "5 of 10", "DERIVED", "register above"),
             ("Risks with an unmitigated gap", "R1, R7", "&mdash;", "stated, not hidden"),
             ("Open questions requiring funding", "0 of 7", "DERIVED", "all need access, not money"),
             ("Longest open question", "2&ndash;3 weeks", "ASSUMPTION", "market count"),
             ("Assumptions listed in Appendix D", "20", "MEASURED", "counted from finance_model.py"),
         ]),
         PageBreak()]
    return s


def ch13():
    s = [heading("13 &nbsp; KPI framework", 0),
         para("What we would measure to know whether the plan is working, separated by the "
              "question each set answers. A KPI that nobody would act on is decoration; every "
              "metric below has a stated trigger."),

         heading("13.1 &nbsp; Product KPIs &mdash; is it good?", 1),
         table(["KPI", "Today", "Target", "Acts on it"],
               [["Dossier fields digitalised per customer", "1,205 [MEASURED]", "&gt;1,000",
                 "Delivery &mdash; below this, the parser needs work for that customer"],
                ["Onboarding days per site", "20 [ASSUMPTION]", "&le;20 and falling",
                 "Delivery &mdash; above 30, services margin is gone"],
                ["Automated tests passing", "143 [MEASURED]", "no regressions", "Engineering"],
                ["Batch record generation", "one click [MEASURED]", "unchanged", "Product"],
                ["Deviations closed with an advisor citation", "n/a", "&gt;50%",
                 "Product &mdash; measures whether adaptive intelligence is used, not just built"]],
               [56 * mm, 30 * mm, 30 * mm, 54 * mm]),

         Spacer(1, 5),
         heading("13.2 &nbsp; Customer KPIs &mdash; does it work in the plant?", 1),
         table(["KPI", "How it is measured", "Trigger"],
               [["Material loss per lot", "mass balance vs BOM, every lot",
                 "**The number that does not exist today.** First real value is a milestone."],
                ["Batch release cycle time", "signature timestamps, paper vs digital",
                 "Below the 40% published low end, investigate the workflow"],
                ["QA review hours per lot", "customer-reported, before and after",
                 "The dominant ROI term (&sect;11.4)"],
                ["Deviation recurrence rate", "advisor case base",
                 "Rising recurrence means CAPAs are not holding"],
                ["SPC warnings before specification breach", "forecast vs actual",
                 "A warning that arrives after the breach is worthless"],
                ["Parallel-run divergences", "digital vs paper, per lot",
                 "Must trend to zero before cutover"]],
               [48 * mm, 54 * mm, 68 * mm]),

         Spacer(1, 5),
         heading("13.3 &nbsp; Commercial KPIs &mdash; is it a business?", 1),
         table(["KPI", "Year 1", "Year 2", "Year 3", "Why it matters"],
               [["Active sites", str(M[1]["active_sites"]), str(M[2]["active_sites"]),
                 str(M[3]["active_sites"]), "the most sensitive variable in the model"],
                ["Exit ARR", money(M[1]["arr_exit_tnd"]), money(M[2]["arr_exit_tnd"]),
                 money(M[3]["arr_exit_tnd"]), "the real measure, not total revenue"],
                ["Recurring revenue share",
                 f"{M[1]['licence_tnd'] / M[1]['revenue_tnd'] * 100:.0f}%",
                 f"{M[2]['licence_tnd'] / M[2]['revenue_tnd'] * 100:.0f}%",
                 f"{M[3]['licence_tnd'] / M[3]['revenue_tnd'] * 100:.0f}%",
                 "software company vs consultancy"],
                ["ARPA", money(M[1]["arpa_tnd"]), money(M[2]["arpa_tnd"]), money(M[3]["arpa_tnd"]),
                 "plan-mix health"],
                ["Net margin", f"{M[1]['margin_pct']}%", f"{M[2]['margin_pct']}%",
                 f"{M[3]['margin_pct']}%", "flattered by founder pay until Y3"],
                ["Sites vs break-even",
                 f"{M[1]['active_sites']} / {BE['sites_for_breakeven_on_licence_alone']}",
                 f"{M[2]['active_sites']} / {BE['sites_for_breakeven_on_licence_alone']}",
                 f"{M[3]['active_sites']} / {BE['sites_for_breakeven_on_licence_alone']}",
                 "when the product business actually works"]],
               [36 * mm, 26 * mm, 26 * mm, 26 * mm, 56 * mm], align_right=(1, 2, 3)),

         Spacer(1, 5),
         heading("13.4 &nbsp; The three leading indicators", 1),
         para("Revenue is a lagging indicator on a 6&ndash;12 month sales cycle &mdash; by the "
              "time it moves, the decision that caused it was made two quarters ago. These "
              "three move first:"),
         ] + bullets([
        "**Did the second customer close without a founder in the room?** Until this "
        "happens the go-to-market is unproven regardless of revenue.",
        "**Is onboarding time falling per customer?** Flat onboarding time means we are a "
        "consultancy. Falling onboarding time means the product is absorbing the work.",
        "**Did a customer's QA Director recommend us to a peer unprompted?** In a market "
        "this small and this conservative, peer reference is the only marketing channel that "
        "compounds.",
    ]) + [
        Spacer(1, 5),
        kpibox("Chapter 13 &mdash; framework summary", [
            ("Product KPIs defined", "5", "MEASURED", "&sect;13.1"),
            ("Customer KPIs defined", "6", "MEASURED", "&sect;13.2"),
            ("Commercial KPIs defined", "6", "MEASURED", "&sect;13.3"),
            ("Leading indicators", "3", "MEASURED", "&sect;13.4"),
            ("KPIs measurable today", "product set only", "&mdash;", "customer set needs a live site"),
        ]),
        PageBreak()]
    return s


def ch14():
    y3 = M[3]
    s = [heading("14 &nbsp; Roadmap and conclusion", 0),

         heading("14.1 &nbsp; Roadmap", 1),
         table(["Horizon", "Objective", "Why this order"],
               [["Next 3 months", "Medicka pilot: live Odoo connection, parallel run, first "
                 "real material-loss measurement.", "Closes R1 and open questions 2, 4 and 6 "
                 "at once. Nothing else should start first."],
                ["3&ndash;6 months", "Validation pack templated (URS/IQ/OQ/PQ). Market count "
                 "completed. Three pricing conversations.", "R7 is the largest product gap; "
                 "open questions 1 and 3 are the largest commercial gaps."],
                ["6&ndash;12 months", "Two paying customers beyond Medicka. First integrator "
                 "partnership. Case study published.", "Proves the sale is repeatable without "
                 "a founder in the room."],
                ["Year 2", "Odoo integrator channel producing pipeline. Multi-site hybrid "
                 "dashboard for Enterprise.", "The only route that scales sales without "
                 "founder time."],
                ["Year 3", "First Maghreb sites. Vertical profiles beyond pharma proven in "
                 "production.", "Geography and vertical expansion, once the motion is proven "
                 "at home."]],
               [30 * mm, 68 * mm, 72 * mm]),

         Spacer(1, 6),
         heading("14.2 &nbsp; What would change our mind", 1),
         para("A plan that cannot be falsified is not a plan. Specific signals that would "
              "cause us to change course rather than push harder:"),
         ] + bullets([
        "**The market count comes back small.** If the Tunisian addressable population is "
        "genuinely under about 40 sites, the domestic-only plan does not support a company "
        "and Maghreb expansion moves from year 3 to year 1.",
        "**Three QA Directors say they will not buy on-premise.** The deployment assumption "
        "is asserted from conservatism, not measured. If it is wrong, the whole cost "
        "structure changes and the margin advantage in Chapter 7 disappears.",
        "**Onboarding takes 40+ days at the second customer.** That would mean the parser "
        "generalises worse than measured on Medicka's four dossiers, which is the central "
        "product bet.",
        "**Odoo ships a compliant eBR module.** Unlikely &mdash; it is not their market "
        "&mdash; but it would remove the wedge entirely, and the response would be to become "
        "the validation and services partner for it rather than to compete.",
    ]) + [
        Spacer(1, 6),
        heading("14.3 &nbsp; Conclusion", 1),
        para(f"BatchTwin addresses a problem that is documented rather than assumed: batch "
             f"records are the leading source of GMP findings [SOURCED], and the affordable "
             f"tooling to fix them does not exist for a 100-person manufacturer. The product "
             f"is built and measurable &mdash; 1,205 fields from a customer's own documents, "
             f"143 passing tests, 84 API routes [MEASURED]. The commercial model is derived "
             f"from public anchors rather than invented, and reaches "
             f"{money(y3['revenue_tnd'])} of revenue and {money(y3['arr_exit_tnd'])} of "
             f"recurring ARR by year 3 [DERIVED] on a customer ramp we have labelled, "
             f"repeatedly, as the least evidenced part of the plan."),
        para("What we are not claiming is as important as what we are. We have not connected "
             "to a production Odoo. We have not measured real material loss. We have not "
             "tested a price with a customer, approached an integrator, or counted our own "
             "addressable market. Every one of those appears in the risk register with the "
             "action that closes it, and none of them requires funding &mdash; only access "
             "and a pilot."),
        Spacer(1, 4),
        callout("The sentence this plan rests on",
                "Odoo tells a manufacturer what **should** have happened. BatchTwin captures "
                "what **actually** happened &mdash; and the gap between the two is where cost, "
                "quality, compliance and carbon all hide. Closing that gap is worth more to a "
                "GMP site than any efficiency saving, because the gap is what an inspector "
                "asks about.", "info"),
        PageBreak()]
    return s


# ================================================================= APPENDICES
def appendices():
    s = [heading("Appendix A &nbsp; KPI catalogue", 0),
         para("Every KPI referenced in this document, consolidated. The evidence column is the "
              "point: a reader can check any row."),
         Spacer(1, 3)]

    rows = [
        ("Dossier fields digitalised", "1,205", "MEASURED", "Ch.1, 2, 4, 5"),
        ("Conformity checks made tappable", "135", "MEASURED", "Ch.2, 4"),
        ("Blank paper rows eliminated", "570", "MEASURED", "Ch.2, 4"),
        ("Repeatable blocks", "27", "MEASURED", "Ch.4"),
        ("Dossier templates &rarr; adaptive form", "4 &rarr; 1", "MEASURED", "Ch.4"),
        ("API routes", "84", "MEASURED", "Ch.4"),
        ("Backend source lines", "6,609", "MEASURED", "Ch.4"),
        ("Automated tests passing", "143 (8 skipped)", "MEASURED", "Ch.1, 4, 13"),
        ("Industry profiles", "4", "MEASURED", "Ch.4"),
        ("Sensor failure modes modelled", "8", "MEASURED", "Ch.11"),
        ("Staleness / dead thresholds", "120 s / 600 s", "MEASURED", "Ch.11"),
        ("Odoo write operations", "0", "MEASURED", "Ch.5, 10"),
        ("ML in release-critical path", "0", "MEASURED", "Ch.5"),
        ("Material cost per demo lot", money(UE["bom_tnd"]), "MEASURED", "Ch.2, 4"),
        ("Material cost per unit", f"{UE['cost_per_unit_tnd']:.4f} TND", "MEASURED", "Ch.4"),
        ("FDA inspections citing batch records", "42%", "SOURCED", "Ch.1, 2"),
        ("FY2025 FDA drug warning letters", "303 (+59%)", "SOURCED", "Ch.2"),
        ("FY2025 letters citing data integrity", "15%", "SOURCED", "Ch.2"),
        ("Batch release time reduction (category)", "40&ndash;60%", "SOURCED", "Ch.11"),
        ("Error reduction, direct capture", "up to 95%", "SOURCED", "Ch.11"),
        ("Typical eBR time to ROI", "12&ndash;18 months", "SOURCED", "Ch.11"),
        ("Tunisia pharma manufacturing sites", "55", "SOURCED", "Ch.3"),
        ("Algeria pharma manufacturing plants", "218", "SOURCED", "Ch.3"),
        ("Tunisia pharma market 2025", "USD 2.74 bn", "SOURCED", "Ch.3"),
        ("Tunisia pharma CAGR to 2032", "12.9%", "SOURCED", "Ch.3"),
        ("EUR/TND rate used", f"{FM.EUR_TND}", "SOURCED", "front matter"),
        ("Tunis engineer salary band", "3,500&ndash;7,000+ TND/mo", "SOURCED", "Ch.6, 7"),
        ("Services day rate", money(FM.DAY_RATE_TND), "DERIVED", "Ch.6"),
        ("First-year services total", money(FM.services_total()), "DERIVED", "Ch.6, 7"),
        ("Essential plan", money(FM.PLANS["Essential"]["annual_tnd"]), "DERIVED", "Ch.6"),
        ("Standard plan", money(FM.PLANS["Standard"]["annual_tnd"]), "DERIVED", "Ch.6"),
        ("Enterprise plan", money(FM.PLANS["Enterprise"]["annual_tnd"]) + " + group", "DERIVED", "Ch.6"),
        ("First-year contract value", money(MK["avg_first_year_contract_tnd"]), "DERIVED", "Ch.7"),
        ("Year-1 revenue", money(M[1]["revenue_tnd"]), "DERIVED", "Ch.1, 8"),
        ("Year-2 revenue", money(M[2]["revenue_tnd"]), "DERIVED", "Ch.8"),
        ("Year-3 revenue", money(M[3]["revenue_tnd"]), "DERIVED", "Ch.1, 8"),
        ("Year-3 exit ARR", money(M[3]["arr_exit_tnd"]), "DERIVED", "Ch.8, 13"),
        ("Year-3 net margin", f"{M[3]['margin_pct']}%", "DERIVED", "Ch.8"),
        ("Cumulative 3-year cash", money(M[3]["cumulative_cash_tnd"]), "DERIVED", "Ch.8"),
        ("Break-even sites, licence only", f"{BE['sites_for_breakeven_on_licence_alone']}",
         "DERIVED", "Ch.1, 9, 13"),
        ("TAM Maghreb floor", f"{MK['tam_maghreb_pharma_floor_sites']} sites", "SOURCED", "Ch.3"),
        ("SAM Tunisia pharma", f"{MK['sam_tunisia_pharma_sites']} sites", "ASSUMPTION", "Ch.3"),
        ("SAM annual value", money(MK["sam_tunisia_value_tnd"]), "DERIVED", "Ch.3"),
        ("Real material loss", "**unknown**", "&mdash;", "Ch.2, 11 &mdash; the missing number"),
        ("BatchTwin ROI figure", "**not stated**", "&mdash;", "Ch.11 &mdash; needs customer inputs"),
        ("Supplement/cosmetics site count", "**unknown**", "&mdash;", "Ch.3 &mdash; open question #1"),
        ("Prices validated with customers", "0", "&mdash;", "Ch.6, 12"),
        ("Integrators approached", "0", "&mdash;", "Ch.10, 12"),
    ]
    s += [table(["KPI", "Value", "Evidence", "Where in this document"],
                [[a, b, f"[{c}]" if c != "&mdash;" else c, d] for a, b, c, d in rows],
                [58 * mm, 34 * mm, 24 * mm, 54 * mm], align_right=(1,)),
          PageBreak()]

    # ---------------------------------------------------- Appendix B
    s += [heading("Appendix B &nbsp; Reproducing every measured claim", 0),
          para("Each command below is run from the repository root and reproduces the "
               "corresponding figure. This appendix exists so that no measured number in this "
               "document has to be taken on trust."),
          Spacer(1, 3),
          table(["Claim", "Command or location"],
                [["1,205 fields / 135 checks / 570 rows / 27 blocks",
                  "`python -c \"from backend import docx_forms; "
                  "print(sum(f['field_count'] for f in docx_forms.load_all('dossier')))\"`"],
                 ["143 tests passing, 8 skipped", "`python -m pytest -q`"],
                 ["84 API routes", "`grep -cE '^@app\\.(get|post|put|delete)' backend/main.py`"],
                 ["6,609 backend source lines", "`find backend -name '*.py' | xargs wc -l`"],
                 ["Material cost per lot and per unit",
                  "`backend/analytics.py::mass_balance()` over the seeded demo lot"],
                 ["Read-only Odoo integration", "`backend/odoo_adapter.py`; "
                  "`tests/test_odoo_contract.py`"],
                 ["No ML in release-critical path",
                  "`tests/test_compliance.py::AssistantReadOnlyTests`"],
                 ["SPC control limits validated",
                  "`tests/test_compliance.py::SPCValidationTests`"],
                 ["8 sensor failure modes, 120 s / 600 s thresholds", "`backend/resilience.py`"],
                 ["Run-mode state machine, QA-only", "`backend/store.py::set_run_mode()`"],
                 ["Advisor case base and ranking", "`backend/advisor.py`; `tests/test_advisor.py`"],
                 ["Every financial figure in this document", "`python docs/finance_model.py`"]],
                [62 * mm, 108 * mm]),
          Spacer(1, 6)]

    # ---------------------------------------------------- Appendix C
    bom = [("Eau purifi&eacute;e", "120.000", "kg", "0.05", "6.00"),
           ("Sirop de sorbitol 70%", "40.000", "kg", "1.10", "44.00"),
           ("Citrate de magn&eacute;sium", "4.800", "kg", "12.00", "57.60"),
           ("Chlorhydrate de pyridoxine (Vit. B6)", "0.032", "kg", "180.00", "5.76"),
           ("Sorbate de potassium (conservateur)", "0.330", "kg", "6.50", "2.15"),
           ("Acide citrique (correcteur pH)", "0.660", "kg", "1.80", "1.19"),
           ("Ar&ocirc;me orange", "1.600", "kg", "22.00", "35.20"),
           ("Flacon PET 200 mL + bouchon", "800", "unit", "0.14", "112.00"),
           ("Gobelet doseur", "800", "unit", "0.03", "24.00"),
           ("&Eacute;tiquette + notice", "800", "unit", "0.05", "40.00"),
           ("&Eacute;tui carton", "800", "unit", "0.09", "72.00")]
    s += [heading("Appendix C &nbsp; Bill of materials, demonstration lot", 0),
          para(f"Medicka's real formula &mdash; magnesium citrate and vitamin B6 oral syrup, "
               f"200 mL, {UE['units']}-unit lot. Costs are in EUR as held in the source data; "
               f"the TND total is converted at {FM.EUR_TND}."),
          Spacer(1, 3),
          table(["Material", "Target", "Unit", "Unit cost (EUR)", "Line cost (EUR)"],
                [[a, b, c, d, e] for a, b, c, d, e in bom]
                + [["**Total**", "", "", "", f"**{UE['bom_eur']:,.2f}**"],
                   ["**Total (TND)**", "", "", "", f"**{UE['bom_tnd']:,.2f}**"],
                   ["**Per unit (TND)**", "", "", "", f"**{UE['cost_per_unit_tnd']:.4f}**"]],
                [66 * mm, 22 * mm, 16 * mm, 32 * mm, 34 * mm], align_right=(1, 3, 4),
                bold_rows=(len(bom), len(bom) + 1, len(bom) + 2)),
          Spacer(1, 5),
          para("This is the theoretical cost &mdash; what Odoo believes was consumed. What was "
               "*actually* consumed is unknown at every site in this segment today, and "
               "producing that number for the first time is the core of the value proposition "
               "(Chapters 2 and 11)."),
          PageBreak()]

    # ---------------------------------------------------- Appendix D
    assumptions = [
        ("Pricing", "Essential / Standard / Enterprise plan prices", "Ch.6", "3 customer conversations"),
        ("Pricing", f"{FM.BILL_MULTIPLIER:.0f}&times; services multiplier over loaded cost", "Ch.6",
         "Benchmark against a local Odoo integrator day rate"),
        ("Pricing", "20 / 16 / 11 days per service engagement", "Ch.6", "First real implementation"),
        ("Pricing", f"{FM.REFERENCE_DISCOUNT:.0%} reference-customer discount", "Ch.10",
         "Negotiation with Medicka"),
        ("Cost", f"Founder pay {money(FM.FOUNDER_MONTHLY_TND[1])} &rarr; "
         f"{money(FM.FOUNDER_MONTHLY_TND[3])} per month", "Ch.7", "Founder agreement"),
        ("Cost", f"Headcount {FM.HEADCOUNT[1]} &rarr; {FM.HEADCOUNT[3]}", "Ch.7", "Delivery load"),
        ("Cost", "Operating cost lines, all three years", "Ch.7", "Actual spend"),
        ("Ramp", f"New customers {FM.RAMP[1]['new']} / {FM.RAMP[2]['new']} / {FM.RAMP[3]['new']}",
         "Ch.8", "**The most sensitive assumption in the plan** (&sect;9.2)"),
        ("Ramp", f"Churn {FM.RAMP[1]['churn']} / {FM.RAMP[2]['churn']} / {FM.RAMP[3]['churn']}",
         "Ch.8", "No customer has ever churned; no evidence either way"),
        ("Ramp", "Geography split, Tunisia vs Maghreb", "Ch.8", "Maghreb entry not attempted"),
        ("Ramp", "Plan mix per year", "Ch.8", "Observed customer sizes"),
        ("Market", f"{FM.ADDRESSABLE_SHARE:.0%} of Tunisian pharma sites are in our band",
         "Ch.3", "Open question #1"),
        ("Market", "Supplement / cosmetics population is material", "Ch.3",
         "**Unquantified. Open question #1**"),
        ("Market", "Morocco excluded from TAM", "Ch.3", "Conservative by choice"),
        ("Product", "Onboarding stays near 20 days at other customers", "Ch.13",
         "Second implementation"),
        ("Product", "Parallel run of 4&ndash;8 weeks is sufficient", "Ch.11", "Medicka pilot"),
        ("Product", "Live Odoo adapter works in production", "Ch.4, 12", "Risk R1 &mdash; one day of work"),
        ("Deployment", "GMP buyers prefer on-premise", "Ch.5, 6", "Open question #7 &mdash; asserted, never measured"),
        ("Commercial", "Integrator channel will accept a margin split", "Ch.10", "Open question #5"),
        ("Commercial", "Regulatory-change updates can be absorbed in the subscription", "Ch.6",
         "Cost of first regulatory change"),
    ]
    s += [heading("Appendix D &nbsp; Assumption register", 0),
          para("Every [ASSUMPTION] in this document, collected so a reader can attack them as a "
               "group rather than hunting them chapter by chapter. This is the list we would "
               "hand to someone whose job was to find the weakest point in the plan."),
          Spacer(1, 3),
          table(["Area", "Assumption", "Where", "What would validate it"],
                [[a, b, c, d] for a, b, c, d in assumptions],
                [22 * mm, 62 * mm, 18 * mm, 68 * mm]),
          Spacer(1, 5),
          callout("The three that matter most",
                  "**Customer ramp** (&sect;9.2 shows halving it produces a loss), **the size "
                  "of the addressable market** (&sect;3.3 shows we cannot state our own share), "
                  "and **willingness to pay** (no price has been tested with anyone). If only "
                  "three things could be validated before this plan is trusted, those are the "
                  "three &mdash; and none of them costs money to answer.", "warn"),
          PageBreak()]
    return s


def references():
    refs = [
        ("[1]", "Capterra &mdash; MasterControl pricing and reviews. "
         "https://www.capterra.com/p/148011/MasterControl/"),
        ("[2]", "OEC.sh &mdash; Odoo Enterprise pricing by country. https://oec.sh/odoo-pricing"),
        ("[3]", "Odoo &mdash; official pricing. https://www.odoo.com/pricing"),
        ("[4]", "iFactory &mdash; Pharma eBR and batch-record automation: 40&ndash;60% release "
         "time reduction. https://ifactoryapp.com/blog/pharma-ebr-batch-record-automation"),
        ("[5]", "MasterControl GxP Lifeline &mdash; Benefits of electronic batch records for "
         "batch record review. https://www.mastercontrol.com/gxp-lifeline/"
         "benefits-electronic-batch-records-for-batch-record-review/"),
        ("[6]", "GMP Pros &mdash; Challenges transitioning from paper to electronic batch "
         "records; batch-record deficiencies in 42% of inspections, 2020&ndash;2023. "
         "https://gmppros.com/challenges-transitioning-from-paper-to-electronic-batch-records/"),
        ("[7]", "Pharmaceutical Online &mdash; What 2025 FDA warning letters tell us about GMP "
         "compliance. https://www.pharmaceuticalonline.com/doc/"
         "what-fda-warning-letters-tell-us-about-gmp-compliance-0001"),
        ("[8]", "QBench &mdash; Inside 470 FDA warning letters from 2025. "
         "https://qbench.com/resources/inside-470-fda-warning-letters-from-2025-what-labs-need-to-know"),
        ("[9]", "Maghreb Pharma &mdash; Pharmaceuticals sector: with 218 plants, Algeria "
         "reinforces its position as African leader, 2025-05-21. "
         "https://www.maghrebpharma.com/en/2025/05/21/"
         "pharmaceuticals-sector-with-218-plants-algeria-reinforces-its-position-as-african-leader/"),
        ("[10]", "African Manager &mdash; Tunisia ranked 9th most competitive pharmaceutical "
         "market in Africa in 2025. https://en.africanmanager.com/"
         "tunisia-ranked-9th-most-competitive-pharmaceutical-market-in-africa-in-2025/"),
        ("[11]", "Maximize Market Research &mdash; Tunisia Pharmaceutical Market, global "
         "industry analysis and forecast 2025&ndash;2032. "
         "https://www.maximizemarketresearch.com/market-report/tunisia-pharmaceutical-market/119566/"),
        ("[12]", "BatchLine &mdash; Electronic Batch Record (eBR) implementation guide 2026. "
         "https://batchline.com/electronic-batch-record-ebr-implementation-guide/"),
        ("[13]", "A3P &mdash; eBR (Electronic Batch Record): opportunities and pitfalls to be "
         "avoided. https://www.a3p.org/en/electronic-batch-record/"),
        ("[14]", "Vimachem &mdash; How electronic batch records in MES improve manufacturing. "
         "https://www.vimachem.com/resources/articles/"
         "how-electronic-batch-records-in-mes-improve-manufacturing/"),
        ("[15]", "Glassdoor, levels.fyi and worldsalaries &mdash; software engineer salary, "
         "Tunisia / Tunis, 2025&ndash;2026. https://www.glassdoor.com/Salaries/"
         "tunisia-software-engineer-salary-SRCH_IL.0,7_IN236_KO8,25.htm"),
        ("[16]", "Pharmaceutical Technology &mdash; Electronic batch records offer advantages "
         "beyond automation. https://www.pharmtech.com/view/"
         "electronic-batch-records-offer-advantages-beyond-automation"),
        ("[17]", "*Further reading, not cited for a specific figure.* EY &mdash; Electronic "
         "batch records improve pharma manufacturing. "
         "https://www.ey.com/en_us/insights/life-sciences/"
         "electronic-batch-records-improve-pharma-manufacturing"),
        ("[18]", "*Further reading, not cited for a specific figure.* IntuitionLabs &mdash; "
         "Pharma MES &amp; eBR software landscape for GMP "
         "manufacturing. https://intuitionlabs.ai/articles/"
         "pharma-mes-ebr-software-gmp-manufacturing"),
        ("[19]", "Banque Centrale de Tunisie EUR/TND mid-rate, 2026-07-10, via "
         "exchange-rates.org. https://www.exchange-rates.org/exchange-rate-history/eur-tnd-2026"),
        ("[20]", "US FDA &mdash; 21 CFR Part 11, Electronic Records; Electronic Signatures. "
         "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/"
         "part-11-electronic-records-electronic-signatures-scope-and-application"),
    ]
    s = [heading("References", 0),
         para("Every [SOURCED] figure in this document traces to an entry below. Accessed "
              "July 2026."),
         Spacer(1, 4)]
    s += [table(["", "Reference"], [[a, b] for a, b in refs], [12 * mm, 158 * mm])]
    s += [Spacer(1, 8),
          callout("A closing note on method",
                  "This document contains a number of places where the honest answer was "
                  "\"we do not know\": the real material loss, the size of our own addressable "
                  "market, what a customer will pay, whether the live Odoo adapter works in "
                  "production. Each is stated as a gap with the action that closes it, rather "
                  "than filled with a plausible figure. That choice makes the plan look less "
                  "complete and makes it considerably more useful &mdash; every remaining "
                  "number in it can be checked, and the ones that cannot be checked are "
                  "labelled.", "info")]
    return s
