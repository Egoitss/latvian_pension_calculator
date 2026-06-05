# Pensijas kalkulators

A personal Latvian pension calculator covering all four savings pillars:
1st pillar NDC, 2nd pillar (P2L), 3rd pillar voluntary pension, and
property equity. Runs locally as a Flask app.

## Features

- **2nd pillar projection** — compound growth with VSAOI ceiling, plan
  switching, and plan fee modelling
- **1st pillar NDC** — state pension estimate from capital and service years
- **3rd pillar** — voluntary pension with IIN tax relief and net payout
- **Property** — equity growth with city-specific appreciation rates
- **Monte Carlo scenarios** — 10 000 bootstrap simulations using your own
  Dinamika NAV history; positive / moderate / negative scenario buttons
- **Loan calculator** — mortgage + consumer credit side-by-side at `/loans`
- **Combined chart** — stacked area showing all four pillars over time,
  inflation-adjusted "today's money" overlay
- **No server round-trips** — all live interactivity runs in the browser

## Quick start

```bash
pip install -r requirements.txt
python3 app.py          # opens on http://localhost:5001
```

> macOS AirPlay occupies port 5000, so the app uses 5001.

## Personal data setup

Form values (salary, balance, birth year, etc.) are saved automatically in
your browser's localStorage — they never touch the server or appear in git.
On first visit the form shows empty inputs with gray demo hints; your saved
values load on every return visit. Clearing browser storage resets to demo
defaults.

If you want to run personalised Monte Carlo simulations, copy the example
config:

```bash
cp local_config.example.py local_config.py
```

and supply historical Dinamika 18-49 NAV prices in `_DINAMIKA_PRICES`.
Without it the three scenario buttons use fixed fallback rates
(10% / 7.5% / 3%).

## Running tests

```bash
python3 -m pytest tests/ -v
python3 -m pytest tests/test_calculator.py::test_name -v   # single test
```

## Project layout

```
app.py           Flask routes (GET / and GET /loans)
calculator.py    Pure Python projection functions — no Flask dependency
data.py          Constants, PLANS list, P3_PLANS, get_plan_by_name()
templates/       Jinja partials included by index.html / loans.html
static/js/       ES modules (no build step)
tests/           pytest suite mirroring calculator.py
local_config.py  Personal overrides — gitignored, never commit
```

### JS modules

| File | Role |
|---|---|
| `data.js` | PLANS + CONSTANTS (mirrors `data.py`) |
| `calc.js` | Projection, VSAOI ceiling, schedule, bootstrap |
| `chart.js` | Chart.js wrapper — `initChart` / `drawChart` |
| `ui.js` | DOM wiring, P2L orchestrator |
| `scenarios.js` | Monte Carlo, scenario buttons, combined totals |
| `pension1.js` | P1 NDC live recalculation |
| `pension3.js` | P3 voluntary pension live recalculation |
| `property.js` | Property equity estimator |
| `loans.js` | Mortgage + credit widget (shared with `/loans`) |
| `accordion.js` | Generic expand/collapse sections |

## Key constants (`data.py`)

| Constant | Value | Meaning |
|---|---|---|
| `VSAOI_CEILING` | 105 300 EUR | Annual gross cap for P2L contributions |
| `P2L_RATE` | 6% | Current legal employee contribution rate |
| `PENSION_TAX_FREE_THRESHOLD` | 1 000 EUR/month | Tax-exempt payout amount |
| `PENSION_TAX_RATE` | 25.5% | Tax on payout above threshold |
| `DEFAULT_RETURN` | 8% | Fallback annual return |

## Updating plan data

Returns are sourced from `manapensija.lv`. Update `return_3y`, `return_5y`,
and `fee_total` in both `data.py` and `static/js/data.js` — they are kept
in sync manually.

## Personal data

Form values (salary, balances, birth year, etc.) are saved automatically
in browser localStorage — they never touch the server or appear in git.
On first visit the form shows empty inputs with gray demo hints; your
saved values load on every return visit. Clearing browser storage resets
to demo defaults.

`local_config.py` is only needed to supply historical Dinamika 18-49 NAV
prices for personalised Monte Carlo simulations. Without it the three
scenario buttons use fixed fallback rates (10% / 7.5% / 3%).
