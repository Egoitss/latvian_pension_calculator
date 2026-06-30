# cases.py — eval test cases for the AI-review prompt.
# Each case: {id, lang, data}. Expected behaviour is DERIVED from the
# data via ai_review._facts (band, oversized, etc.), so cases stay in
# sync with the scoring logic. Covers the band x property x language
# matrix plus edge cases (empty input, totals-only fallback).
#
# Rate = nominal pension / gross salary AT RETIREMENT; nominal = real*5
# (≈ inflation over a long horizon). grossAtRetirement is picked to land
# the rate in each band (WEAK <45, MODERATE 45-60, STRONG 60-75,
# EXCELLENT >=75):
#   real 560  → nominal 2800; gAR 8000 → 35.0% WEAK
#   real 700  → nominal 3500; gAR 7000 → 50.0% MODERATE
#   real 900  → nominal 4500; gAR 6800 → 66.2% STRONG
#   real 1200 → nominal 6000; gAR 7500 → 80.0% EXCELLENT
_CAPITAL = 300000

# Property presets (propEquity nominal, propEquity today's money, m²).
_NONE = (0, 0, 0)
_MODEST = (120000, 90000, 55)        # fits ~2 → right-sized
_OVERSIZED = (350000, 240000, 120)   # fits ~4 → oversized for a couple


def _data(real, gross_at_ret, prop=_NONE):
    equity, equity_real, size = prop
    nominal = round(real * 5)        # ~5x inflation over the horizon
    return {
        "inputs": {"grossMonthly": 1750, "grossAtRetirement": gross_at_ret,
                   "retirementAge": 65, "scenario": "moderate",
                   "homeSize": size},
        "totals": {"realMonthly": real, "monthly": nominal,
                   "capital": _CAPITAL},
        "scenarios": {"moderate": {
            "realMonthly": real, "monthly": nominal,
            "capital": _CAPITAL, "propEquity": equity,
            "propEquityReal": equity_real}},
    }


def _both(prefix, real, gar, prop=_NONE):
    return [
        {"id": f"{prefix}_en", "lang": "en", "data": _data(real, gar, prop)},
        {"id": f"{prefix}_lv", "lang": "lv", "data": _data(real, gar, prop)},
    ]


CASES = (
    _both("weak_none", 560, 8000)
    + _both("weak_oversized", 560, 8000, _OVERSIZED)
    + _both("moderate_modest", 700, 7000, _MODEST)
    + _both("moderate_oversized", 700, 7000, _OVERSIZED)
    + _both("strong_none", 900, 6800)
    # STRONG + oversized: must NOT push downsizing (no shortfall).
    + _both("strong_oversized", 900, 6800, _OVERSIZED)
    + _both("excellent_none", 1200, 7500)
    # EXCELLENT + oversized: the regression case — affirm, never downsize.
    + _both("excellent_oversized", 1200, 7500, _OVERSIZED)
    + [
        # Edge: empty payload — everything zero, must not crash/hallucinate.
        {"id": "edge_empty_en", "lang": "en", "data": {}},
        # Edge: totals only, no scenarios → _moderate falls back to totals.
        {"id": "edge_totals_lv", "lang": "lv", "data": {
            "inputs": {"grossMonthly": 1750, "grossAtRetirement": 9000,
                       "retirementAge": 65},
            "totals": {"realMonthly": 700, "monthly": 3200,
                       "capital": 250000}}},
    ]
)
