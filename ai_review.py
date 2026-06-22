# ai_review.py — short, cheap AI verdict for the PDF report, via the
# DeepSeek API (OpenAI-compatible). Always returns text or None; never
# raises, so a flaky API can never break the PDF download.
import os
import re

import insights

_API_BASE = "https://api.deepseek.com"
_MODEL = "deepseek-chat"          # cheap V3 tier
# Latvian is more token-hungry than English; 300 avoids mid-sentence
# truncation while staying a fraction of a cent per report.
_MAX_TOKENS = 300
_TIMEOUT_S = 8.0

_LANG_NAME = {"lv": "Latvian", "en": "English"}

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
    "Replacement rate scoring:\n"
    "- <45% = WEAK\n"
    "- 45-60% = MODERATE\n"
    "- 60-75% = STRONG\n"
    "- >75% = EXCELLENT\n\n"
    "Instructions:\n"
    "1. Open with a one-line verdict based on replacement rate.\n"
    "2. Compare projected pension with inflation-adjusted purchasing "
    "power and mention inflation risk if purchasing power drops "
    "materially.\n"
    "3. Recommend the single most effective improvement action.\n\n"
    "Priority of recommendations:\n"
    "1. Increase voluntary 3rd-pillar contributions\n"
    "2. Delay retirement\n"
    "3. Downsize oversized property\n"
    "4. Sell non-essential assets\n"
    "5. Relocate to lower-cost country (last resort only)\n\n"
    "Property logic:\n"
    "- If property is flagged oversized, mention downsizing.\n"
    "- If home size is given, mention how many residents it optimally "
    "suits versus a retiring couple.\n\n"
    "Weak outlook rule:\n"
    "If outlook is WEAK, state clearly that pension may struggle to "
    "cover typical Latvian retirement living costs (~1200-1800 "
    "EUR/month for a couple, excluding debt).\n\n"
    "Relocation rule:\n"
    "Mention relocation only for WEAK outlook and only after other "
    "options are mentioned."
)


def _score(rate):
    # Replacement-rate band, matching the scoring table in _SYSTEM.
    if rate < 45:
        return "WEAK"
    if rate < 60:
        return "MODERATE"
    if rate < 75:
        return "STRONG"
    return "EXCELLENT"


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
    gross = (data.get("inputs") or {}).get("grossMonthly")
    real = _num(mod.get("realMonthly"))
    nominal = _num(mod.get("monthly"))
    rate = insights.replacement_rate(real, gross)
    band = _score(rate)
    capital = _num(mod.get("capital"))
    prop = _num(mod.get("propEquity"))
    prop_real = _num(mod.get("propEquityReal"))
    size = _num((data.get("inputs") or {}).get("homeSize"))
    optimal = round(size / _M2_PER_PERSON) if size > 0 else 0
    # Prefer the measured size: a home that comfortably fits more than
    # a couple is oversized. Without a size, fall back to value share.
    if size > 0:
        heavy = optimal > _COUPLE
    else:
        heavy = prop > 0 and prop >= capital and prop_real >= 150000
    return {
        "real": round(real), "nominal": round(nominal),
        "rate": rate, "band": band,
        "capital": round(capital), "prop": round(prop),
        "prop_real": round(prop_real), "heavy": heavy,
        "size": round(size), "optimal": optimal,
    }


def _user_prompt(f):
    lines = [
        "MODERATE scenario:",
        f"- Monthly pension nominal (future EUR): EUR {f['nominal']}",
        f"- Monthly pension real (today's purchasing power): "
        f"EUR {f['real']}",
        f"- Replacement rate: {f['rate']}% of gross  (outlook: "
        f"{f['band']})",
        f"- Capital at retirement: EUR {f['capital']}",
    ]
    if f["prop"] > 0:
        flag = "OVERSIZED" if f["heavy"] else "modest"
        lines.append(
            f"- Property value at retirement: EUR {f['prop']} "
            f"(today's money EUR {f['prop_real']}) — {flag}")
    else:
        lines.append("- Property: none entered")
    if f["size"] > 0:
        lines.append(
            f"- Home size: {f['size']} m2 — comfortably fits about "
            f"{f['optimal']} people (a retiring couple = {_COUPLE})")
    return "\n".join(lines)


def generate_review(data, lang="en"):
    """Return a short AI verdict string, or None if unavailable."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    facts = _facts(data)
    lang_name = _LANG_NAME.get(lang, "English")
    try:
        client = OpenAI(api_key=key, base_url=_API_BASE,
                        timeout=_TIMEOUT_S)
        resp = client.chat.completions.create(
            model=_MODEL, max_tokens=_MAX_TOKENS, temperature=0.3,
            messages=[
                {"role": "system",
                 "content": _SYSTEM.format(lang=lang_name)},
                {"role": "user", "content": _user_prompt(facts)},
            ],
        )
        text = _clean(resp.choices[0].message.content or "")
        return text or None
    except Exception:
        return None
