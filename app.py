import json
from datetime import date as _date
from flask import Flask, render_template
from data import (
    PLANS, VSAOI_CEILING, P2L_RATE, DEFAULT_RETURN,
    PENSION_TAX_FREE_THRESHOLD, PENSION_TAX_RATE,
    LATVIJA_LV_P2L_URL, MANAPENSIJA_STATS_URL,
    P3_PLANS,
)
from calculator import (
    build_plan_schedule, should_apply_vsaoi_ceiling,
    calculate_projection,
)

app = Flask(__name__)


def _age_from_birth(birth_year, birth_month):
    today = _date.today()
    age = today.year - birth_year
    if today.month < birth_month:
        age -= 1
    return max(0, age)


# Default input values used for the initial server-side render
_today = _date.today()
DEFAULTS = {
    "birth_year": _today.year - 30,
    "birth_month": _today.month,
    "retirement_age": 65,
    "balance": 12000,
    "gross_monthly": 1750,
    "selected_plan_name": "Swedbank dzīves cikla plāns 1990+",
    "manual_return": DEFAULT_RETURN,
    "salary_growth": 2,
    "inflation": 2.5,
    "payout_years": 18,
    "enable_switching": False,
    "switch_one_age": 50,
    "switch_one_plan_name": "SEB Sabalansētais plāns",
    "switch_two_age": 60,
    "switch_two_plan_name": "Swedbank Stabilitāte",
    # Loan widget pre-fill — empty strings render as no value attribute
    "mort_balance": "", "mort_end_month": "", "mort_end_year": "", "mort_bank_margin": "", "mort_euribor": "", "mort_actual_payment": "",
    "cred_balance": "", "cred_end_month": "", "cred_end_year": "", "cred_bank_margin": "", "cred_euribor": "", "cred_actual_payment": "",
    # Historical analysis inputs — empty by default so JS hides the result
    "p2l_start_year": "",
    "p2l_start_salary": "",
    "p2l_actual_contributions": "",
    "p2l_rate": 6.0,
    # 1st-pillar NDC inputs — override in local_config.py with personal values
    "p1_capital": "",
    "p1_record_years": "",
    "p1_record_months": "",
    "p1_revaluation_rate": 5.0,
    # 3rd-pillar voluntary pension inputs
    "p3_balance": "",
    "p3_monthly": "",
    "p3_contribution_growth": 5.0,
    "p3_plan_name": "Swedbank Dinamika 18-49",
}

try:
    from local_config import OVERRIDES
    DEFAULTS = {**DEFAULTS, **OVERRIDES}
except ImportError:
    pass


@app.route("/")
def index():
    # Compute the initial projection using default inputs
    d = DEFAULTS
    age = _age_from_birth(d["birth_year"], d["birth_month"])
    plan_schedule = build_plan_schedule(
        age=age,
        retirement_age=d["retirement_age"],
        selected_plan_name=d["selected_plan_name"],
        manual_return=d["manual_return"],
        enable_switching=d["enable_switching"],
        switch_one_age=d["switch_one_age"],
        switch_one_plan_name=d["switch_one_plan_name"],
        switch_two_age=d["switch_two_age"],
        switch_two_plan_name=d["switch_two_plan_name"],
    )
    apply_ceiling = should_apply_vsaoi_ceiling(
        age=age,
        retirement_age=d["retirement_age"],
        gross_monthly=d["gross_monthly"],
        salary_growth=d["salary_growth"],
    )
    projection = calculate_projection(
        age=age,
        retirement_age=d["retirement_age"],
        balance=d["balance"],
        gross_monthly=d["gross_monthly"],
        salary_growth=d["salary_growth"],
        inflation=d["inflation"],
        payout_years=d["payout_years"],
        apply_ceiling=apply_ceiling,
        plan_schedule=plan_schedule,
        manual_return=d["manual_return"],
        p2l_rate=d["p2l_rate"] / 100,
    )

    # Bundle constants and URLs for use in templates
    constants = {
        "VSAOI_CEILING": VSAOI_CEILING,
        "P2L_RATE": P2L_RATE,
        "PENSION_TAX_FREE_THRESHOLD": PENSION_TAX_FREE_THRESHOLD,
        "PENSION_TAX_RATE": PENSION_TAX_RATE,
    }
    urls = {
        "latvija_lv": LATVIJA_LV_P2L_URL,
        "manapensija": MANAPENSIJA_STATS_URL,
    }

    return render_template(
        "index.html",
        plans=PLANS,
        p3_plans=P3_PLANS,
        defaults=d,
        constants=constants,
        urls=urls,
        projection=projection,
        plan_schedule_json=json.dumps(plan_schedule),
        apply_ceiling=apply_ceiling,
    )


if __name__ == "__main__":
    app.run(debug=True)
