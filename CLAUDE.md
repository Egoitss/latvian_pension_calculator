# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask web app implementing a Latvian 2nd-pillar pension calculator (P2L).
Run locally for personal use. UI is in Latvian.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server (opens at http://localhost:5000)
python3 app.py

# Run tests
python3 -m pytest tests/ -v
```

## Key domain constants (`data.py`)

| Constant | Value | Meaning |
|---|---|---|
| `VSAOI_CEILING` | 105 300 EUR | Annual gross cap for P2L contributions |
| `P2L_RATE` | 5% | Employee contribution rate |
| `PENSION_TAX_FREE_THRESHOLD` | 1 000 EUR/month | Tax-exempt payout amount |
| `PENSION_TAX_RATE` | 25.5% | Tax on payout above threshold |
| `DEFAULT_RETURN` | 8% | Fallback annual return |

## Architecture

```
data.py          constants + PLANS list + get_plan_by_name()
calculator.py    pure Python functions (no Flask) — testable
app.py           single GET / route; renders index.html with defaults
templates/       Jinja partials included by index.html
static/js/       ES modules: data.js → calc.js ← chart.js ← ui.js
tests/           pytest suite mirroring calculator.py logic
```

**Data flow:** Flask renders the page with server-computed defaults baked in.
JS takes over on load — all live interactivity (sliders, plan switching) runs
entirely client-side with no server round-trips.

## JS module responsibilities

| File | Role |
|---|---|
| `data.js` | PLANS array + CONSTANTS — mirrors `data.py` |
| `calc.js` | Pure functions: projection, VSAOI ceiling, schedule |
| `chart.js` | Chart.js wrapper; `initChart` / `drawChart` |
| `ui.js` | DOM wiring, event listeners, `onInputChange` orchestrator |

## Updating plan data

Returns come from public data at `manapensija.lv`. Update `return_3y`,
`return_5y`, and `fee_total` in **both** `data.py` and `static/js/data.js`
(they are kept in sync manually).

## Coding rules

- Line width: 80–100 chars (hard limit 120)
- Function length: 20–30 lines (hard limit 50)
- File length: 200–300 lines (hard limit 500)
- Every logical block has a one-line comment explaining what it does
