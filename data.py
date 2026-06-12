# Domain constants used across calculator and app layers

VSAOI_CEILING = 105_300        # annual gross cap for P2L contributions (EUR)
P2L_RATE = 0.06                # employee contribution rate to 2nd pillar
DEFAULT_RETURN = 8.0           # fallback annual return when no plan data (%)
PENSION_TAX_FREE_THRESHOLD = 1_000  # monthly payout exempt from tax (EUR)
PENSION_TAX_RATE = 0.255       # tax rate on payout above threshold (25.5%)

# External URLs shown as copy-link helpers in the UI
LATVIJA_LV_P2L_URL = "https://latvija.gov.lv/Services/45686"
MANAPENSIJA_STATS_URL = (
    "https://www.manapensija.lv/en/2nd-pension-pillar/statistics/"
)

# Pension plan dataset — sourced from public manapensija.lv statistics.
# Keys: category, name, return_3y, return_5y, fee_total (real plans);
#       assumption_return, benchmark=True (market index benchmarks);
#       manual=True (custom user-defined entry).
PLANS = [
    # Custom manual entry — user sets return via slider
    {
        "category": "Custom",
        "name": "Manual assumption",
        "return_3y": DEFAULT_RETURN,
        "return_5y": DEFAULT_RETURN,
        "manual": True,
    },

    # Market benchmark assumptions — long-run historical averages
    {
        "category": "Global market indices",
        "name": "S&P 500 long-term average",
        "assumption_return": 10.0,
        "benchmark": True,
    },
    {
        "category": "Global market indices",
        "name": "MSCI World long-term average",
        "assumption_return": 8.6,
        "benchmark": True,
    },
    {
        "category": "Global market indices",
        "name": "NASDAQ-100 long-term average",
        "assumption_return": 13.5,
        "benchmark": True,
    },
    {
        "category": "Global market indices",
        "name": "Stoxx Europe 600 long-term average",
        "assumption_return": 7.2,
        "benchmark": True,
    },

    # Passive / index-tracking plans
    {
        "category": "Passive / index plans",
        "name": "SEB indeksu plāns 15-54",
        "return_3y": 14.63, "return_5y": 11.49, "fee_total": 0.30,
    },
    {
        "category": "Passive / index plans",
        "name": "INDEXO plāns Jauda 16-55",
        "return_3y": 13.71, "return_5y": 11.15, "fee_total": 0.39,
    },
    {
        "category": "Passive / index plans",
        "name": "INDEXO Izaugsme 16-55",
        "return_3y": 12.42, "return_5y": 9.82, "fee_total": 0.46,
    },

    # Actively managed aggressive plans
    {
        "category": "Active plans",
        "name": "SEB izaugsmes plāns 15-54",
        "return_3y": 12.99, "return_5y": 10.05, "fee_total": 0.38,
    },
    {
        "category": "Active plans",
        "name": "INVL MAKSIMĀLAIS 16+",
        "return_3y": 12.08, "return_5y": 9.34, "fee_total": 0.74,
    },
    {
        "category": "Active plans",
        "name": "CBL Aktīvais plāns",
        "return_3y": 10.87, "return_5y": 8.74, "fee_total": 0.79,
    },
    {
        "category": "Active plans",
        "name": "Luminor Aktīvais plāns",
        "return_3y": 10.14, "return_5y": 8.02, "fee_total": 0.72,
    },

    # Lifecycle plans — gradually shift to conservative as retirement nears
    {
        "category": "Lifecycle plans",
        "name": "Swedbank dzīves cikla plāns 1990+",
        "return_3y": 11.61, "return_5y": 9.19, "fee_total": 0.37,
    },
    {
        "category": "Lifecycle plans",
        "name": "Swedbank dzīves cikla plāns 1980+",
        "return_3y": 11.42, "return_5y": 9.09, "fee_total": 0.37,
    },
    {
        "category": "Lifecycle plans",
        "name": "Swedbank dzīves cikla plāns 1970+",
        "return_3y": 10.88, "return_5y": 8.61, "fee_total": 0.37,
    },
    {
        "category": "Lifecycle plans",
        "name": "SEB dzīves cikla plāns",
        "return_3y": 10.77, "return_5y": 8.54, "fee_total": 0.63,
    },

    # Conservative / classic low-risk plans
    {
        "category": "Conservative / classic",
        "name": "Swedbank Stabilitāte",
        "return_3y": 2.91, "return_5y": 1.87, "fee_total": 0.58,
    },
    {
        "category": "Conservative / classic",
        "name": "SEB konservatīvais plāns",
        "return_3y": 2.74, "return_5y": 1.65, "fee_total": 0.32,
    },
    {
        "category": "Conservative / classic",
        "name": "Luminor Konservatīvais plāns",
        "return_3y": 2.43, "return_5y": 1.54, "fee_total": 0.67,
    },
    {
        "category": "Conservative / classic",
        "name": "CBL Konservatīvais plāns",
        "return_3y": 2.18, "return_5y": 1.42, "fee_total": 0.73,
    },

    # Balanced plans — mix of equity and fixed income
    {
        "category": "Balanced plans",
        "name": "SEB Sabalansētais plāns",
        "return_3y": 6.81, "return_5y": 4.92, "fee_total": 0.40,
    },
    {
        "category": "Balanced plans",
        "name": "Swedbank Sabalansētais plāns",
        "return_3y": 6.54, "return_5y": 4.61, "fee_total": 0.39,
    },
    {
        "category": "Balanced plans",
        "name": "Luminor Sabalansētais plāns",
        "return_3y": 6.12, "return_5y": 4.22,
    },

    # ESG / sustainability-focused balanced plans
    {
        "category": "Sustainable / ESG",
        "name": "C Ilgtspējas plāns 15-50",
        "return_3y": 8.91, "return_5y": 6.24,
    },
    {
        "category": "Sustainable / ESG",
        "name": "Luminor Ilgtspējīgais plāns",
        "return_3y": 8.33, "return_5y": 6.01,
    },
]


def get_plan_by_name(name):
    # Find a plan dict by name, falling back to the first (custom) plan
    return next((p for p in PLANS if p["name"] == name), PLANS[0])


# Latvian CPI annual inflation by calendar year (fraction, e.g. 0.0139 = 1.39 %)
HISTORICAL_INFLATION = {
    2002: 0.0139, 2003: 0.0361, 2004: 0.0733, 2005: 0.0696,
    2006: 0.0684, 2007: 0.1406, 2008: 0.1054, 2009: -0.0117,
    2010: 0.0254, 2011: 0.0403, 2012: 0.0160, 2013: -0.0042,
    2014: 0.0020, 2015: 0.0034, 2016: 0.0218, 2017: 0.0215,
    2018: 0.0255, 2019: 0.0226, 2020: -0.0050, 2021: 0.0792,
    2022: 0.2083, 2023: 0.0063, 2024: 0.0326, 2025: 0.0349,
}


def historical_p2l_rate(year):
    # Return the P2L contribution rate (fraction of gross) for the given year
    if year <= 2006: return 0.02   # 2001–2006: 2 %
    if year == 2007: return 0.04   # 2007: 4 %
    if year == 2008: return 0.08   # 2008: 8 %
    if year <= 2012: return 0.02   # 2009–2012: 2 %
    if year <= 2014: return 0.04   # 2013–2014: 4 %
    if year == 2015: return 0.05   # 2015: 5 %
    return 0.06                    # 2016–present: 6 %


# G coefficient (years) by retirement age — Latvia 2025
# Source: Cabinet Regulations Nr. 1445 (VSAA), updated annually
# Monthly pension formula: capital / (G × 12)
G_TABLE = {
    60: 22.0, 61: 21.2, 62: 20.4, 63: 19.5,
    64: 17.96, 65: 17.24, 66: 16.9, 67: 16.51,
    68: 16.1, 69: 15.7, 70: 15.3,
}


def get_g_coefficient(retirement_age):
    # Return G (years) clamped to the known table range 60–70
    age = max(60, min(70, round(float(retirement_age))))
    return G_TABLE[age]


# Effective divisor (months) for mūža pensija annuity pricing.
# Derived from CSP 2023 life tables with 10% insurer loading
# (longevity margin + expenses). monthly ≈ capital / ANNUITY_DIVISOR[g][age]
# Applicable age range: 62–69. Source: ERGO, BTA market calibration.
ANNUITY_DIVISOR = {
    "male": {
        62: 209, 63: 202, 64: 196, 65: 189,
        66: 183, 67: 176, 68: 169, 69: 162,
    },
    "female": {
        62: 284, 63: 273, 64: 264, 65: 253,
        66: 244, 67: 234, 68: 224, 69: 215,
    },
}


# 3rd-pillar IIN tax relief constants (Cabinet Reg. 2023)
P3_TAX_DEDUCTION_CAP = 4_000        # max annual contribution eligible for refund
P3_TAX_DEDUCTION_RATE = 0.10        # max 10% of annual gross qualifies
P3_IIN_RATE = 0.255                  # income-tax rate used for refund (25.5%)
P3_PAYOUT_GAINS_TAX = 0.255         # tax on investment gains at payout
P3_MIN_PAYOUT_AGE = 55              # earliest unrestricted withdrawal age

# 3rd-pillar open pension fund dataset.
# Data sourced from manapensija.lv — update return_3y, return_5y, fee_total
# in both data.py and static/js/data.js when refreshing figures.
P3_PLANS = [
    {"provider": "Swedbank", "name": "Swedbank Dinamika 18-49",  "return_3y": 14.51, "return_5y": 9.20, "fee_total": 0.65},
    {"provider": "Swedbank", "name": "Swedbank Stabilitāte 50+", "return_3y":  5.80, "return_5y": 3.90, "fee_total": 0.55},
    {"provider": "SEB",      "name": "SEB Aktīvais plāns",       "return_3y": 11.66, "return_5y": 8.48, "fee_total": 0.95},
    {"provider": "SEB",      "name": "SEB Sabalansētais plāns",  "return_3y":  7.42, "return_5y": 5.55, "fee_total": 0.75},
    {"provider": "INDEXO",   "name": "INDEXO 3. pīlārs",         "return_3y": 10.50, "return_5y": 8.20, "fee_total": 0.40},
    {"provider": "CBL",      "name": "CBL Aktīvais",             "return_3y":  9.10, "return_5y": 6.80, "fee_total": 0.80},
    {"provider": "Luminor",  "name": "Luminor Aktīvais",         "return_3y":  8.20, "return_5y": 6.10, "fee_total": 0.85},
    {"provider": "INVL",     "name": "INVL Aktīvais",            "return_3y":  8.60, "return_5y": 6.50, "fee_total": 0.90},
]


def get_p3_plan_by_name(name):
    # Return plan dict matching name, or first plan as fallback
    for p in P3_PLANS:
        if p["name"] == name:
            return p
    return P3_PLANS[0]


# Personal series — loaded from local_config.py if present.
# Falls back to empty list so bootstrap returns fixed fallback rates.
_DINAMIKA_PRICES_LOCAL: list = []
try:
    from local_config import _DINAMIKA_PRICES as _DINAMIKA_PRICES_LOCAL
except (ImportError, AttributeError):
    pass

DINAMIKA_MONTHLY_RETURNS = [
    _DINAMIKA_PRICES_LOCAL[i] / _DINAMIKA_PRICES_LOCAL[i - 1] - 1
    for i in range(1, len(_DINAMIKA_PRICES_LOCAL))
]

P3_COST_BASIS: float = 0.0
try:
    from local_config import P3_COST_BASIS
except (ImportError, AttributeError):
    pass
