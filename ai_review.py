# ai_review.py — short, cheap AI verdict for the PDF report, via the
# DeepSeek API (OpenAI-compatible). Always returns text or None; never
# raises, so a flaky API can never break the PDF download.
import logging
import os
import re

import ai_budget
import insights

_log = logging.getLogger(__name__)

_API_BASE = "https://api.deepseek.com"
_MODEL = "deepseek-chat"          # cheap V3 tier
# Latvian is more token-hungry than English; 300 avoids mid-sentence
# truncation while staying a fraction of a cent per report.
_MAX_TOKENS = 300
_TIMEOUT_S = 8.0

_LANG_NAME = {"lv": "Latvian", "en": "English"}

# Scoring table generated from the single source of truth in insights,
# so the prompt can never drift from the code's banding.
_BAND_TABLE = (
    f"- <{insights.WEAK_MAX:g}% = WEAK\n"
    f"- {insights.WEAK_MAX:g}-{insights.MODERATE_MAX:g}% = MODERATE\n"
    f"- {insights.MODERATE_MAX:g}-{insights.STRONG_MAX:g}% = STRONG\n"
    f"- >{insights.STRONG_MAX:g}% = EXCELLENT\n\n"
)

# Comfortable living space and the assumed retiring household size.
# Used to judge whether a home is larger than a couple needs.
_M2_PER_PERSON = 30
_COUPLE = 2

_SYSTEM = (
    "You are a concise retirement insight assistant for a Latvian "
    "pension simulator.\n\n"
    "Reply in {lang}.\n"
    "Use 2-3 short sentences.\n"
    "Be specific, analytical, and practical.\n"
    "Do not use legal disclaimers, motivational language, or generic "
    "financial-advisor phrasing.\n\n"
    "Use ONLY the MODERATE scenario figures.\n\n"
    "Replacement rate scoring (rate = pension vs gross salary AT "
    "RETIREMENT):\n"
    + _BAND_TABLE +
    "Instructions:\n"
    "1. Open with a one-line verdict based on replacement rate.\n"
    "2. Compare projected pension with inflation-adjusted purchasing "
    "power and mention inflation risk if purchasing power drops "
    "materially.\n"
    "3. Recommendations depend ENTIRELY on the outlook band:\n"
    "   - STRONG or EXCELLENT: there is NO shortfall (EXCELLENT = "
    "comfortably exceeds typical needs). Your reply must contain NO "
    "advice to downsize, sell property or assets, relocate, delay "
    "retirement, or raise contributions — the words downsize, sell, "
    "and relocate must NOT appear. Affirm the position in 2-3 "
    "sentences and stop.\n"
    "   - WEAK or MODERATE: recommend concrete improvements — primarily "
    "raising voluntary 3rd-pillar contributions, then delaying "
    "retirement, then downsizing ONLY if the property is OVERSIZED, "
    "then selling non-essential assets; relocation only as a last "
    "resort and only when WEAK.\n\n"
    "Property logic:\n"
    "- Mention downsizing ONLY for a WEAK or MODERATE outlook AND only "
    "when the home is flagged OVERSIZED; then reference how many "
    "people it suits versus a couple of 2.\n"
    "- For STRONG or EXCELLENT, do NOT suggest downsizing even if the "
    "home is large — the pension does not need it.\n"
    "- If the home is right-sized, or no property value is given, do "
    "not mention property, downsizing, or selling assets at all.\n\n"
    "Weak outlook rule:\n"
    "If outlook is WEAK, state clearly that pension may struggle to "
    "cover typical Latvian retirement living costs (~1200-1800 "
    "EUR/month for a couple, excluding debt).\n\n"
    "Relocation rule:\n"
    "Mention relocation only for WEAK outlook and only after other "
    "options are mentioned."
)


def _score(rate):
    # Replacement-rate band — delegates to the shared scorer.
    return insights.band(rate)


def _clean(text):
    # The PDF renders plain text, so strip Markdown the model may emit
    # (**bold**, headers) and collapse whitespace to one tidy paragraph.
    text = re.sub(r"\*\*|__|`", "", text)
    text = re.sub(r"(?m)^\s*#+\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _moderate(data):
    # Prefer the gathered moderate scenario; fall back to totals.
    s = (data.get("scenarios") or {}).get("moderate")
    return s if s else (data.get("totals") or {})


def _facts(data):
    # Deterministic, grounded inputs so the model can't invent numbers.
    mod = _moderate(data)
    inputs = data.get("inputs") or {}
    gross_ret = insights.salary_at_retirement(inputs)
    real = _num(mod.get("realMonthly"))
    nominal = _num(mod.get("monthly"))
    rate = insights.replacement_rate(nominal, gross_ret)
    band = _score(rate)
    capital = _num(mod.get("capital"))
    prop = _num(mod.get("propEquity"))
    prop_real = _num(mod.get("propEquityReal"))
    size = _num(inputs.get("homeSize"))
    optimal = round(size / _M2_PER_PERSON) if size > 0 else 0
    # Prefer the measured size: a home that comfortably fits more than
    # a couple is oversized. Without a size, fall back to value share.
    if size > 0:
        heavy = optimal > _COUPLE
    else:
        heavy = prop > 0 and prop >= capital and prop_real >= 150000
    return {
        "real": round(real), "nominal": round(nominal),
        "rate": rate, "band": band, "gross_ret": round(gross_ret),
        "capital": round(capital), "prop": round(prop),
        "prop_real": round(prop_real), "heavy": heavy,
        "size": round(size), "optimal": optimal,
    }


def _user_prompt(f):
    # Grounded MODERATE-scenario facts the model reasons from.
    lines = [
        "MODERATE scenario:",
        f"- Monthly pension nominal (future EUR): EUR {f['nominal']}",
        f"- Monthly pension real (today's purchasing power): "
        f"EUR {f['real']}",
        f"- Gross salary at retirement: EUR {f['gross_ret']}",
        f"- Replacement rate: {f['rate']}% of salary at retirement  "
        f"(outlook: {f['band']})",
        f"- Capital at retirement: EUR {f['capital']}",
    ]
    # At STRONG/EXCELLENT there is no shortfall, so the home is never a
    # lever — hide its size/oversized framing so no downsizing is urged.
    strong = f["band"] in ("STRONG", "EXCELLENT")
    if f["prop"] > 0 and not strong:
        flag = "OVERSIZED" if f["heavy"] else "modest"
        lines.append(
            f"- Property value at retirement: EUR {f['prop']} "
            f"(today's money EUR {f['prop_real']}) — {flag}")
    else:
        lines.append("- Property: do NOT mention property, downsizing, "
                     "or selling assets")
    if f["size"] > 0 and not strong:
        if f["heavy"]:
            lines.append(
                f"- Home: {f['size']} m2, fits about {f['optimal']} "
                f"people — LARGER than a couple of 2 needs (oversized)")
        else:
            lines.append(
                f"- Home: {f['size']} m2, fits about {f['optimal']} "
                f"people — right-sized for a couple; do NOT downsize")
    if f["band"] != "WEAK":
        lines.append("- Outlook is not WEAK — do NOT mention "
                     "relocation or moving to another country")
    return "\n".join(lines)


def generate_review(data, lang="en"):
    """Return a short AI verdict string, or None if unavailable."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        _log.warning("DeepSeek review skipped: DEEPSEEK_API_KEY not set")
        return None
    try:
        from openai import OpenAI
    except ImportError:
        _log.warning("DeepSeek review skipped: openai not installed")
        return None
    # Hard daily spend cap: once exhausted, skip the API and let the
    # PDF fall back to the deterministic verdict.
    if not ai_budget.try_consume():
        _log.warning(
            "DeepSeek review skipped: daily AI budget exhausted")
        return None

    facts = _facts(data)
    lang_name = _LANG_NAME.get(lang, "English")
    try:
        client = OpenAI(api_key=key, base_url=_API_BASE,
                        timeout=_TIMEOUT_S)
        resp = client.chat.completions.create(
            model=_MODEL, max_tokens=_MAX_TOKENS, temperature=0.1,
            messages=[
                {"role": "system",
                 "content": _SYSTEM.format(lang=lang_name)},
                {"role": "user", "content": _user_prompt(facts)},
            ],
        )
        text = _clean(resp.choices[0].message.content or "")
        return text or None
    except Exception as exc:
        _log.warning("DeepSeek review failed: %s", exc)
        return None
