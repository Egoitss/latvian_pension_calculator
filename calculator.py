from data import (
    DEFAULT_RETURN, P2L_RATE, VSAOI_CEILING,
    PENSION_TAX_FREE_THRESHOLD, PENSION_TAX_RATE,
    PLANS, get_plan_by_name, historical_p2l_rate, HISTORICAL_INFLATION,
    G_TABLE, get_g_coefficient,
    P3_TAX_DEDUCTION_CAP, P3_TAX_DEDUCTION_RATE, P3_IIN_RATE,
    P3_PAYOUT_GAINS_TAX,
    DINAMIKA_MONTHLY_RETURNS,
)


def get_annual_return(plan, manual_return):
    # Resolve the annual return % for a plan dict
    if not plan:
        return DEFAULT_RETURN
    if plan.get("manual"):
        # User-defined return from slider
        try:
            return float(manual_return)
        except (TypeError, ValueError):
            return DEFAULT_RETURN
    if plan.get("benchmark"):
        # Market index — use long-run assumption
        return float(plan.get("assumption_return", DEFAULT_RETURN))
    # Real plan — prefer 5-year return, fall back to 3-year
    for key in ("return_5y", "return_3y"):
        val = plan.get(key)
        if val is not None:
            return float(val)
    return DEFAULT_RETURN


def should_apply_vsaoi_ceiling(
    age, retirement_age, gross_monthly, salary_growth
):
    # Return True if current or future annual gross will exceed the VSAOI cap
    safe_age = max(0, round(float(age)))
    safe_ret = max(safe_age, round(float(retirement_age)))
    annual_gross = max(0.0, float(gross_monthly)) * 12
    growth = float(salary_growth) / 100
    years = max(0, safe_ret - safe_age)

    for _ in range(years + 1):
        if annual_gross > VSAOI_CEILING:
            return True
        annual_gross *= 1 + growth
    return False


def build_plan_schedule(
    age, retirement_age, selected_plan_name, manual_return,
    enable_switching, switch_one_age, switch_one_plan_name,
    switch_two_age, switch_two_plan_name,
):
    # Build a sorted list of {starts_at_age, plan_name} switch entries
    safe_age = max(0, round(float(age)))
    safe_ret = max(safe_age, round(float(retirement_age)))

    schedule = [
        {"starts_at_age": safe_age, "plan_name": selected_plan_name},
    ]

    if enable_switching:
        # Clamp switch ages between current age+1 and retirement age
        first = max(
            safe_age + 1,
            min(safe_ret, round(float(switch_one_age))),
        )
        second = max(
            first + 1,
            min(safe_ret, round(float(switch_two_age))),
        )
        if first < safe_ret:
            schedule.append(
                {"starts_at_age": first, "plan_name": switch_one_plan_name}
            )
        if second < safe_ret:
            schedule.append(
                {"starts_at_age": second, "plan_name": switch_two_plan_name}
            )

    return sorted(schedule, key=lambda e: e["starts_at_age"])


def get_active_schedule_entry(schedule, age):
    # Return the most-recently-started entry for the given age
    active = schedule[0]
    for entry in schedule:
        if age >= entry["starts_at_age"]:
            active = entry
    return active


def calculate_projection(
    age, retirement_age, balance, gross_monthly,
    salary_growth, inflation, payout_years,
    apply_ceiling, plan_schedule, manual_return,
    p2l_rate=P2L_RATE,
):
    # Year-by-year accumulation from current age to retirement
    safe_age = max(0, round(float(age)))
    safe_ret = max(safe_age, round(float(retirement_age)))
    current_balance = max(0.0, float(balance))
    annual_gross = max(0.0, float(gross_monthly)) * 12
    growth = float(salary_growth) / 100
    infl = float(inflation) / 100
    safe_payout_yrs = max(1, float(payout_years))
    years = max(0, safe_ret - safe_age)

    # Seed the first row (year 0) with the opening balance
    cumulative_contributions = current_balance
    rows = [{
        "age": safe_age,
        "year": 0,
        "annual_gross": round(annual_gross),
        "annual_contribution": 0,
        "annual_return": 0.0,
        "active_plan": get_plan_by_name(
            plan_schedule[0]["plan_name"]
        )["name"],
        "contributions": round(cumulative_contributions),
        "earnings": 0,
        "total": round(current_balance),
        "real_total": round(current_balance),
    }]

    for i in range(1, years + 1):
        # Determine which plan is active this year
        current_age = safe_age + i
        entry = get_active_schedule_entry(plan_schedule, current_age)
        plan = get_plan_by_name(entry["plan_name"])
        rate = get_annual_return(plan, manual_return) / 100

        # Compute contribution, respecting VSAOI ceiling if applicable
        contrib_base = (
            min(annual_gross, VSAOI_CEILING) if apply_ceiling
            else annual_gross
        )
        annual_contribution = max(0.0, contrib_base * p2l_rate)
        cumulative_contributions += annual_contribution

        # Compound balance for the year
        current_balance = (
            (current_balance + annual_contribution) * (1 + rate)
        )
        real_discount = (1 + infl) ** i
        real_total = (
            current_balance / real_discount if real_discount > 0
            else current_balance
        )

        rows.append({
            "age": current_age,
            "year": i,
            "annual_gross": round(annual_gross),
            "annual_contribution": round(annual_contribution),
            "annual_return": round(rate * 100, 4),
            "active_plan": plan["name"],
            "contributions": round(cumulative_contributions),
            "earnings": round(current_balance - cumulative_contributions),
            "total": round(current_balance),
            "real_total": round(real_total),
        })
        annual_gross *= 1 + growth

    # Compute monthly payout figures from the final balance
    final = rows[-1]
    payout_months = safe_payout_yrs * 12
    monthly_payout = final["total"] / payout_months
    real_monthly_payout = final["real_total"] / payout_months

    # Apply pension income tax above the monthly tax-free threshold
    taxable = max(0.0, monthly_payout - PENSION_TAX_FREE_THRESHOLD)
    monthly_tax = taxable * PENSION_TAX_RATE
    monthly_payout_after_tax = monthly_payout - monthly_tax

    real_taxable = max(0.0, real_monthly_payout - PENSION_TAX_FREE_THRESHOLD)
    real_monthly_tax = real_taxable * PENSION_TAX_RATE
    real_monthly_after_tax = real_monthly_payout - real_monthly_tax

    return {
        "rows": rows,
        "final": final,
        "monthly_payout": monthly_payout,
        "real_monthly_payout": real_monthly_payout,
        "monthly_tax": monthly_tax,
        "monthly_payout_after_tax": monthly_payout_after_tax,
        "real_monthly_tax": real_monthly_tax,
        "real_monthly_after_tax": real_monthly_after_tax,
        "years": years,
    }


def calculate_implied_return(
    start_year, start_salary, current_salary, current_balance,
    actual_contributions=None,
):
    # Back-calculate the average annual return that explains how past
    # contributions grew to the current balance, using bisection search.
    # Salary growth is derived from the two known endpoints, not the slider.
    from datetime import date
    current_year = date.today().year
    try:
        start_yr = int(start_year)
        salary0 = max(0.0, float(start_salary))
        salary_now = max(0.0, float(current_salary))
        balance = max(0.0, float(current_balance))
    except (TypeError, ValueError):
        return None

    n = current_year - start_yr
    if start_yr < 2001 or start_yr >= current_year or salary0 <= 0 or balance <= 0:
        return None

    # Derive growth rate from (start salary → current salary) over n years
    growth = (salary_now / salary0) ** (1 / n) - 1 if salary_now > 0 else 0.0

    # Reconstructed undiscounted total for optional scaling
    recon_total = 0.0
    ag = salary0 * 12
    for i in range(n):
        recon_total += min(ag, VSAOI_CEILING) * historical_p2l_rate(start_yr + i)
        ag *= 1 + growth
    actual = max(0.0, float(actual_contributions or 0))
    scale = actual / recon_total if (actual > 0 and recon_total > 0) else 1.0

    def fv(rate):
        # Forward value of all P2L contributions compounded to today
        total = 0.0
        annual_gross = salary0 * 12
        for i in range(n):
            p2l_rate = historical_p2l_rate(start_yr + i)
            contrib_base = min(annual_gross, VSAOI_CEILING)
            # Mid-year contribution scaled to match actual total if provided
            total += contrib_base * p2l_rate * scale * ((1 + rate) ** (n - i - 0.5))
            annual_gross *= 1 + growth
        return total

    # Bisect between -10 % and +100 % to find r where fv(r) = balance
    lo, hi = -0.10, 1.00
    for _ in range(80):
        mid = (lo + hi) / 2
        if fv(mid) < balance:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-7:
            break
    r_nom = (lo + hi) / 2

    # Geometric-mean annual inflation over the accumulation period
    cumulative_infl = 1.0
    for i in range(n):
        cumulative_infl *= 1 + HISTORICAL_INFLATION.get(start_yr + i, 0.025)
    avg_infl = cumulative_infl ** (1 / n) - 1
    r_real = (1 + r_nom) / (1 + avg_infl) - 1

    return {
        "nominal": r_nom * 100,
        "real": r_real * 100,
        "recon_contributions": round(recon_total * scale),
    }


def monthly_p1_pension(final_capital, g_coefficient):
    # Monthly pension = accumulated NDC capital / (G years × 12 months)
    if g_coefficient <= 0:
        return 0.0
    return final_capital / (g_coefficient * 12)


def calculate_p1_projection(
    age, retirement_age, current_capital,
    gross_monthly, salary_growth, revaluation_rate,
    p1_rate=0.14,
):
    # Year-by-year 1st-pillar NDC capital from current age to retirement
    safe_age = max(0, round(float(age)))
    safe_ret = max(safe_age, round(float(retirement_age)))
    capital = max(0.0, float(current_capital))
    annual_gross = max(0.0, float(gross_monthly)) * 12
    growth = float(salary_growth) / 100
    reval = float(revaluation_rate) / 100
    years = max(0, safe_ret - safe_age)

    for _ in range(years):
        # Revalue accumulated capital at year start, then credit contribution
        capital *= (1 + reval)
        contrib_base = min(annual_gross, VSAOI_CEILING)
        capital += contrib_base * p1_rate
        annual_gross *= (1 + growth)

    return {"final_capital": round(capital), "years": years}


def calculate_p3_annual_refund(gross_monthly, monthly_contribution):
    # IIN refund = min(annual_contrib, min(10% of annual_gross, €4 000)) × 25.5%
    annual_gross = max(0.0, float(gross_monthly)) * 12
    annual_contrib = max(0.0, float(monthly_contribution)) * 12
    eligible_cap = min(annual_gross * P3_TAX_DEDUCTION_RATE,
                       P3_TAX_DEDUCTION_CAP)
    eligible = min(annual_contrib, eligible_cap)
    return round(eligible * P3_IIN_RATE, 2)


def calculate_p3_projection(
    age, retirement_age, current_balance,
    gross_monthly, monthly_contribution,
    contribution_growth, plan_return,
    inflation,
):
    # Year-by-year 3rd-pillar balance: grow by net return, add annual contributions
    safe_age = max(0, round(float(age)))
    safe_ret = max(safe_age, round(float(retirement_age)))
    years = max(0, safe_ret - safe_age)

    balance = max(0.0, float(current_balance))
    monthly = max(0.0, float(monthly_contribution))
    growth = float(contribution_growth) / 100
    r = float(plan_return) / 100
    infl = float(inflation) / 100
    total_own_contrib = 0.0

    for _ in range(years):
        annual_contrib = monthly * 12
        # Grow balance at net return rate, then credit annual contribution
        balance = balance * (1 + r) + annual_contrib
        total_own_contrib += annual_contrib
        monthly *= (1 + growth)

    total_invested = float(current_balance) + total_own_contrib
    gains = max(0.0, balance - total_invested)
    tax_on_gains = gains * P3_PAYOUT_GAINS_TAX
    deflator = (1 + infl) ** years if years > 0 else 1.0
    real_balance = balance / deflator if deflator > 0 else balance

    return {
        "final_balance": round(balance, 2),
        "real_balance": round(real_balance, 2),
        "total_own_contrib": round(total_own_contrib, 2),
        "gains": round(gains, 2),
        "tax_on_gains": round(tax_on_gains, 2),
        "net_payout": round(balance - tax_on_gains, 2),
        "years": years,
    }


def bootstrap_scenario_returns(num_months, n_simulations=10_000, seed=None):
    # Bootstrap Monte Carlo using Dinamika 18-49 historical monthly returns.
    # Draws num_months returns (with replacement) per simulation, compounds
    # them to a final multiplier, then converts the 10/50/90th percentile
    # multipliers to annualized return rates (%).
    import random
    rng = random.Random(seed)
    pool = DINAMIKA_MONTHLY_RETURNS
    multipliers = []

    for _ in range(n_simulations):
        mult = 1.0
        for _ in range(num_months):
            mult *= 1.0 + rng.choice(pool)
        multipliers.append(mult)

    multipliers.sort()
    exp = 12.0 / max(1, num_months)

    def pct_rate(p):
        idx = max(0, min(n_simulations - 1, int(p * n_simulations)))
        return round((multipliers[idx] ** exp - 1) * 100, 2)

    return {
        "positive": pct_rate(0.90),
        "moderate": pct_rate(0.50),
        "negative": pct_rate(0.10),
    }
