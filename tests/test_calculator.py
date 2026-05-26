import sys
import os

# Allow importing from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data import DEFAULT_RETURN, VSAOI_CEILING, P2L_RATE
from calculator import (
    get_annual_return,
    should_apply_vsaoi_ceiling,
    calculate_projection,
    build_plan_schedule,
    calculate_p3_annual_refund,
    calculate_p3_projection,
    bootstrap_scenario_returns,
)

# Default schedule used by simple projection tests
SIMPLE_SCHEDULE = [{"starts_at_age": 0, "plan_name": "Manuāls pieņēmums"}]


class TestGetAnnualReturn:
    # Tests for plan return resolution logic

    def test_real_plan_uses_return_5y(self):
        plan = {"name": "Test", "return_5y": 6.24}
        assert get_annual_return(plan, 99) == 6.24

    def test_real_plan_falls_back_to_return_3y(self):
        plan = {"name": "Test", "return_3y": 5.0}
        assert get_annual_return(plan, 99) == 5.0

    def test_benchmark_uses_assumption_return(self):
        plan = {"benchmark": True, "assumption_return": 10.0}
        assert get_annual_return(plan, 0) == 10.0

    def test_manual_plan_uses_manual_return(self):
        plan = {"manual": True}
        assert get_annual_return(plan, 7.5) == 7.5

    def test_none_plan_returns_default(self):
        assert get_annual_return(None, None) == DEFAULT_RETURN


class TestVsaoiCeiling:
    # Tests for automatic VSAOI ceiling detection

    def test_off_when_below_ceiling(self):
        # 8000/mo * 12 = 96000 < 105300
        assert not should_apply_vsaoi_ceiling(35, 65, 8000, 0)

    def test_on_when_above_ceiling(self):
        # 9800/mo * 12 = 117600 > 105300
        assert should_apply_vsaoi_ceiling(35, 65, 9800, 0)

    def test_on_when_growth_crosses_ceiling(self):
        # 7000/mo grows to exceed ceiling before age 65
        assert should_apply_vsaoi_ceiling(35, 65, 7000, 3)


class TestCalculateProjection:
    # Tests for year-by-year accumulation logic

    def test_one_year_zero_return(self):
        # 1000 balance + 6% of 1000*12 annual gross = 1000 + 720 = 1720
        result = calculate_projection(
            age=64, retirement_age=65, balance=1000,
            gross_monthly=1000, salary_growth=0,
            inflation=0, payout_years=10,
            apply_ceiling=True,
            plan_schedule=SIMPLE_SCHEDULE,
            manual_return=0,
        )
        assert result["final"]["total"] == 1720

    def test_vsaoi_ceiling_caps_contribution(self):
        # Gross 20000/mo far exceeds ceiling — contribution capped at ceiling*rate
        result = calculate_projection(
            age=64, retirement_age=65, balance=0,
            gross_monthly=20000, salary_growth=0,
            inflation=0, payout_years=10,
            apply_ceiling=True,
            plan_schedule=SIMPLE_SCHEDULE,
            manual_return=0,
        )
        expected = round(VSAOI_CEILING * P2L_RATE)
        assert result["final"]["total"] == expected

    def test_pension_tax_above_threshold(self):
        # Large balance produces monthly payout well above tax-free threshold
        result = calculate_projection(
            age=35, retirement_age=36, balance=720000,
            gross_monthly=0, salary_growth=0,
            inflation=0, payout_years=18,
            apply_ceiling=False,
            plan_schedule=SIMPLE_SCHEDULE,
            manual_return=0,
        )
        assert result["monthly_tax"] > 0

    def test_zero_balance_zero_contribution_stays_zero(self):
        result = calculate_projection(
            age=64, retirement_age=65, balance=0,
            gross_monthly=0, salary_growth=0,
            inflation=0, payout_years=10,
            apply_ceiling=False,
            plan_schedule=SIMPLE_SCHEDULE,
            manual_return=0,
        )
        assert result["final"]["total"] == 0


class TestBuildPlanSchedule:
    # Tests for plan-switch schedule construction

    def test_no_switching_returns_single_entry(self):
        schedule = build_plan_schedule(
            age=30, retirement_age=65,
            selected_plan_name="Plan A", manual_return=8,
            enable_switching=False,
            switch_one_age=50, switch_one_plan_name="Plan B",
            switch_two_age=60, switch_two_plan_name="Plan C",
        )
        assert len(schedule) == 1
        assert schedule[0]["plan_name"] == "Plan A"

    def test_switching_adds_two_entries(self):
        schedule = build_plan_schedule(
            age=30, retirement_age=65,
            selected_plan_name="Plan A", manual_return=8,
            enable_switching=True,
            switch_one_age=50, switch_one_plan_name="Plan B",
            switch_two_age=60, switch_two_plan_name="Plan C",
        )
        assert len(schedule) == 3
        ages = [e["starts_at_age"] for e in schedule]
        assert ages == sorted(ages)


class TestP1Pension:
    def test_monthly_pension_formula_age_65(self):
        from calculator import monthly_p1_pension
        result = monthly_p1_pension(100_000, 17.24)
        expected = 100_000 / (17.24 * 12)
        assert abs(result - expected) < 0.01

    def test_monthly_pension_zero_g_returns_zero(self):
        from calculator import monthly_p1_pension
        assert monthly_p1_pension(100_000, 0) == 0.0

    def test_p1_projection_one_year_no_growth(self):
        from calculator import calculate_p1_projection
        # capital = 10_000 × 1.0 + min(12_000, 105_300) × 0.14 = 11_680
        result = calculate_p1_projection(
            age=64, retirement_age=65,
            current_capital=10_000, gross_monthly=1_000,
            salary_growth=0, revaluation_rate=0, p1_rate=0.14,
        )
        assert result["final_capital"] == 11_680

    def test_p1_projection_vsaoi_ceiling_caps_contribution(self):
        from calculator import calculate_p1_projection
        # gross 20_000/mo × 12 = 240_000 > ceiling 105_300
        result = calculate_p1_projection(
            age=64, retirement_age=65,
            current_capital=0, gross_monthly=20_000,
            salary_growth=0, revaluation_rate=0, p1_rate=0.14,
        )
        assert result["final_capital"] == round(105_300 * 0.14)

    def test_p1_projection_revaluation_applied(self):
        from calculator import calculate_p1_projection
        # 0 contributions, 10% revaluation: 10_000 × 1.1 = 11_000
        result = calculate_p1_projection(
            age=64, retirement_age=65,
            current_capital=10_000, gross_monthly=0,
            salary_growth=0, revaluation_rate=10.0, p1_rate=0.14,
        )
        assert result["final_capital"] == 11_000

    def test_p1_projection_zero_years_returns_current_capital(self):
        from calculator import calculate_p1_projection
        result = calculate_p1_projection(
            age=65, retirement_age=65,
            current_capital=50_000, gross_monthly=2_000,
            salary_growth=0, revaluation_rate=5.0, p1_rate=0.14,
        )
        assert result["final_capital"] == 50_000
        assert result["years"] == 0


class TestGetGCoefficient:
    def test_known_age_65_returns_exact(self):
        from data import get_g_coefficient
        assert get_g_coefficient(65) == 17.24

    def test_known_age_63_returns_exact(self):
        from data import get_g_coefficient
        assert get_g_coefficient(63) == 19.5

    def test_clamps_below_minimum(self):
        from data import get_g_coefficient
        assert get_g_coefficient(55) == get_g_coefficient(60)

    def test_clamps_above_maximum(self):
        from data import get_g_coefficient
        assert get_g_coefficient(75) == get_g_coefficient(70)


class TestCalculateP3AnnualRefund:
    def test_basic_refund(self):
        # €27.5/month = €330/yr contrib; gross €1830/month = €21960/yr
        # eligible = min(330, min(21960*0.10, 4000)) = min(330, 2196) = 330
        # refund = 330 * 0.255 = 84.15
        result = calculate_p3_annual_refund(1830, 27.5)
        assert result == 84.15

    def test_refund_capped_at_4000_eur(self):
        # High earner: gross 5000/m = 60000/yr; 10% = 6000 > cap 4000
        # contrib 500/m = 6000/yr > cap 4000; eligible = 4000
        # refund = 4000 * 0.255 = 1020.0
        result = calculate_p3_annual_refund(5000, 500)
        assert result == 1020.0

    def test_refund_capped_by_gross_pct(self):
        # Low earner: gross 800/m = 9600/yr; 10% = 960
        # contrib 200/m = 2400/yr > 960; eligible = 960
        # refund = 960 * 0.255 = 244.80
        result = calculate_p3_annual_refund(800, 200)
        assert result == 244.80

    def test_zero_contribution_no_refund(self):
        assert calculate_p3_annual_refund(2000, 0) == 0.0

    def test_zero_gross_no_refund(self):
        assert calculate_p3_annual_refund(0, 100) == 0.0


class TestCalculateP3Projection:
    def test_zero_years_returns_current_balance(self):
        result = calculate_p3_projection(
            age=65, retirement_age=65, current_balance=5000,
            gross_monthly=1830, monthly_contribution=27.5,
            contribution_growth=5.0, plan_return=9.2, inflation=4.0,
        )
        assert result["final_balance"] == 5000.0
        assert result["years"] == 0

    def test_one_year_growth(self):
        # balance=1000, monthly=100, annual=1200, return=10%
        # final = 1000*1.10 + 1200 = 1100 + 1200 = 2300
        result = calculate_p3_projection(
            age=64, retirement_age=65, current_balance=1000,
            gross_monthly=2000, monthly_contribution=100,
            contribution_growth=0.0, plan_return=10.0, inflation=0.0,
        )
        assert result["final_balance"] == 2300.0
        assert result["years"] == 1

    def test_gains_and_tax_calculation(self):
        # invested = 1000 + 1200 = 2200, gains = 2300-2200 = 100
        # tax_on_gains = 100 * 0.255 = 25.5, net = 2300 - 25.5 = 2274.5
        result = calculate_p3_projection(
            age=64, retirement_age=65, current_balance=1000,
            gross_monthly=2000, monthly_contribution=100,
            contribution_growth=0.0, plan_return=10.0, inflation=0.0,
        )
        assert result["gains"] == 100.0
        assert result["tax_on_gains"] == 25.5
        assert result["net_payout"] == 2274.5

    def test_real_value_deflated(self):
        # 1 year, 10% return, 4% inflation: real = 2300 / 1.04
        result = calculate_p3_projection(
            age=64, retirement_age=65, current_balance=1000,
            gross_monthly=2000, monthly_contribution=100,
            contribution_growth=0.0, plan_return=10.0, inflation=4.0,
        )
        expected_real = round(2300 / 1.04, 2)
        assert result["real_balance"] == expected_real

    def test_longer_projection_grows_balance(self):
        result = calculate_p3_projection(
            age=43, retirement_age=63, current_balance=5175.94,
            gross_monthly=1830, monthly_contribution=27.5,
            contribution_growth=5.0, plan_return=9.2, inflation=4.0,
        )
        assert result["final_balance"] > 50_000
        assert result["years"] == 20
        assert result["real_balance"] < result["final_balance"]


class TestBootstrapScenarioReturns:
    def test_returns_three_keys(self):
        result = bootstrap_scenario_returns(num_months=12, seed=0)
        assert set(result.keys()) == {"positive", "moderate", "negative"}

    def test_ordering_negative_lt_moderate_lt_positive(self):
        result = bootstrap_scenario_returns(num_months=120, seed=0)
        assert result["negative"] < result["moderate"] < result["positive"]

    def test_rates_are_positive_and_bounded(self):
        # Dinamika has a strong positive long-run mean → all pcts positive
        result = bootstrap_scenario_returns(num_months=264, seed=42)
        assert result["negative"] > 0
        assert result["positive"] < 30

    def test_seeded_is_reproducible(self):
        r1 = bootstrap_scenario_returns(num_months=60, seed=7)
        r2 = bootstrap_scenario_returns(num_months=60, seed=7)
        assert r1 == r2

    def test_short_horizon_has_wider_spread_than_long(self):
        short = bootstrap_scenario_returns(num_months=12, seed=0)
        long_ = bootstrap_scenario_returns(num_months=240, seed=0)
        assert (short["positive"] - short["negative"]) > \
               (long_["positive"] - long_["negative"])
