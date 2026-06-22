# report_pdf.py — render the calculator state into a premium one/two-
# page PDF retirement report (Swiss editorial) via WeasyPrint.
import os
import sys
from pathlib import Path

# macOS: WeasyPrint's native deps (pango/cairo/gobject) live in the
# Homebrew lib dir, which the dynamic loader doesn't search by
# default. Add it before WeasyPrint is imported. No-op elsewhere.
if sys.platform == "darwin":
    for _p in ("/opt/homebrew/lib", "/usr/local/lib"):
        if os.path.isdir(_p):
            _cur = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
            _parts = [x for x in _cur.split(":") if x]
            if _p not in _parts:
                _parts.append(_p)
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(_parts)

from jinja2 import Environment, FileSystemLoader, select_autoescape

import insights

ROOT = Path(__file__).parent
CSS_PATH = ROOT / "static" / "css" / "report.css"
_env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    autoescape=select_autoescape(["html"]),
)

_OUTLOOK = {"strong": "Strong", "moderate": "Moderate", "weak": "Weak"}
_SCENARIO = {"positive": "Positive", "moderate": "Moderate",
             "negative": "Negative"}
# Worst → best, left to right in the comparison strip.
_SCN_ORDER = [("negative", "Negative"), ("moderate", "Moderate"),
              ("positive", "Positive")]
_VERDICT = {
    "strong":
        "On track — your pension covers a strong share of today's "
        "income.",
    "moderate":
        "Reasonable — there is room to strengthen your pension.",
    "weak":
        "Below target — extra voluntary saving would help "
        "significantly.",
}


def _eur(value):
    # "€ 1 311" — space thousands, matching the lv-LV UI formatting.
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        n = 0
    return "€ " + f"{n:,.0f}".replace(",", " ")


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bars(t, pillars):
    # Horizontal contribution bars, widths ∝ each pillar's monthly.
    rows = [
        (t("State pension"), "p1", "muted"),
        (t("Investment pension"), "p2", ""),
        (t("Voluntary pension"), "p3", "soft"),
    ]
    monthly = {key: max(0.0, _num((pillars.get(key) or {}).get("monthly")))
               for _, key, _ in rows}
    total = sum(monthly.values()) or 1.0
    return [{
        "name": name, "val": _eur(monthly[key]) + " " + t("/month"),
        "pct": round(monthly[key] / total * 100, 1), "cls": cls,
    } for name, key, cls in rows]


def _scenarios(t, data):
    # Three detailed scenario cards; empty when not provided.
    s = data.get("scenarios") or {}
    if not s:
        return []
    active = data.get("activeScenario", "moderate")
    gross = (data.get("inputs") or {}).get("grossMonthly")
    out = []
    for key, label in _SCN_ORDER:
        v = s.get(key) or {}
        rate = insights.replacement_rate(v.get("realMonthly"), gross)
        band = insights.outlook(rate)
        prop = _num(v.get("propEquity"))
        out.append({
            "label": t(label),
            "real": _eur(v.get("realMonthly")),
            "nominal": _eur(v.get("monthly")),
            "capital": _eur(v.get("capital")),
            "rate": rate,
            # Property is opt-in: only surfaced when a value was entered.
            "property": _eur(prop) if prop > 0 else None,
            "active": key == active,
        })
    return out


def build_report_pdf(data, t, date_str=""):
    # Render the report HTML and convert it to PDF bytes.
    from weasyprint import CSS, HTML
    totals = data.get("totals", {})
    inputs = data.get("inputs", {})
    ins = insights.summarize(data)
    ctx = {
        "t": t, "date": date_str,
        "hero_real": _eur(totals.get("realMonthly")),
        "hero_nominal": _eur(totals.get("monthly")),
        "ret_age": str(inputs.get("retirementAge") or "—"),
        "gross_fmt": _eur(inputs.get("grossMonthly")),
        "active_label": t(_SCENARIO.get(
            inputs.get("scenario", "moderate"), "Moderate")),
        "bars": _bars(t, data.get("pillars", {})),
        "scenarios": _scenarios(t, data),
        "outlook": ins["outlook"],
        "outlook_label": t(_OUTLOOK[ins["outlook"]]),
        "verdict": t(_VERDICT[ins["outlook"]]),
        "rate": ins["replacement_rate"],
        "erosion": ins["inflation_erosion"],
        "exposure": f'{ins["market_share"]}%',
    }
    html = _env.get_template("report.html").render(**ctx)
    return HTML(string=html, base_url=str(ROOT)).write_pdf(
        stylesheets=[CSS(filename=str(CSS_PATH))])
