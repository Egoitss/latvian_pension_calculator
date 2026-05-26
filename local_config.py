# Personal defaults — not for version control
OVERRIDES = {
    "birth_year": 1982,
    "birth_month": 8,
    "balance": 20819.80,
    "gross_monthly": 1830,
    "selected_plan_name": "SEB indeksu plāns 15-54",
    "p2l_start_year": 2002,
    "p2l_start_salary": 140,
    "p2l_actual_contributions": 15070.35,
    "salary_growth": 5.0,   # historical 11.3% was catch-up; ~5% realistic going forward
    "inflation": 4.16,       # Latvian CPI geometric mean 2002–2025
    "p2l_rate": 6.0,         # current legal rate; adjust to model future cuts
    # 1st-pillar NDC personal values
    "p1_capital": 83236.97,
    "p1_record_years": 22,
    "p1_record_months": 10,
    # 3rd-pillar voluntary pension (Swedbank Dinamika 18-49)
    "p3_balance":             5175.94,
    "p3_monthly":             27.5,
    "p3_contribution_growth": 5.0,
    "p3_plan_name":           "Swedbank Dinamika 18-49",
    # Mortgage (SEB, variable rate: bank margin + EURIBOR 3M; ends 16.12.2051)
    "mort_balance":        103964.62,
    "mort_end_month":      12,
    "mort_end_year":       2051,
    "mort_bank_margin":    1.740,
    "mort_euribor":        2.130,
    "mort_actual_payment": 537.31,
    # Car loan (fixed rate; GPL 10.870% is APR for comparison only; ends 15.07.2029)
    "cred_balance":        4904.05,
    "cred_end_month":      7,
    "cred_end_year":       2029,
    "cred_bank_margin":    9.900,
    "cred_euribor":        0.000,
    "cred_actual_payment": 151.23,
    # Property widget defaults — Valmiera home
    "prop_price": 250_000,
    "prop_type":  "valmiera",
}
