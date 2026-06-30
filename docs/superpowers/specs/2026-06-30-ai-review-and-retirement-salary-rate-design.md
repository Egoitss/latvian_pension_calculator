# AI review on live + salary-at-retirement replacement rate

**Date:** 2026-06-30
**Status:** approved design

Two independent workstreams in `pension_calc`. Both touch the
downloadable PDF report; neither touches the on-page Anthropic
`/api/recommend` feature or the (paused) BMX deployment.

## Workstream A — render the AI review on pension.oats.lv

### Problem

The code path is already wired (`app.py` `load_dotenv()`, `openai`
installed, `export_pdf` → `ai_review.generate_review`). The live VPS
loads the key via `deploy/docker-compose.yml`
(`env_file: ../.env`). That `.env` still holds the **revoked** key,
so DeepSeek returns 401, `generate_review` swallows it
(`except Exception: return None`), and the PDF drops the AI box with
no trace.

### Changes

1. **Deploy (run by the user on the VPS):** update `../.env` with the
   new key, then `docker compose up -d` to restart the `pension`
   service. No git change — `.env` stays gitignored.
2. **Observability (code):** in `ai_review.generate_review`, replace
   the silent swallow with `logging.warning(...)` that names the
   reason — API error, missing key, or budget exhausted — so a
   missing AI box is diagnosable from container logs. Behaviour is
   unchanged: the PDF still falls back gracefully.

### Non-goals

No retry logic, no surfacing errors to the end user, no secret in
git (verified none is hardcoded; only `sk-test` in tests).

## Workstream B — replacement rate vs salary-at-retirement

### Problem

`insights.replacement_rate(real_monthly, gross_monthly)` divides the
pension by the person's **current** salary. It should divide by the
salary they will earn **at retirement**. Today this denominator
feeds three PDF surfaces: the AI verdict (`ai_review._facts`), the
deterministic outlook box, and the per-scenario cards
(`report_pdf._scenarios`).

### Data flow — surface the salary already computed

`calc.js` already builds `final = rows[last]` with
`final.annualGross` (the projected gross in the final working year).
`export.js` discards it. Surface it instead:

1. `calc.js` P2 result → add
   `grossAtRetirement = final.annualGross / 12` to the `pillarResult`
   detail.
2. `export.js buildPayload()` → add `grossAtRetirement` to `inputs`
   (scenario-independent — one value).
3. Backend reads `inputs.grossAtRetirement` as the new denominator.

Reusing the engine's value avoids a second JS/Python implementation
of the salary projection (no drift).

### Metric — one source of truth

Thresholds are triplicated today (`ai_review._score`,
`ai_review._SYSTEM` prose, `insights.STRONG_MIN/MODERATE_MIN`). Since
all three change, consolidate the band thresholds **and** the
replacement-rate function into `insights.py`; `ai_review` imports
them and generates its prompt's scoring table from the constants.

- New rate: **nominal** pension ÷ **nominal** salary-at-retirement
  (textbook gross replacement rate — both in future EUR).
- Fallback: if `grossAtRetirement` is absent (old payloads), fall
  back to current `grossMonthly` so nothing crashes.

### Recalibrated bands (provisional — tuned by a sweep)

| Band | Old (vs current) | New (vs at-retirement) |
|------|------|------|
| WEAK | <45% | <20% |
| MODERATE | 45–60% | 20–30% |
| STRONG | 60–75% | 30–45% |
| EXCELLENT | >75% | ≥45% |

`insights.outlook` keeps its 3-way weak/moderate/strong using the
same boundaries (20, 30); `ai_review` keeps EXCELLENT as a fourth
top tier split at 45. Verdict prose ("…share of today's income") is
reworded to "…of your salary at retirement."

## Testing

- `replacement_rate` with the new denominator; band boundaries
  (19/20/29/30/44/45); fallback when `grossAtRetirement` is missing.
- `ai_review._facts` passes `grossAtRetirement`; `_score` matches the
  new thresholds; the generated scoring table matches the constants.
- `report_pdf` shows one consistent rate across all three boxes.
- A calibration script sweeps representative personas (young/old,
  low/high salary, ±P3, delayed retirement) to confirm a sensible
  band spread; tune thresholds if skewed.
- Existing `tests/test_report.py` / `test_security.py` stay green.

## Design constraints

≤300 lines/file, ≤50 lines/function, ≤80 chars/line; every
function/macro opens with a describing comment (house rules).
