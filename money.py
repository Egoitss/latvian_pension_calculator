"""Euro formatting, one rule per locale.

The amount shown for a given number used to depend on which code path
rendered it. The server formatted #annualContribution with Python's "{:,}"
and produced "1,260 EUR" on the Latvian page, where a comma is a decimal
separator and that reads as one euro twenty-six. The browser then
recomputed the same figure through Intl.NumberFormat pinned to "lv-LV",
so the English page showed Latvian grouping.

Both sides now format here. static/js/money.js is the mirror of this
file and must produce byte-identical output; tests/test_money.py checks
the pair against the same table.

Latvian: no grouping below five digits, so "1260 EUR" stays plain and
only "105 300 EUR" is grouped, with a narrow no-break space. The comma
is reserved for decimals. The symbol trails after a no-break space.

English: ordinary thousands commas and a leading symbol, "EUR1,260".
"""
from __future__ import annotations

NARROW_NBSP = " "          # grouping separator, Latvian
NBSP = " "                 # keeps the symbol with its amount
EURO = "€"

# Latvian groups only from five digits up; English always groups.
LV_MIN_DIGITS_TO_GROUP = 5


def _group(digits: str, sep: str) -> str:
    """Insert `sep` every three digits from the right."""
    out = []
    for i, ch in enumerate(reversed(digits)):
        if i and i % 3 == 0:
            out.append(sep)
        out.append(ch)
    return "".join(reversed(out))


def _split(value: float, decimals: int) -> tuple[str, str, str]:
    """Sign, integer digits and fraction digits, already rounded."""
    sign = "-" if value < 0 else ""
    text = f"{abs(float(value)):.{decimals}f}"
    whole, _, frac = text.partition(".")
    return sign, whole, frac


def format_eur(value, lang: str = "lv", decimals: int = 0) -> str:
    """Format `value` as euros for `lang` ("lv" or "en").

    Anything unparseable formats as zero rather than raising: these are
    display strings and a template must not 500 over a bad input.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0

    sign, whole, frac = _split(number, decimals)

    if lang == "en":
        body = _group(whole, ",")
        if decimals:
            body = f"{body}.{frac}"
        return f"{sign}{EURO}{body}"

    body = whole
    if len(whole) >= LV_MIN_DIGITS_TO_GROUP:
        body = _group(whole, NARROW_NBSP)
    if decimals:
        body = f"{body},{frac}"
    return f"{sign}{body}{NBSP}{EURO}"
