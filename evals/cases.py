# cases.py — eval test cases for the AI-review prompt.
# Each case: {id, lang, data}. The expected behaviour is DERIVED from
# the data via ai_review._facts (band, oversized, etc.), so cases stay
# in sync with the scoring logic. Covers the band x property x language
# matrix plus edge cases (empty input, totals-only fallback).

# gross 1750 → replacement rate = realMonthly / 1750 * 100:
#   560 = 32%  WEAK | 900 = 51% MODERATE
#  1200 = 69%  STRONG | 1450 = 83% EXCELLENT
_GROSS = 1750
_CAPITAL = 300000

# Property presets (propEquity nominal, propEquity today's money, m²).
_NONE = (0, 0, 0)
_MODEST = (120000, 90000, 55)        # fits ~2 → right-sized
_OVERSIZED = (350000, 240000, 120)   # fits ~4 → oversized for a couple


def _data(real, prop=_NONE):
    equity, equity_real, size = prop
    nominal = round(real * 5)        # ~5x inflation over the horizon
    return {
        "inputs": {"grossMonthly": _GROSS, "retirementAge": 65,
                   "scenario": "moderate", "homeSize": size},
        "totals": {"realMonthly": real, "monthly": nominal,
                   "capital": _CAPITAL},
        "scenarios": {"moderate": {
            "realMonthly": real, "monthly": nominal,
            "capital": _CAPITAL, "propEquity": equity,
            "propEquityReal": equity_real}},
    }


def _both(prefix, real, prop=_NONE):
    return [
        {"id": f"{prefix}_en", "lang": "en", "data": _data(real, prop)},
        {"id": f"{prefix}_lv", "lang": "lv", "data": _data(real, prop)},
    ]


CASES = (
    _both("weak_none", 560)
    + _both("weak_oversized", 560, _OVERSIZED)
    + _both("moderate_modest", 900, _MODEST)
    + _both("moderate_oversized", 900, _OVERSIZED)
    + _both("strong_none", 1200)
    # STRONG + oversized: must NOT advise relocation, but MAY downsize.
    + _both("strong_oversized", 1200, _OVERSIZED)
    + _both("excellent_none", 1450)
    + [
        # Edge: empty payload — everything zero, must not crash/hallucinate.
        {"id": "edge_empty_en", "lang": "en", "data": {}},
        # Edge: totals only, no scenarios → _moderate falls back to totals.
        {"id": "edge_totals_lv", "lang": "lv", "data": {
            "inputs": {"grossMonthly": _GROSS, "retirementAge": 65},
            "totals": {"realMonthly": 700, "monthly": 3200,
                       "capital": 250000}}},
    ]
)
