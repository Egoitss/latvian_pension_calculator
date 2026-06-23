# insights.py — deterministic retirement-outlook metrics. No AI:
# replacement rate, outlook band, inflation erosion, and a market-
# risk label derived purely from the projected numbers.

# Replacement-rate thresholds, % of gross income. Tunable.
STRONG_MIN = 60.0
MODERATE_MIN = 40.0

# Market-pillar share thresholds (% of monthly pension from P2+P3).
RISK_HIGH_MIN = 55.0
RISK_MODERATE_MIN = 30.0


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def replacement_rate(real_monthly, gross_monthly):
    # Real (today's-money) pension as a % of current gross income.
    gross = _num(gross_monthly)
    if gross <= 0:
        return 0.0
    return round(_num(real_monthly) / gross * 100, 1)


def outlook(rate):
    # Band the replacement rate into strong / moderate / weak.
    if rate >= STRONG_MIN:
        return "strong"
    if rate >= MODERATE_MIN:
        return "moderate"
    return "weak"


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
        totals.get("realMonthly"), inputs.get("grossMonthly"))
    return {
        "replacement_rate": rate,
        "outlook": outlook(rate),
        "inflation_erosion": inflation_erosion(
            totals.get("monthly"), totals.get("realMonthly")),
        "market_share": market_share(pillars),
        "risk": risk_level(pillars),
    }
