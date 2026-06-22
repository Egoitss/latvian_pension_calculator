import json
import os
import time
from datetime import date as _date

from dotenv import load_dotenv

load_dotenv()  # load DEEPSEEK_API_KEY / ANTHROPIC_API_KEY from .env

from flask import (
    Flask, jsonify, make_response, redirect,
    render_template, request, url_for,
)
from data import (
    PLANS, VSAOI_CEILING, P2L_RATE, DEFAULT_RETURN,
    PENSION_TAX_FREE_THRESHOLD, PENSION_TAX_RATE,
    LATVIJA_LV_P2L_URL, MANAPENSIJA_STATS_URL, STATE_PENSION_URL,
    P3_PLANS,
)
from calculator import (
    build_plan_schedule, should_apply_vsaoi_ceiling,
    calculate_projection,
)
from i18n import (
    lang_from_path, make_t, js_catalog,
)
from report_pdf import build_report_pdf
import ai_review
import download_counter
import rate_limit

app = Flask(__name__)

# Max PDF exports per IP per hour (each may trigger one AI call).
try:
    EXPORT_LIMIT = int(os.environ.get("EXPORT_RATE_LIMIT", "20"))
except ValueError:
    EXPORT_LIMIT = 20


def _alt_path(path: str, lang: str) -> str:
    # Path to the same page in the other language (for the switcher).
    if lang == "lv":
        return path[3:] or "/"          # strip leading "/lv"
    return "/lv" + ("" if path == "/" else path)


@app.context_processor
def inject_i18n():
    # Expose t(), lang, the alt-language path and the JS override map
    # to every template, derived from the current request path.
    lang = lang_from_path(request.path)
    return {
        "t": make_t(lang),
        "lang": lang,
        "alt_path": _alt_path(request.path, lang),
        "js_i18n": js_catalog(lang),
    }


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.svg'), 301)


@app.context_processor
def inject_js_version():
    js_dir = os.path.join(app.static_folder, 'js')
    try:
        max_mtime = max(
            os.path.getmtime(os.path.join(js_dir, f))
            for f in os.listdir(js_dir) if f.endswith('.js')
        )
        js_v = int(max_mtime)
    except Exception:
        js_v = int(time.time())
    return {"js_v": js_v}


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
    # 1st-pillar NDC inputs — set via browser localStorage, empty by default
    "p1_capital": "",
    "p1_record_years": "",
    "p1_record_months": "",
    # Conservative neutral baseline; the active scenario shifts it ±2pp.
    "p1_revaluation_rate": 3.0,
    # 3rd-pillar voluntary pension inputs
    "p3_balance": "",
    "p3_monthly": "",
    "p3_contribution_growth": 5.0,
    "p3_plan_name": "Swedbank Dinamika 18-49",
}

# Load personal JS data from local_config if available
_lc_prices: list = []
_lc_cost_basis: float = 0.0
try:
    from local_config import _DINAMIKA_PRICES as _lc_prices
except (ImportError, AttributeError):
    pass
try:
    from local_config import P3_COST_BASIS as _lc_cost_basis
except (ImportError, AttributeError):
    pass

LOCAL_DATA = {
    "dinamika_prices": _lc_prices,
    "p3_cost_basis": _lc_cost_basis,
}


@app.route("/")
@app.route("/lv")
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
        "state_pension": STATE_PENSION_URL,
    }

    resp = make_response(render_template(
        "index.html",
        plans=PLANS,
        p3_plans=P3_PLANS,
        defaults=d,
        constants=constants,
        urls=urls,
        projection=projection,
        plan_schedule_json=json.dumps(plan_schedule),
        apply_ceiling=apply_ceiling,
        local_data=LOCAL_DATA,
    ))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.route("/loans")
@app.route("/lv/loans")
def loans():
    resp = make_response(render_template(
        "loans.html",
        defaults=DEFAULTS,
    ))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


_AI_SYSTEM_PROMPT = (
    "Tu esi pieredzējis Latvijas finanšu konsultants, kas palīdz cilvēkiem "
    "pieņemt lēmumus par 2. un 3. pensiju līmeņa izmaksu.\n\n"
    "Tavs uzdevums: novērtēt, vai konkrētajai personai būtu izdevīgāk "
    "(a) saņemt 2. un 3. līmeņa uzkrājumus kā vienreizēju izmaksu, "
    "(b) saglabāt kā programmēto pensiju (mēneša izmaksa no fonda), "
    "vai (c) iegādāties mūža pensijas polisi (annuitāti).\n\n"
    "Atbildē apsver: vecums, mūža ilgums (CSP statistika), nodokļi "
    "(25.5% IIN virs 1000 €/mēn 2. līmenim, 25.5% IIN peļņai 3. līmenim), "
    "alternatīvas investīcijas, mantojuma aspekts, drošības tīkls.\n\n"
    "Atbildi LATVIEŠU valodā, 4-6 īsas rindkopas, konkrēti, bez juridiskām "
    "atrunām. NAV finanšu padoms - tikai izglītojoša informācija."
)


def _build_recommend_prompt(d: dict) -> str:
    """Format calculator state into a structured prompt for the AI."""
    age = d.get("age", "—")
    ret_age = d.get("retirementAge", "—")
    yrs_to_ret = d.get("yearsToRetirement", "—")
    gender = d.get("gender", "—")
    scenario = d.get("scenario", "moderate")
    p1 = d.get("p1", {})
    p2 = d.get("p2", {})
    p3 = d.get("p3", {})
    return (
        f"Personas dati:\n"
        f"- Vecums: {age} gadi (dzimums: {gender})\n"
        f"- Pensionēšanās vecums: {ret_age} (pēc ~{yrs_to_ret} gadiem)\n"
        f"- Aktīvais scenārijs: {scenario}\n\n"
        f"1. līmenis (NDC):\n"
        f"- Pašreizējais kapitāls: {p1.get('capital', 0)} €\n"
        f"- Prognozētā mēneša pensija: {p1.get('monthly', 0)} €\n\n"
        f"2. līmenis (fondētais):\n"
        f"- Pašreizējais atlikums: {p2.get('balance', 0)} €\n"
        f"- Prognozētais kapitāls pensijai: {p2.get('finalBalance', 0)} €\n"
        f"- Programmētā mēneša izmaksa: {p2.get('monthlyAfterTax', 0)} €\n\n"
        f"3. līmenis (brīvprātīgais):\n"
        f"- Pašreizējais atlikums: {p3.get('balance', 0)} €\n"
        f"- Prognozētais kapitāls pensijai: {p3.get('finalBalance', 0)} €\n"
        f"- Mēneša izmaksa (neto): {p3.get('monthlyPayout', 0)} €\n\n"
        f"Jautājums: kā šai personai izdevīgāk saņemt 2. un 3. līmeņa "
        f"uzkrājumus pensionējoties?"
    )


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    # Lazy import: keep app boot fast even if anthropic isn't installed
    try:
        from anthropic import Anthropic
    except ImportError:
        return jsonify({"error": "anthropic package not installed"}), 500

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"error": "ANTHROPIC_API_KEY not set"}), 500

    payload = request.get_json(silent=True) or {}
    # Temperature clamped 0.0-1.0, default 0.7
    try:
        temperature = float(payload.get("temperature", 0.7))
    except (TypeError, ValueError):
        temperature = 0.7
    temperature = max(0.0, min(1.0, temperature))

    prompt = _build_recommend_prompt(payload)

    client = Anthropic()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            temperature=temperature,
            system=_AI_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    text = "".join(
        block.text for block in msg.content if getattr(block, "type", "") == "text"
    )
    return jsonify({
        "text": text,
        "temperature": temperature,
        "usage": {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        },
    })


def _client_ip() -> str:
    # First hop in X-Forwarded-For (set by a proxy) else the peer addr.
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd
            else (request.remote_addr or "unknown"))


@app.route("/export/pdf", methods=["POST"])
@app.route("/lv/export/pdf", methods=["POST"])
def export_pdf():
    # Build the PDF retirement report from the posted calculator
    # state, localized to the request path's language, and count it.
    # Per-IP throttle in front of the AI call (see rate_limit).
    if not rate_limit.allow(f"pdf:{_client_ip()}", EXPORT_LIMIT, 3600):
        return make_response(("Too many requests, try later.", 429))
    lang = lang_from_path(request.path)
    payload = request.get_json(silent=True) or {}
    date_str = _date.today().isoformat()
    # Short DeepSeek verdict; None (graceful fallback) if key/API absent.
    review = ai_review.generate_review(payload, lang)
    blob = build_report_pdf(payload, make_t(lang), date_str, review)
    total = download_counter.increment()
    app.logger.info("pdf export #%d", total)

    resp = make_response(blob)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="pension-report-{date_str}.pdf"'
    )
    resp.headers["X-Download-Count"] = str(total)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/download-count")
def api_download_count():
    # Read-only total downloads — handy once the app is live.
    return jsonify({"count": download_counter.read_count()})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
