import os
import sys
import types

# Allow importing from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml

import ai_review
import insights
from i18n import make_t
from report_pdf import build_report_pdf, render_report_html
import app as app_module


SAMPLE = {
    "inputs": {
        "age": 30, "retirementAge": 65,
        "grossMonthly": 1750, "scenario": "negative",
    },
    "pillars": {
        "p1": {"monthly": 820, "capital": 242000},
        "p2": {"monthly": 410, "capital": 139000},
        "p3": {"monthly": 150, "capital": 42000},
    },
    "totals": {
        "monthly": 1380, "realMonthly": 690,
        "capital": 423000, "realCapital": 205000,
    },
}


# ── insights (deterministic, no AI) ────────────────────────────

def test_replacement_rate_basis_is_gross():
    assert insights.replacement_rate(700, 1750) == 40.0
    assert insights.replacement_rate(700, 0) == 0.0


def test_outlook_bands():
    assert insights.outlook(75) == "strong"
    assert insights.outlook(60) == "strong"
    assert insights.outlook(59.9) == "moderate"
    assert insights.outlook(40) == "moderate"
    assert insights.outlook(39.9) == "weak"


def test_inflation_erosion():
    assert insights.inflation_erosion(1000, 600) == 40.0
    assert insights.inflation_erosion(0, 0) == 0.0


def test_market_share_and_risk():
    assert insights.market_share(SAMPLE["pillars"]) == \
        round(560 / 1380 * 100, 1)
    assert insights.risk_level(SAMPLE["pillars"]) == "moderate"
    heavy = {"p1": {"monthly": 100}, "p2": {"monthly": 500},
             "p3": {"monthly": 400}}
    assert insights.risk_level(heavy) == "higher"


def test_summarize_shape():
    s = insights.summarize(SAMPLE)
    assert s["outlook"] == "weak"        # 39.4% < 40
    assert s["replacement_rate"] == 39.4


# ── PDF builder ────────────────────────────────────────────────

def test_build_pdf_returns_pdf_bytes():
    pdf = build_report_pdf(SAMPLE, make_t("en"), "2026-06-18")
    assert pdf[:5] == b"%PDF-" and len(pdf) > 3000


def test_build_pdf_latvian():
    pdf = build_report_pdf(SAMPLE, make_t("lv"), "2026-06-18")
    assert pdf[:5] == b"%PDF-"


def test_build_pdf_empty_payload_is_safe():
    pdf = build_report_pdf({}, make_t("en"), "2026-06-18")
    assert pdf[:5] == b"%PDF-"


# ── property (opt-in) inclusion in scenario cards ──────────────

def test_scenarios_include_property_when_entered():
    import report_pdf
    data = dict(SAMPLE, activeScenario="moderate", scenarios={
        "negative": {"realMonthly": 600, "capital": 250000,
                     "propEquity": 90000},
        "moderate": {"realMonthly": 900, "capital": 400000,
                     "propEquity": 230000},
        "positive": {"realMonthly": 1200, "capital": 560000,
                     "propEquity": 310000},
    })
    cards = report_pdf._scenarios(make_t("en"), data)
    assert [c["property"] for c in cards] == \
        ["€ 90000", "€ 230000", "€ 310000"]


def test_scenarios_omit_property_when_absent():
    import report_pdf
    data = dict(SAMPLE, activeScenario="moderate", scenarios={
        "negative": {"realMonthly": 600, "capital": 250000},
        "moderate": {"realMonthly": 900, "capital": 400000},
        "positive": {"realMonthly": 1200, "capital": 560000},
    })
    cards = report_pdf._scenarios(make_t("en"), data)
    assert all(c["property"] is None for c in cards)


# ── route + counter ────────────────────────────────────────────

def test_lv_yaml_parses():
    path = os.path.join(
        os.path.dirname(__file__), "..", "translations", "lv.yaml")
    data = yaml.safe_load(open(path, encoding="utf-8"))
    assert data["Pension Scenario Report"] == "Pensijas scenāriju pārskats"


def _client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_export_pdf_route(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)  # no network
    monkeypatch.setenv(
        "DOWNLOAD_COUNT_FILE", str(tmp_path / "count.json"))
    resp = _client().post("/export/pdf", json=SAMPLE)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert resp.headers["X-Download-Count"] == "1"
    assert resp.data[:5] == b"%PDF-"


def test_download_count_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)  # no network
    monkeypatch.setenv(
        "DOWNLOAD_COUNT_FILE", str(tmp_path / "count.json"))
    client = _client()
    client.post("/export/pdf", json=SAMPLE)
    client.post("/lv/export/pdf", json=SAMPLE)
    assert client.get("/api/download-count").get_json()["count"] == 2


# ── AI review (DeepSeek) — mocked, no real network ─────────────

AI_DATA = dict(SAMPLE, scenarios={
    "moderate": {"realMonthly": 700, "capital": 200000,
                 "propEquity": 300000, "propEquityReal": 220000},
})


def _fake_openai(reply, captured):
    """Return a stand-in openai.OpenAI capturing the create() kwargs."""
    def create(**kw):
        captured.update(kw)
        msg = types.SimpleNamespace(content=reply)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=msg)])
    chat = types.SimpleNamespace(
        completions=types.SimpleNamespace(create=create))
    return lambda **kw: types.SimpleNamespace(chat=chat)


def test_generate_review_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert ai_review.generate_review(AI_DATA, "en") is None


def test_generate_review_uses_moderate_and_flags_property(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    captured = {}
    import openai
    monkeypatch.setattr(
        openai, "OpenAI", _fake_openai("Looks weak.", captured))
    out = ai_review.generate_review(AI_DATA, "en")
    assert out == "Looks weak."
    user_msg = captured["messages"][-1]["content"]
    assert "MODERATE" in user_msg          # based on moderate scenario
    assert "OVERSIZED" in user_msg         # 300k prop ≥ 200k capital
    assert captured["model"] == "deepseek-chat"
    assert captured["max_tokens"] <= 320   # short / cheap


def test_clean_strips_markdown_and_whitespace():
    raw = "**Verdict:** WEAK\n\nRisk: inflation __erodes__ `value`."
    out = ai_review._clean(raw)
    assert "*" not in out and "_" not in out and "`" not in out
    assert "\n" not in out
    assert out == "Verdict: WEAK Risk: inflation erodes value."


def test_home_size_drives_oversized_flag():
    # 120 m² → fits ~4 people → oversized for a couple.
    big = dict(AI_DATA, inputs=dict(AI_DATA["inputs"], homeSize=120))
    f = ai_review._facts(big)
    assert f["optimal"] == 4 and f["heavy"] is True
    # 60 m² → fits ~2 → right-sized for a couple.
    small = dict(AI_DATA, inputs=dict(AI_DATA["inputs"], homeSize=60))
    f2 = ai_review._facts(small)
    assert f2["optimal"] == 2 and f2["heavy"] is False


def test_home_size_appears_in_prompt(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    captured = {}
    import openai
    monkeypatch.setattr(
        openai, "OpenAI", _fake_openai("ok", captured))
    data = dict(AI_DATA, inputs=dict(AI_DATA["inputs"], homeSize=120))
    ai_review.generate_review(data, "en")
    user_msg = captured["messages"][-1]["content"]
    assert "120 m2" in user_msg and "about 4 people" in user_msg


def test_generate_review_swallows_api_errors(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    def boom(**kw):
        raise RuntimeError("network down")
    import openai
    monkeypatch.setattr(openai, "OpenAI", boom)
    assert ai_review.generate_review(AI_DATA, "en") is None


# ── AI box rendering in the report ─────────────────────────────

def test_report_html_shows_ai_box_when_present():
    html = render_report_html(
        SAMPLE, make_t("en"), "2026-06-22", ai_review="Consider downsizing.")
    assert "Consider downsizing." in html
    assert 'class="ai-review"' in html and "Consider downsizing." in html
    assert "ai-badge" in html               # DeepSeek badge rendered
    # AI prose replaces the deterministic verdict sentence (SAMPLE=weak).
    assert "voluntary saving" not in html


def test_report_html_falls_back_without_ai():
    html = render_report_html(SAMPLE, make_t("en"), "2026-06-22")
    assert 'class="ai-review"' not in html   # no AI box
    # Deterministic verdict still present (SAMPLE outlook is weak).
    assert "voluntary saving" in html
