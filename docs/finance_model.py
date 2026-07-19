"""
BatchTwin financial model -- the single source of truth for every number in
BUSINESS_PLAN.pdf.

Rule inherited from BUSINESS_MODEL.md: nothing is typed twice and nothing is
invented. Each input below is tagged with where it comes from:

    SOURCED     published third-party figure, cited in REFERENCES
    MEASURED    computed by code in this repository against Medicka's real files
    DERIVED     arithmetic on SOURCED/MEASURED inputs, shown in full
    ASSUMPTION  our estimate -- must be validated before it is quoted

Currency is TND. The plan is sold in Tunisia, the cost base is Tunisian, and
quoting a Tunisian QA Director in euro invites a conversation about the euro
rather than about the product.

    python docs/finance_model.py
"""
from __future__ import annotations

# --------------------------------------------------------------- constants
# [SOURCED] Banque Centrale de Tunisie mid-rate, 2026-07-10, via exchange-rates.org
EUR_TND = 3.37

# [MEASURED] backend/analytics.mass_balance() over Medicka's real BOM,
# lot PF201-260718-001, 800 units of magnesium + B6 oral syrup 200 mL.
BOM_EUR = 399.89
BOM_UNITS = 800

# [SOURCED] Software engineer, Tunis: 3,500-7,000+ TND/month (Glassdoor /
# levels.fyi / worldsalaries composite). We take the middle for a loaded
# senior cost and state it as the midpoint, not a precise figure.
ENG_MONTHLY_TND = 5_000
WORKING_DAYS_PER_MONTH = 21
BILL_MULTIPLIER = 3.0        # [ASSUMPTION] standard services markup over loaded cost


def eur(t: float) -> float:
    return round(t / EUR_TND, 2)


def tnd(e: float) -> float:
    return round(e * EUR_TND, 2)


# ------------------------------------------------------------- unit economics
def unit_economics() -> dict:
    """What one lot actually costs, in TND, from the real formula."""
    bom_tnd = tnd(BOM_EUR)
    return {
        "bom_eur": BOM_EUR,
        "bom_tnd": round(bom_tnd, 2),
        "units": BOM_UNITS,
        "cost_per_unit_tnd": round(bom_tnd / BOM_UNITS, 4),
        "cost_per_unit_eur": round(BOM_EUR / BOM_UNITS, 4),
    }


# ------------------------------------------------------------------- pricing
# [DERIVED] see Chapter 6. Round TND figures, not converted euro figures --
# a price list that reads 20,220 TND announces that it was written in euro.
PLANS = {
    "Essential":  {"annual_tnd": 20_000, "scope": "1 ligne de production, 5 produits"},
    "Standard":   {"annual_tnd": 40_000, "scope": "1 site, lignes illimitees, SPC + VERA + deviations"},
    "Enterprise": {"annual_tnd": 30_000, "scope": "par site, + 50 000 TND groupe",
                   "group_fee_tnd": 50_000},
}

# [DERIVED] day rate = loaded monthly cost / working days, times services markup
DAY_RATE_TND = round(ENG_MONTHLY_TND / WORKING_DAYS_PER_MONTH * BILL_MULTIPLIER)

SERVICES = {
    # name: (days, note)
    "Implementation & dossier onboarding": (20, "parse + validate the customer's own .docx templates"),
    "Validation pack (URS/IQ/OQ/PQ)":      (16, "documents the customer shows the inspector"),
    "Parallel-run support & training":     (11, "8 weeks part-time, both systems live"),
}


def services_table() -> list[dict]:
    out = []
    for name, (days, note) in SERVICES.items():
        out.append({"name": name, "days": days, "note": note,
                    "price_tnd": days * DAY_RATE_TND})
    return out


def services_total() -> int:
    return sum(r["price_tnd"] for r in services_table())


# ------------------------------------------------------------------ cost base
# [ASSUMPTION] Founders take below-market pay in year 1 and step up as revenue
# allows. Three founders: Oussama Labidi, Salem Amara, Ahmed Hammami.
FOUNDER_MONTHLY_TND = {1: 2_500, 2: 4_000, 3: 5_500}
HEADCOUNT = {1: 3, 2: 4, 3: 6}          # [ASSUMPTION] +1 support Y2, +2 delivery Y3

# [ASSUMPTION] Non-payroll operating cost. On-premise deployment means no
# per-customer cloud bill -- the largest cost line a SaaS would carry is absent
# by construction, which is a real structural advantage and is argued in Ch.7.
OPEX_TND = {
    1: {"Infrastructure & tooling": 6_000, "Legal, accounting, company": 8_000,
        "Travel & GMP events": 9_000, "Marketing & collateral": 4_000},
    2: {"Infrastructure & tooling": 9_000, "Legal, accounting, company": 10_000,
        "Travel & GMP events": 18_000, "Marketing & collateral": 12_000},
    3: {"Infrastructure & tooling": 14_000, "Legal, accounting, company": 14_000,
        "Travel & GMP events": 30_000, "Marketing & collateral": 25_000},
}


# ------------------------------------------------------------ customer ramp
# [ASSUMPTION] Sales cycle in regulated manufacturing is 6-12 months and needs
# QA sign-off (BUSINESS_MODEL.md s6). The ramp below is deliberately slow;
# a plan that assumes fast bottom-up adoption in GMP is wrong.
RAMP = {
    1: {"new": 3,  "churn": 0, "tn": 3, "mg": 0,
        "note": "Medicka (reference, 50% year-1 discount) + 2 paying, all Tunisia"},
    2: {"new": 5,  "churn": 1, "tn": 5, "mg": 0,
        "note": "Odoo integrator channel opens, still Tunisia only"},
    3: {"new": 10, "churn": 2, "tn": 4, "mg": 6,
        "note": "First Maghreb sites and first multi-site group"},
}

# [ASSUMPTION] Mix shifts toward Standard as the reference case matures.
# Each year's mix must sum to that year's active sites -- asserted below.
MIX = {
    1: {"Essential": 2, "Standard": 1, "Enterprise": 0},
    2: {"Essential": 3, "Standard": 4, "Enterprise": 0},
    3: {"Essential": 4, "Standard": 9, "Enterprise": 2},
}

REFERENCE_DISCOUNT = 0.50   # [ASSUMPTION] Medicka year 1, in exchange for a case study


def build_model() -> dict:
    years = {}
    active_prev = 0
    cash = 0
    for y in (1, 2, 3):
        ramp = RAMP[y]
        active = active_prev + ramp["new"] - ramp["churn"]

        # --- recurring licence revenue, from the mix
        mix = MIX[y]
        # A plan whose plan mix disagrees with its own customer count is a plan
        # nobody should read past. Fail loudly rather than publish the mismatch.
        assert sum(mix.values()) == active, (
            f"year {y}: mix sums to {sum(mix.values())} but {active} sites are active")
        assert ramp["tn"] + ramp["mg"] == ramp["new"], (
            f"year {y}: geography split does not sum to new customers")
        licence = sum(PLANS[p]["annual_tnd"] * n for p, n in mix.items())
        if y == 3:
            licence += PLANS["Enterprise"]["group_fee_tnd"]      # one group fee
        if y == 1:
            licence -= PLANS["Essential"]["annual_tnd"] * REFERENCE_DISCOUNT

        # --- one-off services, charged to NEW customers only
        svc = services_total() * ramp["new"]

        revenue = licence + svc

        # --- costs
        payroll = FOUNDER_MONTHLY_TND[y] * HEADCOUNT[y] * 12
        opex = sum(OPEX_TND[y].values())
        cost = payroll + opex

        profit = revenue - cost
        cash += profit

        years[y] = {
            "active_sites": active, "new": ramp["new"], "churn": ramp["churn"],
            "note": ramp["note"], "mix": mix,
            "licence_tnd": round(licence), "services_tnd": round(svc),
            "revenue_tnd": round(revenue),
            "payroll_tnd": payroll, "opex_tnd": opex, "cost_tnd": round(cost),
            "profit_tnd": round(profit), "margin_pct": round(profit / revenue * 100, 1) if revenue else None,
            "cumulative_cash_tnd": round(cash),
            "arr_exit_tnd": round(licence),
            "arpa_tnd": round(licence / active) if active else None,
        }
        active_prev = active
    return years


def breakeven(years: dict) -> dict:
    """The number that matters: how many sites pay for the company."""
    y2 = years[2]
    monthly_cost = y2["cost_tnd"] / 12
    # average licence per site in the year-2 mix
    mix = MIX[2]
    n = sum(mix.values())
    avg_licence = sum(PLANS[p]["annual_tnd"] * c for p, c in mix.items()) / n
    sites_needed = monthly_cost * 12 / avg_licence
    return {
        "annual_cost_tnd": round(y2["cost_tnd"]),
        "avg_licence_tnd": round(avg_licence),
        "sites_for_breakeven_on_licence_alone": round(sites_needed, 1),
        "note": "Licence revenue only. Services accelerate it but do not recur, "
                "so a plan that breaks even on services is not a product company.",
    }


def sensitivity(years: dict) -> list[dict]:
    """What breaks the plan. Each row varies one driver and holds the rest."""
    base = years[3]["revenue_tnd"]
    out = []
    for label, factor in [("Price 25% lower", 0.75), ("Base case", 1.0),
                          ("Price 25% higher", 1.25)]:
        lic = sum(PLANS[p]["annual_tnd"] * factor * n for p, n in MIX[3].items())
        lic += PLANS["Enterprise"]["group_fee_tnd"] * factor
        rev = lic + services_total() * RAMP[3]["new"]
        cost = FOUNDER_MONTHLY_TND[3] * HEADCOUNT[3] * 12 + sum(OPEX_TND[3].values())
        out.append({"scenario": label, "y3_revenue_tnd": round(rev),
                    "y3_profit_tnd": round(rev - cost),
                    "delta_vs_base_pct": round((rev - base) / base * 100, 1)})
    for label, adj in [("Half the customers", -0.5), ("Double the customers", 1.0)]:
        scale = 1 + adj
        lic = sum(PLANS[p]["annual_tnd"] * round(n * scale) for p, n in MIX[3].items())
        rev = lic + services_total() * round(RAMP[3]["new"] * scale)
        cost = FOUNDER_MONTHLY_TND[3] * HEADCOUNT[3] * 12 + sum(OPEX_TND[3].values())
        out.append({"scenario": label, "y3_revenue_tnd": round(rev),
                    "y3_profit_tnd": round(rev - cost),
                    "delta_vs_base_pct": round((rev - base) / base * 100, 1)})
    return out


# [SOURCED] Licensed pharmaceutical manufacturing sites.
PHARMA_SITES = {"Tunisia": 55, "Algeria": 218}      # Morocco: no figure published
# [ASSUMPTION] Share of those sites inside our band: 50-300 staff, running an
# ERP, still keeping batch records on paper. Never measured -- see Chapter 4.
ADDRESSABLE_SHARE = 0.55


def market(years: dict) -> dict:
    """TAM / SAM / SOM -- and the denominator we cannot honestly state.

    This is the weakest section of the plan and it is written to be read that
    way. The pharma-only denominator is the one we can source; it is also the
    wrong one, because our design partner is a supplement maker and would not
    appear in it.
    """
    tn = PHARMA_SITES["Tunisia"]
    maghreb_floor = sum(PHARMA_SITES.values())          # Morocco not counted
    sam_tn = round(tn * ADDRESSABLE_SHARE)

    y3 = years[3]
    sites_y3 = y3["active_sites"]
    tn_sites_y3 = sum(RAMP[y]["tn"] for y in (1, 2, 3)) - sum(RAMP[y]["churn"] for y in (1, 2, 3))
    share_of_pharma_sam = round(tn_sites_y3 / sam_tn * 100, 1)

    return {
        "tam_maghreb_pharma_floor_sites": maghreb_floor,
        "tam_note": "Tunisia 55 + Algeria 218, both SOURCED. Morocco publishes no "
                    "site count and is excluded, so this is a FLOOR, not an estimate.",
        "sam_tunisia_pharma_sites": sam_tn,
        "sam_tunisia_value_tnd": sam_tn * PLANS["Standard"]["annual_tnd"],
        "som_y3_total_sites": sites_y3,
        "som_y3_tunisia_sites": tn_sites_y3,
        "som_y3_share_of_tunisia_pharma_sam_pct": share_of_pharma_sam,
        "denominator_problem":
            f"{tn_sites_y3} Tunisian sites is {share_of_pharma_sam}% of a "
            f"pharma-only SAM of {sam_tn}. That share is implausible on its face, "
            "and we are not going to argue for it. The resolution is that the "
            "denominator is wrong, not the numerator: BatchTwin's segment is "
            "nutraceutical, food-supplement, cosmetics and device makers as well "
            "as pharma &mdash; Medicka itself is a supplement maker and does NOT "
            "appear in the 55. No public register counts that population in "
            "Tunisia. Until it is counted, the plan's market share is unstated "
            "rather than estimated. Counting it is open question #1, and "
            "Chapter 12 gives the method and the cost.",
        "avg_first_year_contract_tnd": PLANS["Standard"]["annual_tnd"] + services_total(),
    }


if __name__ == "__main__":
    ue = unit_economics()
    print("=" * 66)
    print("UNIT ECONOMICS (measured, Medicka's real BOM)")
    print("=" * 66)
    for k, v in ue.items():
        print(f"  {k:<24} {v}")

    print()
    print("=" * 66)
    print(f"SERVICES  (day rate {DAY_RATE_TND} TND = {ENG_MONTHLY_TND}/{WORKING_DAYS_PER_MONTH} x {BILL_MULTIPLIER})")
    print("=" * 66)
    for r in services_table():
        print(f"  {r['name']:<40} {r['days']:>3}d  {r['price_tnd']:>8,} TND")
    print(f"  {'TOTAL first-year services':<40} {'':>4}  {services_total():>8,} TND")

    m = build_model()
    print()
    print("=" * 66)
    print("THREE-YEAR MODEL (TND)")
    print("=" * 66)
    hdr = f"  {'':<26}{'Year 1':>13}{'Year 2':>13}{'Year 3':>13}"
    print(hdr)
    rows = [("Active sites", "active_sites"), ("New / churn", None),
            ("Licence revenue", "licence_tnd"), ("Services revenue", "services_tnd"),
            ("TOTAL REVENUE", "revenue_tnd"), ("Payroll", "payroll_tnd"),
            ("Other opex", "opex_tnd"), ("TOTAL COST", "cost_tnd"),
            ("PROFIT", "profit_tnd"), ("Margin %", "margin_pct"),
            ("Cumulative cash", "cumulative_cash_tnd"), ("ARPA", "arpa_tnd")]
    for label, key in rows:
        if key is None:
            vals = [f"+{m[y]['new']}/-{m[y]['churn']}" for y in (1, 2, 3)]
        else:
            vals = [f"{m[y][key]:,}" if isinstance(m[y][key], (int, float)) else "-" for y in (1, 2, 3)]
        print(f"  {label:<26}" + "".join(f"{v:>13}" for v in vals))

    print()
    print("=" * 66)
    print("BREAK-EVEN")
    print("=" * 66)
    for k, v in breakeven(m).items():
        print(f"  {k:<42} {v}")

    print()
    print("=" * 66)
    print("SENSITIVITY (year 3)")
    print("=" * 66)
    for r in sensitivity(m):
        print(f"  {r['scenario']:<24} rev {r['y3_revenue_tnd']:>10,}  "
              f"profit {r['y3_profit_tnd']:>10,}  ({r['delta_vs_base_pct']:+.1f}%)")

    print()
    print("=" * 66)
    print("MARKET")
    print("=" * 66)
    for k, v in market(m).items():
        print(f"  {k:<36} {v}")
