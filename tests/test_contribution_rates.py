"""The contribution split is a schedule, not a constant.

Contribution years 2025-2028 divert one point from the funded pillar to
the NDC one: 5% to the 2nd pillar and 15% to the 1st, against a
statutory base of 6% and 14%. Both pillars were hardcoded to the base,
which overstated the funded pillar and understated the state one for
every projection running through the transitional window.

Source: Valsts fondēto pensiju likums, pārejas noteikumu 40. punkts.
"""
from __future__ import annotations

import re
import subprocess

import pytest

from app import app
from calculator import calculate_p1_projection, calculate_projection
from data import (
    DATA_UPDATED, P1_RATE, P1_RATE_TRANSITIONAL, P2L_RATE,
    P2L_RATE_TRANSITIONAL, STATUTES, contribution_rates,
    historical_p2l_rate,
)

SIMPLE_SCHEDULE = [{"starts_at_age": 0, "plan_name": "Manuāla pieņēmums"}]


# ---- the schedule ----------------------------------------------------

@pytest.mark.parametrize("year,p1,p2", [
    (2024, P1_RATE, P2L_RATE),                              # before
    (2025, P1_RATE_TRANSITIONAL, P2L_RATE_TRANSITIONAL),    # first
    (2026, P1_RATE_TRANSITIONAL, P2L_RATE_TRANSITIONAL),
    (2028, P1_RATE_TRANSITIONAL, P2L_RATE_TRANSITIONAL),    # last
    (2029, P1_RATE, P2L_RATE),                              # resumes
    (2040, P1_RATE, P2L_RATE),
])
def test_the_split_by_year(year, p1, p2):
    assert contribution_rates(year) == (p1, p2)


def test_the_two_pillars_always_sum_to_twenty_percent():
    """One point moves between them; the total never changes."""
    for year in range(2020, 2041):
        assert round(sum(contribution_rates(year)), 4) == 0.20


def test_past_reconstruction_reads_the_same_schedule():
    """historical_p2l_rate is used to rebuild contributions already made.
    If it disagreed with the forward projection, the same calendar year
    would be worth two different amounts depending on which side asked.
    """
    assert historical_p2l_rate(2024) == 0.06
    assert historical_p2l_rate(2026) == P2L_RATE_TRANSITIONAL
    assert historical_p2l_rate(2029) == P2L_RATE
    # The pre-2016 table is untouched.
    assert historical_p2l_rate(2008) == 0.08
    assert historical_p2l_rate(2015) == 0.05


# ---- the projections -------------------------------------------------

def test_pillar_one_credits_fifteen_percent_during_the_window():
    # Four transitional years at 15%, then six at 14%, flat 12 000 gross.
    result = calculate_p1_projection(
        age=30, retirement_age=40, current_capital=0, gross_monthly=1000,
        salary_growth=0, revaluation_rate=0, start_year=2025)
    assert result["final_capital"] == round(12000 * (4 * 0.15 + 6 * 0.14))


def test_pillar_two_steps_back_up_in_2029():
    """A projection that starts inside the window must not carry 5% all
    the way to retirement."""
    inside = calculate_projection(
        age=60, retirement_age=65, balance=0, gross_monthly=1000,
        salary_growth=0, inflation=0, payout_years=10, apply_ceiling=True,
        plan_schedule=SIMPLE_SCHEDULE, manual_return=0, start_year=2026)
    # 2026-2028 at 5%, 2029-2030 at 6%.
    assert inside["final"]["total"] == round(12000 * (3 * 0.05 + 2 * 0.06))


def test_an_explicit_rate_still_overrides_every_year():
    """The slider sends a flat rate once the visitor moves it."""
    flat = calculate_projection(
        age=60, retirement_age=65, balance=0, gross_monthly=1000,
        salary_growth=0, inflation=0, payout_years=10, apply_ceiling=True,
        plan_schedule=SIMPLE_SCHEDULE, manual_return=0,
        p2l_rate=0.08, start_year=2026)
    assert flat["final"]["total"] == round(12000 * 5 * 0.08)


def test_the_python_and_js_schedules_agree():
    src = open("static/js/data.js", encoding="utf-8").read()
    assert "CONTRIBUTION_TRANSITION_YEARS = [2025, 2028]" in src
    assert f"P2L_RATE_TRANSITIONAL = {P2L_RATE_TRANSITIONAL}" in src
    assert f"P1_RATE_TRANSITIONAL = {P1_RATE_TRANSITIONAL}" in src
    assert f"P1_RATE: {P1_RATE}" in src
    # No module may credit a hand-written pillar rate any more.
    js = subprocess.run(
        ["git", "grep", "-n", "-E", r"const P1_RATE\s*=", "--", "static/js"],
        capture_output=True, text=True).stdout
    assert js == "", js


# ---- what the page says ----------------------------------------------

def _page(path: str = "/") -> str:
    return app.test_client().get(path).data.decode()


def test_the_slider_defaults_to_the_scheduled_rate():
    html = _page()
    m = re.search(r'id="p2lRate"[^>]*value="([\d.]+)"', html)
    assert m, "rate slider not rendered"
    assert float(m.group(1)) == contribution_rates(2026)[1] * 100


def test_the_label_names_the_transition_and_the_base():
    lv, en = _page("/"), _page("/en")
    assert "Current rate: 5% (transitional 2025-2028; statutory base 6%)" in en
    assert "pārejas periods 2025.–2028. g." in lv
    assert "since 2021" not in en


def test_the_rate_cites_the_statute_in_both_languages():
    for path, phrase in (("/", "pārejas noteikumu 40. punkts"),
                         ("/en", "pārejas noteikumu 40. punkts")):
        html = _page(path)
        assert phrase in html, path
        assert STATUTES["p2l_transition"] in html, path
        assert "likumi.lv" in html, path


def test_the_footer_stamps_when_the_data_was_checked():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA_UPDATED), DATA_UPDATED
    assert DATA_UPDATED in _page("/")
    assert "Dati atjaunoti:" in _page("/")
    assert "Data updated:" in _page("/en")
