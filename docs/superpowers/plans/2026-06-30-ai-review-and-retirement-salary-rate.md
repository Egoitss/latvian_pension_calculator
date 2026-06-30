# AI Review + Salary-at-Retirement Rate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the DeepSeek AI review render on live, and recompute
the replacement rate against the projected salary-at-retirement
(with recalibrated outlook bands) consistently across the PDF report.

**Architecture:** Consolidate band thresholds + the replacement-rate
basis into `insights.py` (one source of truth); `ai_review.py` and
`report_pdf.py` consume them. Surface the salary-at-retirement the
JS engine already computes (`calc.js` → `ui.js` → `export.js`) into
the export payload. Add warning-logs so a skipped AI review is
diagnosable. Workstream A's live fix is an operational `.env` update.

**Tech Stack:** Python 3.12, Flask, Jinja2, pytest; vanilla ES
modules; DeepSeek via the `openai` client; Docker + Caddy on the VPS.

## Global Constraints

- ≤300 lines/file, ≤50 lines/function, ≤80 chars/line.
- Every function opens with a comment describing what it does.
- Replacement rate = **nominal** pension ÷ **nominal** salary at
  retirement (both future EUR).
- Band thresholds live ONLY in `insights.py`; no duplication.
- EN source strings changed in templates require a matching LV entry
  in `translations/lv.yaml` (English text → Latvian text).
- Run from repo root with the venv: `source .venv/bin/activate`.

---

### Task 1: insights.py — new bands + retirement-salary basis

**Files:**
- Modify: `insights.py`
- Test: `tests/test_report.py` (the insights section)

**Interfaces:**
- Produces: `WEAK_MAX=20.0`, `MODERATE_MAX=30.0`, `STRONG_MAX=45.0`;
  `band(rate) -> "WEAK"|"MODERATE"|"STRONG"|"EXCELLENT"`;
  `salary_at_retirement(inputs) -> float`; `outlook(rate)` rebanded;
  `summarize(data)` now uses nominal pension ÷ salary-at-retirement.

- [ ] **Step 1: Update the failing tests** — replace `test_outlook_bands`
in `tests/test_report.py` and add three tests:

```python
def test_outlook_bands():
    assert insights.outlook(45) == "strong"
    assert insights.outlook(30) == "strong"
    assert insights.outlook(29.9) == "moderate"
    assert insights.outlook(20) == "moderate"
    assert insights.outlook(19.9) == "weak"


def test_band_four_way():
    assert insights.band(19.9) == "WEAK"
    assert insights.band(20) == "MODERATE"
    assert insights.band(29.9) == "MODERATE"
    assert insights.band(30) == "STRONG"
    assert insights.band(44.9) == "STRONG"
    assert insights.band(45) == "EXCELLENT"


def test_salary_at_retirement_prefers_projected():
    assert insights.salary_at_retirement(
        {"grossMonthly": 1750, "grossAtRetirement": 9000}) == 9000
    assert insights.salary_at_retirement({"grossMonthly": 1750}) == 1750
    assert insights.salary_at_retirement({}) == 0.0


def test_summarize_rate_uses_retirement_salary():
    data = {
        "totals": {"monthly": 1800, "realMonthly": 900},
        "inputs": {"grossMonthly": 1750, "grossAtRetirement": 9000},
        "pillars": {},
    }
    assert insights.summarize(data)["replacement_rate"] == 20.0
    assert insights.summarize(data)["outlook"] == "moderate"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_report.py -k "outlook_bands or band_four or
salary_at_retirement or summarize_rate" -v`
Expected: FAIL (`band` / `salary_at_retirement` undefined).

- [ ] **Step 3: Edit `insights.py`** — replace the two threshold
constants (lines 6-7) with three, and update/add functions:

```python
# Replacement-rate bands, % of gross salary AT RETIREMENT. Tunable;
# single source of truth — ai_review imports these for its prompt.
WEAK_MAX = 20.0       # rate < WEAK_MAX             -> weak
MODERATE_MAX = 30.0   # WEAK_MAX <= rate < MOD_MAX  -> moderate
STRONG_MAX = 45.0     # MOD_MAX <= rate < STRONG    -> strong; >= excellent
```

Update `replacement_rate`'s comment and `outlook`, and add two
functions:

```python
def replacement_rate(pension_monthly, salary_monthly):
    # Nominal pension as a % of gross salary at retirement.
    salary = _num(salary_monthly)
    if salary <= 0:
        return 0.0
    return round(_num(pension_monthly) / salary * 100, 1)


def outlook(rate):
    # Band the replacement rate into strong / moderate / weak.
    if rate >= MODERATE_MAX:
        return "strong"
    if rate >= WEAK_MAX:
        return "moderate"
    return "weak"


def band(rate):
    # Four-way band (adds EXCELLENT) used by the AI prompt + verdict.
    if rate < WEAK_MAX:
        return "WEAK"
    if rate < MODERATE_MAX:
        return "MODERATE"
    if rate < STRONG_MAX:
        return "STRONG"
    return "EXCELLENT"


def salary_at_retirement(inputs):
    # Projected gross monthly salary at retirement; fall back to the
    # current salary when the projected value is absent (old payloads).
    data = inputs or {}
    projected = _num(data.get("grossAtRetirement"))
    return projected if projected > 0 else _num(data.get("grossMonthly"))
```

In `summarize`, change the rate line to:

```python
    rate = replacement_rate(
        totals.get("monthly"), salary_at_retirement(inputs))
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_report.py -v`
Expected: PASS (the pre-existing `test_replacement_rate_basis_is_gross`
still passes — `replacement_rate(700, 1750) == 40.0`).

- [ ] **Step 5: Commit**

```bash
git add insights.py tests/test_report.py
git commit -m "feat(insights): rebanded replacement rate vs salary at retirement"
```

---

### Task 2: ai_review.py — new basis, shared bands, logging

**Files:**
- Modify: `ai_review.py`
- Test: `tests/test_report.py` (the ai_review section)

**Interfaces:**
- Consumes: `insights.WEAK_MAX/MODERATE_MAX/STRONG_MAX`,
  `insights.band`, `insights.salary_at_retirement`,
  `insights.replacement_rate` (Task 1).
- Produces: `_facts(data)` dict gains `gross_ret`; `_SYSTEM` scoring
  table generated from constants; `generate_review` logs why it skips.

- [ ] **Step 1: Write the failing tests** — add to `tests/test_report.py`:

```python
def test_facts_rate_uses_retirement_salary():
    data = {
        "scenarios": {"moderate": {"monthly": 1800, "realMonthly": 900,
                                   "capital": 200000}},
        "inputs": {"grossMonthly": 1750, "grossAtRetirement": 9000},
    }
    f = ai_review._facts(data)
    assert f["gross_ret"] == 9000
    assert f["rate"] == 20.0          # 1800 / 9000
    assert f["band"] == "MODERATE"


def test_user_prompt_mentions_retirement_salary():
    data = {
        "scenarios": {"moderate": {"monthly": 1800, "realMonthly": 900,
                                   "capital": 200000}},
        "inputs": {"grossMonthly": 1750, "grossAtRetirement": 9000},
    }
    prompt = ai_review._user_prompt(ai_review._facts(data))
    assert "salary at retirement" in prompt
    assert "9000" in prompt


def test_scoring_table_matches_constants():
    assert f"<{insights.WEAK_MAX:g}% = WEAK" in ai_review._SYSTEM
    assert f">{insights.STRONG_MAX:g}% = EXCELLENT" in ai_review._SYSTEM


def test_missing_key_logs_and_returns_none(monkeypatch, caplog):
    import logging
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with caplog.at_level(logging.WARNING):
        assert ai_review.generate_review({}, "en") is None
    assert "DEEPSEEK_API_KEY not set" in caplog.text
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_report.py -k "facts_rate or user_prompt_mentions
or scoring_table or missing_key_logs" -v`
Expected: FAIL.

- [ ] **Step 3: Edit `ai_review.py`** — add logging and a generated
band table near the top (after the imports / constants):

```python
import logging

_log = logging.getLogger(__name__)

# Scoring table generated from the single source of truth in insights,
# so the prompt can never drift from the code's banding.
_BAND_TABLE = (
    f"- <{insights.WEAK_MAX:g}% = WEAK\n"
    f"- {insights.WEAK_MAX:g}-{insights.MODERATE_MAX:g}% = MODERATE\n"
    f"- {insights.MODERATE_MAX:g}-{insights.STRONG_MAX:g}% = STRONG\n"
    f"- >{insights.STRONG_MAX:g}% = EXCELLENT\n\n"
)
```

In `_SYSTEM`, replace the four hard-coded scoring lines with the
generated table (keep the surrounding text; note the new basis):

```python
    "Replacement rate scoring (rate = pension vs gross salary AT "
    "RETIREMENT):\n"
    + _BAND_TABLE +
```

Replace `_score` body and `_facts`'s salary handling:

```python
def _score(rate):
    # Replacement-rate band — delegates to the shared scorer.
    return insights.band(rate)
```

In `_facts`, replace the `gross`/`rate`/`band` lines and the return
dict's first row:

```python
    inputs = data.get("inputs") or {}
    gross_ret = insights.salary_at_retirement(inputs)
    real = _num(mod.get("realMonthly"))
    nominal = _num(mod.get("monthly"))
    rate = insights.replacement_rate(nominal, gross_ret)
    band = _score(rate)
```

```python
        "real": round(real), "nominal": round(nominal),
        "rate": rate, "band": band, "gross_ret": round(gross_ret),
```

In `_user_prompt`, replace the replacement-rate line and add a salary
line:

```python
        f"- Gross salary at retirement: EUR {f['gross_ret']}",
        f"- Replacement rate: {f['rate']}% of salary at retirement  "
        f"(outlook: {f['band']})",
```

In `generate_review`, add a warning before each early return:

```python
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        _log.warning("DeepSeek review skipped: DEEPSEEK_API_KEY not set")
        return None
    try:
        from openai import OpenAI
    except ImportError:
        _log.warning("DeepSeek review skipped: openai not installed")
        return None
    if not ai_budget.try_consume():
        _log.warning("DeepSeek review skipped: daily AI budget exhausted")
        return None
```

```python
    except Exception as exc:
        _log.warning("DeepSeek review failed: %s", exc)
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_report.py -v`
Expected: PASS (existing `sk-test` tests still green).

- [ ] **Step 5: Commit**

```bash
git add ai_review.py tests/test_report.py
git commit -m "feat(ai_review): retirement-salary basis, shared bands, logging"
```

---

### Task 3: report_pdf + template + LV copy

**Files:**
- Modify: `report_pdf.py`, `templates/report.html`, `translations/lv.yaml`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `insights.salary_at_retirement`, `insights.replacement_rate`
  (Task 1).
- Produces: one consistent rate across hero, scenario cards, footer.

- [ ] **Step 1: Write the failing test** — add to `tests/test_report.py`:

```python
def test_report_uses_retirement_salary_basis():
    scn = {"monthly": 1800, "realMonthly": 900, "capital": 423000}
    data = {
        "inputs": {"grossMonthly": 1750, "grossAtRetirement": 9000,
                   "retirementAge": 65, "scenario": "moderate"},
        "totals": {"monthly": 1800, "realMonthly": 900, "capital": 423000},
        "pillars": {"p1": {"monthly": 900}, "p2": {"monthly": 600},
                    "p3": {"monthly": 300}},
        "activeScenario": "moderate",
        "scenarios": {"moderate": scn, "positive": scn, "negative": scn},
    }
    html = render_report_html(data, make_t("en"), "2026-06-30")
    assert "20.0%" in html                 # 1800 / 9000
    assert "salary at retirement" in html
    assert "current gross income" not in html
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_report.py -k retirement_salary_basis -v`
Expected: FAIL (`current gross income` still present; rate differs).

- [ ] **Step 3a: Edit `report_pdf.py`** — reword the strong verdict and
switch `_scenarios` to the retirement-salary basis:

```python
    "strong":
        "On track — your pension covers a strong share of your "
        "salary at retirement.",
```

```python
def _scenarios(t, data):
    # Three detailed scenario cards; empty when not provided.
    s = data.get("scenarios") or {}
    if not s:
        return []
    active = data.get("activeScenario", "moderate")
    inputs = data.get("inputs") or {}
    salary = insights.salary_at_retirement(inputs)
    out = []
    for key, label in _SCN_ORDER:
        v = s.get(key) or {}
        rate = insights.replacement_rate(v.get("monthly"), salary)
        prop = _num(v.get("propEquity"))
        out.append({
            "label": t(label),
            "real": _eur(v.get("realMonthly")),
            "nominal": _eur(v.get("monthly")),
            "capital": _eur(v.get("capital")),
            "rate": rate,
            "property": _eur(prop) if prop > 0 else None,
            "active": key == active,
        })
    return out
```

- [ ] **Step 3b: Edit `templates/report.html`** (line ~103) — reword
the rate caption:

```jinja
          <small>{{ t("of salary at retirement") }}</small></span>
```

- [ ] **Step 3c: Edit `translations/lv.yaml`** — replace the two
affected entries (the income caption and the strong verdict):

```yaml
of salary at retirement: no algas pensionējoties
On track — your pension covers a strong share of your salary at retirement.: Uz pareizā ceļa — pensija sedz būtisku daļu no algas pensionējoties.
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_report.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add report_pdf.py templates/report.html translations/lv.yaml \
  tests/test_report.py
git commit -m "feat(report): retirement-salary rate + reworded copy (EN/LV)"
```

---

### Task 4: Frontend — surface grossAtRetirement into the payload

**Files:**
- Modify: `static/js/ui.js`, `static/js/export.js`

**Interfaces:**
- Consumes: `calc.js` `projection.final.annualGross` (already computed).
- Produces: `inputs.grossAtRetirement` in the `/export/pdf` payload.

- [ ] **Step 1: Edit `static/js/ui.js`** — add the field to the P2
`pillarResult` detail (after the `rows:` line, ~158):

```javascript
      rows:                projection.rows,
      grossAtRetirement:   Math.round(projection.final.annualGross / 12),
```

- [ ] **Step 2: Edit `static/js/export.js`** — add it to `buildPayload`
`inputs` (after `grossMonthly`, ~48):

```javascript
      grossMonthly: readNum("grossMonthly"),
      grossAtRetirement: n((pillarCache.p2 || {}).grossAtRetirement),
```

- [ ] **Step 3: Manual end-to-end verification**

```bash
source .venv/bin/activate
DEEPSEEK_API_KEY=$(grep '^DEEPSEEK_API_KEY=' .env | cut -d= -f2-) \
  python app.py     # serves on http://127.0.0.1:5001
```
Open the page, leave defaults, download the PDF. Confirm: the
replacement rate is markedly lower than before (~20% vs ~45%), the
caption reads "of salary at retirement", and the AI box renders.

- [ ] **Step 4: Commit**

```bash
git add static/js/ui.js static/js/export.js
git commit -m "feat(export): send projected salary-at-retirement in payload"
```

---

### Task 5: Calibration sweep + tune bands

**Files:**
- Create: `tools/calibrate_bands.py`
- Modify (if skewed): `insights.py`

- [ ] **Step 1: Create `tools/calibrate_bands.py`**

```python
# tools/calibrate_bands.py — sweep representative personas and print
# the new replacement rate + band, so the WEAK/MODERATE/STRONG/
# EXCELLENT thresholds in insights.py can be sanity-checked or tuned.
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import insights


def salary_at_ret(gross, growth_pct, years):
    # Mirror calc.js: final working-year salary = gross*(1+g)^(years-1).
    return round(gross * (1 + growth_pct / 100) ** max(0, years - 1))


# (label, current gross, salary growth %, years, nominal total pension)
PERSONAS = [
    ("Young, low save", 1200, 5.0, 37, 900),
    ("Young, strong P3", 1750, 5.0, 35, 2600),
    ("Mid, moderate", 2200, 4.0, 22, 1800),
    ("Older, near retire", 3000, 3.0, 8, 2400),
    ("High earner", 5000, 5.0, 30, 5200),
    ("Low growth", 1600, 2.0, 30, 1300),
]

print(f"{'persona':22}{'salary@ret':>11}{'pension':>9}"
      f"{'rate%':>7}{'band':>11}")
for label, gross, g, yrs, pension in PERSONAS:
    sret = salary_at_ret(gross, g, yrs)
    rate = insights.replacement_rate(pension, sret)
    print(f"{label:22}{sret:>11}{pension:>9}{rate:>7}"
          f"{insights.band(rate):>11}")
```

- [ ] **Step 2: Run the sweep**

Run: `python tools/calibrate_bands.py`
Expected: a table; bands should span at least WEAK→STRONG (not all in
one band).

- [ ] **Step 3: Tune if skewed**

If every persona lands in one band, adjust `WEAK_MAX/MODERATE_MAX/
STRONG_MAX` in `insights.py` so the spread is meaningful, then re-run
Step 2 and `pytest tests/test_report.py -v` (boundary tests may need
matching updates).

- [ ] **Step 4: Commit**

```bash
git add tools/calibrate_bands.py insights.py tests/test_report.py
git commit -m "test(insights): band calibration sweep + tuning"
```

---

## Deployment (Workstream A — operational, run by the user)

Code change is only the logging; the live fix is the new key. On the
VPS, in the pension repo:

```bash
# 1. put the NEW DeepSeek key in the gitignored .env
nano ~/pension_calc/.env          # DEEPSEEK_API_KEY=<new key>
# 2. rebuild + restart the app (Caddy keeps running)
cd ~/pension_calc/deploy
docker compose up -d --build pension
# 3. verify: download a report from https://pension.oats.lv → AI box
docker compose logs --tail=30 pension   # any "DeepSeek review" warnings?
```

A warning like `DeepSeek review failed: ... 401` means the key is
still wrong; no warning + AI box present means success.

## Self-Review

- **Spec coverage:** observability logging (T2) + deploy (Deployment);
  data flow `calc.js`→`ui.js`→`export.js` (T4) + backend consume
  (T1-T3); one-source-of-truth bands in `insights.py` (T1) imported by
  `ai_review` (T2); nominal÷nominal basis + fallback (T1); recalibrated
  bands (T1) + calibration sweep (T5); consistent rate across three PDF
  surfaces (T3); LV parity (T3); tests each task.
- **Placeholders:** none — every step has concrete code/commands.
- **Type consistency:** `salary_at_retirement(inputs)`, `band(rate)`,
  `replacement_rate(pension, salary)`, `grossAtRetirement` (JS+payload),
  `_facts(...)["gross_ret"]` are defined where introduced and used with
  the same names downstream.
