import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ai_budget
import ai_review
import rate_limit


# ── daily AI budget (spend ceiling) ────────────────────────────

def test_budget_caps_daily_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_BUDGET_FILE", str(tmp_path / "b.json"))
    monkeypatch.setenv("AI_DAILY_LIMIT", "2")
    assert ai_budget.remaining() == 2
    assert ai_budget.try_consume() is True
    assert ai_budget.try_consume() is True
    assert ai_budget.try_consume() is False          # 3rd blocked
    assert ai_budget.remaining() == 0


def test_budget_zero_disables_ai(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_BUDGET_FILE", str(tmp_path / "b.json"))
    monkeypatch.setenv("AI_DAILY_LIMIT", "0")
    assert ai_budget.try_consume() is False


def test_review_skips_when_budget_exhausted(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(ai_budget, "try_consume", lambda: False)
    # Returns None without ever calling the API.
    out = ai_review.generate_review(
        {"scenarios": {"moderate": {"realMonthly": 500}}}, "en")
    assert out is None


# ── per-IP rate limiter ────────────────────────────────────────

def test_rate_limit_blocks_after_limit():
    k = "sec-test-ip-1"
    assert all(rate_limit.allow(k, 3, 60) for _ in range(3))
    assert rate_limit.allow(k, 3, 60) is False


def test_rate_limit_window_resets(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(rate_limit.time, "time", lambda: clock[0])
    k = "sec-test-ip-2"
    assert rate_limit.allow(k, 1, 10) is True
    assert rate_limit.allow(k, 1, 10) is False
    clock[0] += 11
    assert rate_limit.allow(k, 1, 10) is True         # window rolled
