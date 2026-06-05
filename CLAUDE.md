# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask web app implementing a Latvian 2nd-pillar pension calculator (P2L).
Run locally for personal use. UI is in Latvian.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server
python3 app.py
# Note: macOS AirPlay occupies port 5000 — app.py runs on 5001

# Run tests
python3 -m pytest tests/ -v

# Run a single test
python3 -m pytest tests/test_calculator.py::test_name -v
```

## Key domain constants (`data.py`)

| Constant | Value | Meaning |
|---|---|---|
| `VSAOI_CEILING` | 105 300 EUR | Annual gross cap for P2L contributions |
| `P2L_RATE` | 6% | Employee contribution rate (current legal rate since 2021) |
| `PENSION_TAX_FREE_THRESHOLD` | 1 000 EUR/month | Tax-exempt payout amount |
| `PENSION_TAX_RATE` | 25.5% | Tax on payout above threshold |
| `DEFAULT_RETURN` | 8% | Fallback annual return |

## Personal data

Personal form values (balance, salary, birth year) live **only in browser localStorage** —
never on the server. `storage.js` owns all save/load logic. Flask `DEFAULTS` holds
demo values only; `OVERRIDES` was removed — do NOT re-add it.
`local_config.py` (gitignored) is only for `_DINAMIKA_PRICES` + `P3_COST_BASIS` (Monte Carlo).

## Architecture

```
data.py          constants + PLANS list + P3_PLANS + get_plan_by_name()
calculator.py    pure Python functions (no Flask) — testable
app.py           GET / and GET /loans routes; merges local_config at import
templates/       Jinja partials included by index.html and loans.html
static/js/       ES modules loaded at bottom of each page template
tests/           pytest suite mirroring calculator.py logic
```

**Data flow:** Flask renders the page with demo defaults. On load, `storage.js`
`loadInputs()` restores personal values from localStorage before the first calculation.
All live interactivity runs client-side with no server round-trips.

**JS inter-module communication** uses CustomEvents on `document`:
- `scenarioChange` — scenarios.js → property.js, pension3.js (active scenario)
- `pillarResult` — ui.js/pension1.js/pension3.js → scenarios.js (per-pillar totals)
- `propertyResult` — property.js → scenarios.js (equity at retirement)

## JS module responsibilities

| File | Role |
|---|---|
| `data.js` | PLANS array + CONSTANTS — mirrors `data.py` |
| `calc.js` | Pure functions: projection, VSAOI ceiling, schedule, bootstrap |
| `chart.js` | Chart.js wrapper; `initChart` / `drawChart` |
| `ui.js` | DOM wiring, event listeners, `onInputChange` orchestrator (P2L) |
| `scenarios.js` | Monte Carlo bootstrap (10k runs), scenario buttons, combined totals |
| `pension1.js` | P1 NDC (1st pillar) live recalculation |
| `pension3.js` | P3 voluntary pension live recalculation |
| `property.js` | Property value estimator; reads shared inputs |
| `loans.js` | Shared loan widget (mortgage + credit); used on `/loans` page too |
| `accordion.js` | Generic accordion: expand on click or when trigger input has value |
| `ai_recommend.js` | AI recommendation card (calls backend `/ai_recommend`) |
| `storage.js` | localStorage persistence for all form inputs, gender, propType |

## Input persistence (storage.js)

All tracked inputs save/restore via `static/js/storage.js`. Key: `pensija_v1`.
Bump the version string if input IDs change (invalidates old stored data).
`balance`, `grossMonthly`, `birthYear` use `placeholder=` not `value=` in templates.
`ui.js` init order: `loadGender()` → `syncRetirementAge(false)` → `loadInputs()` → `onInputChange()`.
To add a new persisted input: add its ID + `"value"` (or `"checked"`) to the `INPUTS` map in `storage.js`.

## GitHub remote

`origin` → `https://github.com/Egoitss/latvian_pension_calculator.git`

## Updating plan data

Returns come from public data at `manapensija.lv`. Update `return_3y`,
`return_5y`, and `fee_total` in **both** `data.py` and `static/js/data.js`
(they are kept in sync manually).

## Coding rules

- Line width: 80–100 chars (hard limit 120)
- Function length: 20–30 lines (hard limit 50)
- File length: 200–300 lines (hard limit 500)
- Every logical block has a one-line comment explaining what it does
