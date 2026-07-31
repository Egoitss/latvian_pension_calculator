"""The 3rd-pillar refund is capped twice, and the page says which bites.

Eligible contributions are the lower of 10% of annual gross and €4,000;
the refund is 25.5% of that. Both caps were already applied in
calculator.py and pension3.js, but the panel only ever showed the €1,020
headline, which is what a €4,000 contribution returns and is out of
reach for anyone earning under €40,000 gross a year.
"""
from __future__ import annotations

import re

import pytest

from app import app
from calculator import calculate_p3_annual_refund
from data import P3_IIN_RATE, P3_TAX_DEDUCTION_CAP, P3_TAX_DEDUCTION_RATE

# gross/month, contribution/month, expected refund, binding limit
CASES = [
    # 10% of gross is the smaller cap below €40 000 a year.
    (1500, 400, round(18000 * 0.10 * 0.255, 2), "share"),
    (2000, 400, round(24000 * 0.10 * 0.255, 2), "share"),
    # At €40 000 the two caps meet.
    (10000 / 3, 400, round(4000 * 0.255, 2), "either"),
    # Above it the €4 000 ceiling binds and the headline applies.
    (5000, 400, round(4000 * 0.255, 2), "ceiling"),
    # A small contribution is below both caps and qualifies in full.
    (5000, 100, round(1200 * 0.255, 2), "contribution"),
]


@pytest.mark.parametrize("gross,contrib,expected,_binding", CASES)
def test_the_lower_of_the_two_caps_applies(gross, contrib, expected, _binding):
    assert calculate_p3_annual_refund(gross, contrib) == pytest.approx(
        expected, abs=0.02)


def test_a_low_earner_does_not_get_the_headline_refund():
    """The bug this guards: applying only the €4,000 ceiling would pay
    €1,020 to someone on €18,000 a year, nearly twice the real figure."""
    real = calculate_p3_annual_refund(1500, 400)
    ceiling_only = round(min(400 * 12, P3_TAX_DEDUCTION_CAP) * P3_IIN_RATE, 2)
    assert real < ceiling_only
    assert real == pytest.approx(459.00, abs=0.01)
    assert ceiling_only == pytest.approx(1020.00, abs=0.01)


def test_the_cap_constants_are_the_statutory_ones():
    assert P3_TAX_DEDUCTION_RATE == 0.10
    assert P3_TAX_DEDUCTION_CAP == 4_000
    assert P3_IIN_RATE == 0.255


def test_zero_and_negative_inputs_are_safe():
    assert calculate_p3_annual_refund(0, 400) == 0
    assert calculate_p3_annual_refund(-100, -100) == 0


# ---- what the page shows ---------------------------------------------

def _page(path: str = "/") -> str:
    return app.test_client().get(path).data.decode()


def test_the_panel_has_somewhere_to_name_the_binding_limit():
    assert 'id="p3RefundBinding"' in _page()


def test_the_rule_is_explained_in_both_languages():
    en = _page("/en")
    assert "lower of 10%" in en
    assert "25.5%" in en
    lv = _page("/")
    assert "10% no bruto algas gadā" in lv
    assert "25,5%" in lv


def test_the_javascript_reports_which_limit_bound():
    """calcAnnualRefund returns the binding limit alongside the figure,
    so the panel can name it instead of asserting a headline."""
    src = open("static/js/pension3.js", encoding="utf-8").read()
    assert "binding" in src
    for key in ("share", "ceiling", "contribution"):
        assert f'{key}:' in src or f'"{key}"' in src, key
    # The mirror of the Python rule, not a second implementation of it.
    assert "TAX_DEDUCTION_RATE" in src and "TAX_DEDUCTION_CAP" in src
