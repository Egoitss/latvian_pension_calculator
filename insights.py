# insights.py — deterministic retirement-outlook metrics. No AI:
# replacement rate, outlook band, inflation erosion, and a market-
# risk label derived purely from the projected numbers.

# Replacement-rate bands, % of gross salary AT RETIREMENT. Tunable;
# single source of truth — ai_review imports these for its prompt.
WEAK_MAX = 20.0       # rate < WEAK_MAX             -> weak
MODERATE_MAX = 30.0   # WEAK_MAX <= rate < MOD_MAX  -> moderate
STRONG_MAX = 45.0     # MOD_MAX <= rate < STRONG    -> strong; >= excellent

# Market-pillar share thresholds (% of monthly pension from P2+P3).
RISK_HIGH_MIN = 55.0
RISK_MODERATE_MIN = 30.0


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def replacement_rate(pension_monthly, salary_monthly):
    # Nominal pension as a % of gross salary at retirement.
    salary = _num(salary_monthly)
    if salary <= 0:
        return 0.0
    return round(_num(pension_monthly) / salary * 100, 1)


def outlook(rate):
    # Band the replacement rate into strong / moderate / weak.
    if rate >= MODERATE_MAX:
        return "strong"
    if rate >= WEAK_MAX:
        return "moderate"
    return "weak"


def band(rate):
    # Four-way band (adds EXCELLENT) used by the AI prompt + verdict.
    if rate < WEAK_MAX:
        return "WEAK"
    if rate < MODERATE_MAX:
        return "MODERATE"
    if rate < STRONG_MAX:
        return "STRONG"
    return "EXCELLENT"


def salary_at_retirement(inputs):
    # Projected gross monthly salary at retirement; fall back to the
    # current salary when the projected value is absent (old payloads).
    data = inputs or {}
    projected = _num(data.get("grossAtRetirement"))
    return projected if projected > 0 else _num(data.get("grossMonthly"))


def inflation_erosion(nominal_monthly, real_monthly):
    # % of the nominal pension lost to inflation by retirement.
    nominal = _num(nominal_monthly)
    if nominal <= 0:
        return 0.0
    lost = max(0.0, (nominal - _num(real_monthly)) / nominal)
    return round(lost * 100, 1)


def market_share(pillars):
    # Share of monthly pension from market pillars (2 + 3) vs state.
    p = pillars or {}

    def monthly(key):
        return max(0.0, _num((p.get(key) or {}).get("monthly")))

    total = monthly("p1") + monthly("p2") + monthly("p3")
    if total <= 0:
        return 0.0
    return round((monthly("p2") + monthly("p3")) / total * 100, 1)


def risk_level(pillars):
    # Higher market-pillar share → more exposure to market swings.
    share = market_share(pillars)
    if share >= RISK_HIGH_MIN:
        return "higher"
    if share >= RISK_MODERATE_MIN:
        return "moderate"
    return "lower"


def summarize(data):
    # Bundle every insight metric for the report template.
    totals = data.get("totals", {})
    inputs = data.get("inputs", {})
    pillars = data.get("pillars", {})
    rate = replacement_rate(
        totals.get("monthly"), salary_at_retirement(inputs))
    return {
        "replacement_rate": rate,
        "outlook": outlook(rate),
        "inflation_erosion": inflation_erosion(
            totals.get("monthly"), totals.get("realMonthly")),
        "market_share": market_share(pillars),
        "risk": risk_level(pillars),
    }
