# tools/calibrate_bands.py — sweep representative personas and print
# the new replacement rate + band, so the WEAK/MODERATE/STRONG/
# EXCELLENT thresholds in insights.py can be sanity-checked or tuned.
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import insights


def salary_at_ret(gross, growth_pct, years):
    # Mirror calc.js: final working-year salary = gross*(1+g)^(years-1).
    return round(gross * (1 + growth_pct / 100) ** max(0, years - 1))


# (label, current gross, salary growth %, years, nominal total pension)
PERSONAS = [
    ("Young, low save", 1200, 5.0, 37, 900),
    ("Young, strong P3", 1750, 5.0, 35, 2600),
    ("Mid, moderate", 2200, 4.0, 22, 1800),
    ("Older, near retire", 3000, 3.0, 8, 2400),
    ("High earner", 5000, 5.0, 30, 5200),
    ("Low growth", 1600, 2.0, 30, 1300),
]

print(f"{'persona':22}{'salary@ret':>11}{'pension':>9}"
      f"{'rate%':>7}{'band':>11}")
for label, gross, g, yrs, pension in PERSONAS:
    sret = salary_at_ret(gross, g, yrs)
    rate = insights.replacement_rate(pension, sret)
    print(f"{label:22}{sret:>11}{pension:>9}{rate:>7}"
          f"{insights.band(rate):>11}")
