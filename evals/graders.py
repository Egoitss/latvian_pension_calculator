# graders.py — code-based graders for the AI-review prompt eval.
# Each grader: (output, facts, lang) -> (status, note),
# status in {"pass", "fail", "skip"}. Skips mean "criterion N/A for
# this case" and are excluded from the score. Graders are bilingual.
import re

PASS, FAIL, SKIP = "pass", "fail", "skip"

_RELOCATE_EN = ["relocat", "lower-cost countr", "cheaper countr",
                "move abroad", "another country", "leave latvia"]
# LV: a move/cheaper word that co-occurs with a country reference, so
# "pārcelt pensionēšanos" (delay retirement) isn't a false positive.
_RELO_VERB_LV = ["pārcel", "pamest", "lētāk", "zemāk"]
_COUNTRY_LV = ["valst", "ārzem", "latvij"]


def _relocation_advice(text, lang):
    if lang == "en":
        return _has(text, _RELOCATE_EN)
    return _has(text, _RELO_VERB_LV) and _has(text, _COUNTRY_LV)
_PILLAR3 = {
    "en": ["3rd-pillar", "3rd pillar", "third pillar", "voluntary"],
    "lv": ["3. pensiju", "3. līmeņ", "3.līmeņ", "brīvprātīg",
           "trešā līmeņ", "trešo līmeņ", "trešajā līmen"],
}
# Downsizing must be PROPERTY-specific. In LV that means a "make
# smaller / sell" verb stem co-occurring with a property noun — a bare
# "samazin*" (reduce) on its own (e.g. "reduce expenses") is NOT it.
_DOWNSIZE_EN = ["downsiz", "smaller home", "smaller propert",
                "sell the home", "sell your home", "sell the propert"]
_DOWN_VERB_LV = ["mazāk", "mazin", "pārdo", "izmēr", "main"]
_PROP_NOUN_LV = ["mājokl", "īpašum"]


def _downsize_advice(text, lang):
    if lang == "en":
        return _has(text, _DOWNSIZE_EN)
    return _has(text, _DOWN_VERB_LV) and _has(text, _PROP_NOUN_LV)
_INFLATION = {
    "en": ["inflation", "purchasing power"],
    "lv": ["inflācij", "pirktspēj"],
}
_LIVING = {
    "en": ["living cost", "cost of living", "expenses",
           "cover", "1200", "1800"],
    "lv": ["izdevum", "dzīves izmaks", "iztik", "1200", "1800"],
}
_BANDS = {
    "WEAK": {"en": ["weak"], "lv": ["vāj"]},
    "MODERATE": {"en": ["moderate"], "lv": ["mēren", "vidēj"]},
    "STRONG": {"en": ["strong"], "lv": ["stipr", "spēcīg", "laba"]},
    "EXCELLENT": {"en": ["excellent"], "lv": ["izcil", "teicam"]},
}
_LV_DIACRITICS = set("āčēģīķļņōŗšūž")


def _has(text, keys):
    low = text.lower()
    return any(k in low for k in keys)


def grade_band(out, f, lang):
    # Verdict should reflect the deterministic replacement-rate band.
    want = f["band"]
    if _has(out, _BANDS[want][lang]):
        return PASS, want
    if lang == "lv":
        return SKIP, "LV band word not detected"
    return FAIL, f"missing '{want}'"


def grade_relocation(out, f, lang):
    # GUARDRAIL: relocation may appear only for a WEAK outlook.
    present = _relocation_advice(out, lang)
    if f["band"] == "WEAK":
        return PASS, "weak: allowed"
    return (FAIL, "relocation in non-weak") if present else (PASS, "—")


def grade_pillar3(out, f, lang):
    # 3rd-pillar top-ups are the primary fix for WEAK/MODERATE; for a
    # STRONG/EXCELLENT outlook improvement is optional — don't require it.
    if f["band"] in ("STRONG", "EXCELLENT"):
        return SKIP, "strong/excellent: improvement optional"
    return (PASS, "—") if _has(out, _PILLAR3[lang]) \
        else (FAIL, "no 3rd-pillar advice")


def grade_downsize(out, f, lang):
    # Oversized property → must suggest downsizing, but ONLY for a
    # WEAK/MODERATE outlook; a strong/excellent pension needs no fix.
    if not (f["heavy"] and f["prop"] > 0):
        return SKIP, "not oversized"
    if f["band"] in ("STRONG", "EXCELLENT"):
        return SKIP, "strong/excellent: downsizing not required"
    return (PASS, "—") if _downsize_advice(out, lang) \
        else (FAIL, "no downsizing advice")


def grade_no_overadvice(out, f, lang):
    # GUARDRAIL: a STRONG/EXCELLENT outlook must NOT be told to downsize —
    # pushing a "fix" when there is no shortfall contradicts the verdict.
    if f["band"] not in ("STRONG", "EXCELLENT"):
        return SKIP, "not strong/excellent"
    return (FAIL, "downsizing pushed at strong/excellent") \
        if _downsize_advice(out, lang) else (PASS, "—")


def grade_no_phantom(out, f, lang):
    # No property entered → must not invent downsizing advice.
    if f["prop"] > 0 or f["size"] > 0:
        return SKIP, "property present"
    return (FAIL, "phantom downsizing") if _downsize_advice(out, lang) \
        else (PASS, "—")


def grade_no_downsize_rightsized(out, f, lang):
    # Home sized for a couple (size given, not oversized) → no
    # downsizing advice (the "optimal for 1-2, not a couple" bug).
    if f["size"] <= 0 or f["heavy"]:
        return SKIP, "not a right-sized case"
    return (FAIL, "downsizing a right-sized home") \
        if _downsize_advice(out, lang) else (PASS, "—")


def grade_size(out, f, lang):
    # Reference size/occupancy only when the home is oversized AND the
    # outlook is WEAK/MODERATE — at strong/excellent the home isn't
    # discussed, and for a right-sized home the m² is just noise.
    if (f["size"] <= 0 or not f["heavy"]
            or f["band"] in ("STRONG", "EXCELLENT")):
        return SKIP, "size not actionable"
    refs = [str(f["size"]), "m²", "m2", "people", "person",
            "cilvēk", "residents", "iedzīvotāj"]
    return (PASS, "—") if _has(out, refs) else (FAIL, "size not referenced")


def grade_inflation(out, f, lang):
    # Material erosion (real << nominal) → mention inflation risk.
    if f["nominal"] <= 0 or f["real"] >= 0.85 * f["nominal"]:
        return SKIP, "no material erosion"
    return (PASS, "—") if _has(out, _INFLATION[lang]) \
        else (FAIL, "no inflation note")


def grade_living(out, f, lang):
    # WEAK outlook → flag Latvian living-cost shortfall.
    if f["band"] != "WEAK":
        return SKIP, "not weak"
    return (PASS, "—") if _has(out, _LIVING[lang]) \
        else (FAIL, "no living-cost note")


def grade_language(out, f, lang):
    # Output must be in the requested language.
    has_lv = any(ch in _LV_DIACRITICS for ch in out.lower())
    if lang == "lv":
        return (PASS, "—") if has_lv else (FAIL, "not Latvian")
    return (FAIL, "Latvian chars in EN") if has_lv else (PASS, "—")


def grade_no_markdown(out, f, lang):
    # Plain text only — no Markdown reaches the PDF.
    bad = re.search(r"\*\*|__|`", out) or re.search(r"(?m)^\s*#+\s", out)
    return (FAIL, "markdown present") if bad else (PASS, "—")


def grade_not_truncated(out, f, lang):
    # Must end on terminal punctuation (no mid-sentence cut-off).
    return (PASS, "—") if out.rstrip().endswith((".", "!", "?", "…")) \
        else (FAIL, "looks truncated")


def grade_length(out, f, lang):
    # Concise: 2-3 short sentences ≈ ≤ 80 words.
    n = len(out.split())
    return (PASS, f"{n}w") if n <= 80 else (FAIL, f"{n}w > 80")
