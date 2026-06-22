# ai_review.py — short, cheap AI verdict for the PDF report, via the
# DeepSeek API (OpenAI-compatible). Always returns text or None; never
# raises, so a flaky API can never break the PDF download.
import os

import insights

_API_BASE = "https://api.deepseek.com"
_MODEL = "deepseek-chat"          # cheap V3 tier
# Latvian is more token-hungry than English; 220 avoids mid-sentence
# truncation while staying a fraction of a cent per report.
_MAX_TOKENS = 220
_TIMEOUT_S = 8.0

_LANG_NAME = {"lv": "Latvian", "en": "English"}

# Comfortable living space and the assumed retiring household size.
# Used to judge whether a home is larger than a couple needs.
_M2_PER_PERSON = 30
_COUPLE = 2

_SYSTEM = (
    "You are a concise retirement assistant for a Latvian pension "
    "simulator. Reply in {lang}, 2-3 short sentences, plain and "
    "specific, no legal boilerplate. Base everything on the MODERATE "
    "scenario figures given.\n"
    "- Open with a one-line verdict on the replacement rate.\n"
    "- Always recommend raising voluntary (3rd-pillar) pension "
    "contributions as the main lever to lift the rate.\n"
    "- If the property is flagged oversized, say downsizing the home "
    "could release capital to top up income. When a home size is "
    "given, reference how many people it optimally suits versus a "
    "retiring couple of two.\n"
    "- If, and only if, the outlook is WEAK, state plainly that this "
    "pension may not cover Latvian living costs and that selling "
    "assets (including the property) and relocating to a lower-cost "
    "country is an option worth considering. Otherwise do not mention "
    "relocation."
)


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
    rate = insights.replacement_rate(real, gross)
    band = insights.outlook(rate)
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
        "real": round(real), "rate": rate, "band": band,
        "capital": round(capital), "prop": round(prop),
        "prop_real": round(prop_real), "heavy": heavy,
        "size": round(size), "optimal": optimal,
    }


def _user_prompt(f):
    lines = [
        "MODERATE scenario:",
        f"- Monthly pension (today's money): EUR {f['real']}",
        f"- Replacement rate: {f['rate']}% of gross  (outlook: "
        f"{f['band'].upper()})",
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
        text = (resp.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None
