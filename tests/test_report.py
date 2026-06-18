import os
import sys

# Allow importing from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml

import insights
from i18n import make_t
from report_pdf import build_report_pdf
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
    monkeypatch.setenv(
        "DOWNLOAD_COUNT_FILE", str(tmp_path / "count.json"))
    resp = _client().post("/export/pdf", json=SAMPLE)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert resp.headers["X-Download-Count"] == "1"
    assert resp.data[:5] == b"%PDF-"


def test_download_count_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DOWNLOAD_COUNT_FILE", str(tmp_path / "count.json"))
    client = _client()
    client.post("/export/pdf", json=SAMPLE)
    client.post("/lv/export/pdf", json=SAMPLE)
    assert client.get("/api/download-count").get_json()["count"] == 2
