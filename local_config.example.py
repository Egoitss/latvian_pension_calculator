# Copy this file to local_config.py and fill in your own values.
# local_config.py is gitignored — it will never be committed.

OVERRIDES = {
    # Personal profile
    "birth_year":  1990,
    "birth_month": 6,
    # 2nd pillar pension
    "balance":               3_500.00,
    "gross_monthly":         1_600,
    "selected_plan_name":    "SEB indeksu plāns 15-54",
    "p2l_start_year":        2008,
    "p2l_start_salary":      400,
    "p2l_actual_contributions": 2_100.00,
    "salary_growth":         4.0,
    "inflation":             3.5,
    "p2l_rate":              6.0,
    # 1st pillar NDC
    "p1_capital":       18_000.00,
    "p1_record_years":  12,
    "p1_record_months": 4,
    # 3rd pillar
    "p3_balance":             2_000.00,
    "p3_monthly":             20.0,
    "p3_contribution_growth": 3.0,
    "p3_plan_name":           "Swedbank Dinamika 18-49",
    # Mortgage (example: 80 000 EUR, ends Dec 2045, variable)
    "mort_balance":        80_000.00,
    "mort_end_month":      12,
    "mort_end_year":       2045,
    "mort_bank_margin":    2.000,
    "mort_euribor":        2.500,
    "mort_actual_payment": 510.00,
    # Car loan (example: 8 000 EUR, ends Jun 2028, fixed)
    "cred_balance":        8_000.00,
    "cred_end_month":      6,
    "cred_end_year":       2028,
    "cred_bank_margin":    9.900,
    "cred_euribor":        0.000,
    "cred_actual_payment": 180.00,
    # Property widget
    "prop_price": 150_000,
    "prop_type":  "riga",
}

# Historical Dinamika 18-49 NAV prices (monthly, from Swedbank CSV export).
# Replace with your own sequence. Must have at least 2 values.
# Leave as [] if you don't have this data — scenarios use fixed fallback rates.
_DINAMIKA_PRICES = []

# Your personal P3 cost basis BEFORE the simulation window (EUR).
# Set to 0.0 if all your contributions happen within the simulation period.
P3_COST_BASIS = 0.0
