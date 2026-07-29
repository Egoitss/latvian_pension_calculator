"""Latvian is the default locale, and the Latvian copy stays Latvian.

The interface was already fully translated when PROMPT 04 landed; what
these guard is the wording and voice, which is what actually drifts:
a new English key added to a template renders in English on the LV site
because i18n falls back rather than failing.
"""
from __future__ import annotations

import re

import yaml
from app import app


def _lv() -> dict[str, str]:
    data = yaml.safe_load(open("translations/lv.yaml")) or {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _page(path: str) -> str:
    return app.test_client().get(path).data.decode()


def test_bare_url_is_latvian_and_en_prefix_is_english():
    assert '<html lang="lv"' in _page("/")
    assert '<html lang="lv"' in _page("/loans")
    assert '<html lang="en"' in _page("/en")
    assert '<html lang="en"' in _page("/en/loans")


def test_scenario_toggle_labels():
    lv = _lv()
    assert lv["Positive"] == "Pozitīvs"
    assert lv["Moderate"] == "Mērens"
    assert lv["Negative"] == "Negatīvs"
    home = _page("/")
    for label in ("Pozitīvs", "Mērens", "Negatīvs"):
        assert label in home, label


def test_outcome_panel_labels():
    # "Nominālā / mēn." was jargon; the panel says what the number is.
    lv = _lv()
    assert lv["Monthly at retirement"] == "Mēnesī pensijā"
    assert lv["In today's money"] == "Šodienas naudā"
    home = _page("/")
    assert "Mēnesī pensijā" in home
    assert "Šodienas naudā" in home
    assert "Nominālā" not in home


def test_pdf_download_action():
    assert _lv()["Download report PDF"] == "Lejupielādēt PDF pārskatu"
    assert "Lejupielādēt PDF pārskatu" in _page("/")


def test_latvian_says_mi_never_ai():
    # Owner's rule across every OATS property: Latvian uses MI.
    offenders = [v for v in _lv().values() if re.search(r"\bAI\b", v)]
    assert not offenders, offenders


def test_latvian_addresses_the_reader_informally():
    """The interface says "tu" throughout ("Tavi dati", "Ievadi...").

    A stray formal form reads as a second voice on the same screen.
    Latvian plural imperatives end in -iet/-ieties; "Pāriet" is an
    infinitive (the skip link) and is not one.
    """
    imperative = re.compile(r"\b(\w{3,}(?:iet|ieties))\b")
    formal = {w for v in _lv().values() for w in imperative.findall(v)
              if w not in ("Pāriet", "iet")}
    assert not formal, formal
    pronouns = re.compile(r"\b(jūs|jūsu|jums)\b", re.I)
    assert not [v for v in _lv().values() if pronouns.search(v)]


def test_no_visible_english_on_the_latvian_pages():
    """A missing key falls back to English rather than erroring, so the
    only reliable check is what the page actually renders."""
    common = re.compile(
        r"\b(the|your|with|from|month|year|total|savings|salary|growth|"
        r"retirement|scenario|assumptions|download|today|money|fees)\b",
        re.I)
    for path in ("/", "/loans"):
        html = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ",
                      _page(path), flags=re.S)
        visible = [t.strip() for t in re.findall(r">([^<>]{3,90})<", html)]
        # Latvian diacritics mark a string as translated; anything with
        # English function words and none of them is a fallback.
        leaks = [t for t in visible
                 if common.search(t) and not re.search(r"[ēūīļķģšņčžā]", t)]
        assert not leaks, (path, leaks[:5])


def test_section_markers_are_mono_uppercase():
    # Matches oats.lv's .c-lbl. The markers were uppercase but set in
    # the body sans, which read as a different family beside oats.lv.
    css = open("static/css/oats-theme.css").read()
    block = css[css.index(".oats-lbl {"):css.index("@media (max-width: 480px)")]
    assert "IBM Plex Mono" in block
    assert "text-transform: uppercase" in block
    assert "letter-spacing: 0.14em" in block
    # Several markers sit in flex cells narrower than one Latvian word.
    assert "overflow-wrap: anywhere" in block
    assert _page("/").count("oats-lbl") >= 8


def test_headings_are_sentence_case():
    """oats.lv sets headings in sentence case. An ALL-CAPS or
    Title Cased heading here would read as a different site."""
    html = _page("/")
    for tag in ("h1", "h2", "h3"):
        for raw in re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S):
            text = " ".join(re.sub(r"<[^>]+>", " ", raw).split())
            if not text or not re.search(r"[a-zāēīūčģķļņšž]", text):
                continue
            assert text != text.upper(), (tag, text)
            # Every word capitalised is Title Case; allow single words
            # and any word carrying a digit or a bracket.
            words = [w for w in text.split() if len(w) > 3 and w.isalpha()]
            capped = [w for w in words if w[0].isupper()]
            assert len(capped) <= 1 or len(words) < 2, (tag, text)
