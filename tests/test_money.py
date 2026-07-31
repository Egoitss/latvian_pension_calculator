"""One euro format per locale, and the two implementations agree.

The server rendered #annualContribution with Python's "{:,}" and the
browser recomputed it through Intl.NumberFormat pinned to "lv-LV". So
the Latvian page showed "1,260 €", where a comma is a decimal separator,
and the English page showed Latvian grouping.

money.py and static/js/money.js are mirrors. The table below is checked
against both, so the pair cannot drift.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from app import app
from money import format_eur

NARROW_NBSP = " "
NBSP = " "

# value, lang, decimals, expected
CASES = [
    (0, "lv", 0, f"0{NBSP}€"),
    (7, "lv", 0, f"7{NBSP}€"),
    (999, "lv", 0, f"999{NBSP}€"),
    # Four digits stay plain: "1 260" would invite reading the space as
    # a separator, and "1,260" reads as one euro twenty-six in Latvian.
    (1260, "lv", 0, f"1260{NBSP}€"),
    (9999, "lv", 0, f"9999{NBSP}€"),
    # Five digits and up group with a narrow no-break space.
    (10000, "lv", 0, f"10{NARROW_NBSP}000{NBSP}€"),
    (105300, "lv", 0, f"105{NARROW_NBSP}300{NBSP}€"),
    (1234567, "lv", 0, f"1{NARROW_NBSP}234{NARROW_NBSP}567{NBSP}€"),
    (-2500, "lv", 0, f"-2500{NBSP}€"),
    # The comma is the decimal separator, never a group separator.
    (1260.5, "lv", 2, f"1260,50{NBSP}€"),
    (105300.25, "lv", 2, f"105{NARROW_NBSP}300,25{NBSP}€"),
    # English: leading symbol, ordinary thousands commas throughout.
    (0, "en", 0, "€0"),
    (999, "en", 0, "€999"),
    (1260, "en", 0, "€1,260"),
    (105300, "en", 0, "€105,300"),
    (-2500, "en", 0, "-€2,500"),
    (1260.5, "en", 2, "€1,260.50"),
]


@pytest.mark.parametrize("value,lang,decimals,expected", CASES)
def test_python_formatter(value, lang, decimals, expected):
    assert format_eur(value, lang, decimals) == expected


def test_bad_input_formats_as_zero():
    """A template must not 500 over an unparseable figure."""
    assert format_eur(None, "lv") == f"0{NBSP}€"
    assert format_eur("", "en") == "€0"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_the_javascript_mirror_agrees():
    """Same table through static/js/money.js."""
    cases = json.dumps([[v, lang, d] for v, lang, d, _ in CASES])
    script = f"""
      import {{ formatEur }} from './static/js/money.js';
      const out = {cases}.map(([v, lang, decimals]) =>
        formatEur(v, {{ decimals, lang }}));
      console.log(JSON.stringify(out));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True, cwd=".")
    assert proc.returncode == 0, proc.stderr
    got = json.loads(proc.stdout)
    for (value, lang, decimals, expected), actual in zip(CASES, got):
        assert actual == expected, (value, lang, decimals, actual, expected)


# ---- the rendered page ----------------------------------------------

def _page(path: str) -> str:
    return app.test_client().get(path).data.decode()


def _contribution(html: str) -> str:
    m = re.search(r'id="annualContribution"[^>]*>(.*?)</span>', html, re.S)
    assert m, "annualContribution not rendered"
    return " ".join(m.group(1).split())


def test_the_server_no_longer_emits_a_latvian_thousands_comma():
    lv = _contribution(_page("/"))
    assert "," not in lv, lv
    assert lv.endswith("€")


def test_the_english_page_uses_english_grouping():
    en = _contribution(_page("/en"))
    assert en.startswith("€"), en


def test_no_module_pins_a_locale_by_hand():
    """Six modules each carried their own Intl.NumberFormat("lv-LV").

    Comments are stripped first: money.js names the old call in its own
    header to explain what it replaced.
    """
    files = subprocess.run(
        ["git", "grep", "-l", "-E", "lv-LV|en-US", "--", "static/js"],
        capture_output=True, text=True).stdout.split()
    offenders = []
    for path in files:
        src = open(path, encoding="utf-8").read()
        code = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
        if re.search(r"lv-LV|en-US", code):
            offenders.append(path)
    assert offenders == [], offenders
