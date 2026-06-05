# Separate Calculators + Git-Safe Personal Data

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the loans widget to its own page at `/loans`, and ensure
no personal financial data (balances, prices, cost basis) is ever committed
to git — only imaginary demo values.

**Architecture:** Two changes run in parallel but Phase A must finish first
because Phase B depends on the LOCAL_DATA injection pattern from Phase A.
Phase A wires a `local_config.py → Flask → window.LOCAL_DATA → data.js`
pipeline so all personal numbers flow through one gitignored file. Phase B
creates a standalone `/loans` page that reads the P2L balance from a URL
param rather than from the pension page's DOM.

**Tech Stack:** Python/Flask, Jinja2, vanilla ES modules, no new deps.

---

## Phase A — Git-safe personal data layer

### ⚠️ Priority: `local_config.py` is not gitignored

`local_config.py` exists and holds real mortgage balances, pension
capital, salary, and birth date. There is currently **no `.gitignore`**.
The very first task below fixes this before any other work.

### File map

| Action  | Path |
|---------|------|
| Create  | `.gitignore` |
| Create  | `local_config.example.py` |
| Modify  | `local_config.py` — add personal series data |
| Modify  | `data.py` — remove personal series, add fallbacks |
| Modify  | `calculator.py` — guard empty pool in bootstrap |
| Modify  | `app.py` — pass `local_data` dict to template |
| Modify  | `templates/index.html` — inject `window.LOCAL_DATA` |
| Modify  | `static/js/data.js` — read prices/cost-basis from window |
| Modify  | `static/js/calc.js` — guard empty pool in JS bootstrap |

---

### Task 1 — Create `.gitignore`

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Write `.gitignore`**

```
# Personal config — NEVER commit
local_config.py

# Python artefacts
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
.venv/
venv/

# OS
.DS_Store
Thumbs.db

# Editor
.idea/
.vscode/
*.swp
```

- [ ] **Step 2: Verify local_config.py is now ignored**

```bash
git status
```

Expected: `local_config.py` no longer appears in untracked/modified.
If it was already staged, unstage it:

```bash
git rm --cached local_config.py
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore (exclude local_config.py)"
```

---

### Task 2 — Create `local_config.example.py` with imaginary data

**Files:**
- Create: `local_config.example.py`

This is the file that gets committed. It shows the structure with
plausible but entirely made-up numbers a new user can replace.

- [ ] **Step 1: Write `local_config.example.py`**

```python
# Copy this file to local_config.py and fill in your own values.
# local_config.py is gitignored — it will never be committed.

OVERRIDES = {
    # Personal profile
    "birth_year":  1990,
    "birth_month": 6,
    # 2nd pillar pension
    "balance":               3_500.00,
    "gross_monthly":         1_600,
    "selected_plan_name":    "SEB indeksu plāns 15-54",
    "p2l_start_year":        2008,
    "p2l_start_salary":      400,
    "p2l_actual_contributions": 2_100.00,
    "salary_growth":         4.0,
    "inflation":             3.5,
    "p2l_rate":              6.0,
    # 1st pillar NDC
    "p1_capital":       18_000.00,
    "p1_record_years":  12,
    "p1_record_months": 4,
    # 3rd pillar
    "p3_balance":             2_000.00,
    "p3_monthly":             20.0,
    "p3_contribution_growth": 3.0,
    "p3_plan_name":           "Swedbank Dinamika 18-49",
    # Mortgage (example: 80 000 EUR, ends Dec 2045, variable)
    "mort_balance":        80_000.00,
    "mort_end_month":      12,
    "mort_end_year":       2045,
    "mort_bank_margin":    2.000,
    "mort_euribor":        2.500,
    "mort_actual_payment": 510.00,
    # Car loan (example: 8 000 EUR, ends Jun 2028, fixed)
    "cred_balance":        8_000.00,
    "cred_end_month":      6,
    "cred_end_year":       2028,
    "cred_bank_margin":    9.900,
    "cred_euribor":        0.000,
    "cred_actual_payment": 180.00,
    # Property widget
    "prop_price": 150_000,
    "prop_type":  "riga",
}

# Historical Dinamika 18-49 NAV prices (monthly, from Swedbank CSV export).
# Replace with your own sequence. Must have at least 2 values.
# Leave as [] if you don't have this data — scenarios use fixed fallback rates.
_DINAMIKA_PRICES = []

# Your personal P3 cost basis BEFORE the simulation window (EUR).
# Set to 0.0 if all your contributions happen within the simulation period.
P3_COST_BASIS = 0.0
```

- [ ] **Step 2: Commit**

```bash
git add local_config.example.py
git commit -m "docs: add local_config.example.py with imaginary demo data"
```

---

### Task 3 — Move personal series out of `data.py`

`data.py` currently embeds 88 real NAV prices and the real cost basis.
These move to `local_config.py`; `data.py` gets empty fallbacks.

**Files:**
- Modify: `data.py:168-190` (remove personal series block)
- Modify: `local_config.py` (add series vars)

- [ ] **Step 1: Add series to `local_config.py`**

Open `local_config.py`. After the `OVERRIDES = {...}` block, append:

```python
# Historical Dinamika 18-49 NAV prices Feb 2019–May 2026
# (source: Swedbank CSV)
_DINAMIKA_PRICES = [
    1.62790, 1.63010, 1.69840, 1.66600, 1.66830, 1.72710, 1.66160,
    # ... (keep the full existing list from data.py unchanged) ...
]

# Total cost basis for P3 (Sabalansētais Dec 2013–Feb 2019 +
# Dinamika Mar 2019–May 2026)
P3_COST_BASIS = 2_983.17
```

Copy the actual values from the current `data.py` lines 168–190 verbatim.

- [ ] **Step 2: Replace the personal-data block in `data.py`**

Remove lines 167–190 (the `_DINAMIKA_PRICES` list, the derived
`DINAMIKA_MONTHLY_RETURNS`, and `P3_COST_BASIS`) and replace them with:

```python
# Personal series — loaded from local_config.py if present.
# Falls back to empty list so bootstrap returns fixed fallback rates.
_DINAMIKA_PRICES_LOCAL: list = []
try:
    from local_config import _DINAMIKA_PRICES as _DINAMIKA_PRICES_LOCAL
except (ImportError, AttributeError):
    pass

DINAMIKA_MONTHLY_RETURNS = [
    _DINAMIKA_PRICES_LOCAL[i] / _DINAMIKA_PRICES_LOCAL[i - 1] - 1
    for i in range(1, len(_DINAMIKA_PRICES_LOCAL))
]

P3_COST_BASIS: float = 0.0
try:
    from local_config import P3_COST_BASIS
except (ImportError, AttributeError):
    pass
```

- [ ] **Step 3: Run tests to verify nothing broke**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Smoke test the server**

```bash
python3 app.py &
sleep 2
curl -s http://localhost:5000 | grep -c "Pensijas kalkulators"
kill %1
```

Expected: output is `1` (page title found).

- [ ] **Step 5: Commit**

```bash
git add data.py local_config.py
git commit -m \
  "refactor: move personal Dinamika series + cost basis to local_config"
```

---

### Task 4 — Guard empty pool in Python bootstrap

`calculator.py:bootstrap_scenario_returns()` calls `rng.choice(pool)`.
If `pool` is `[]`, this raises `IndexError`.

**Files:**
- Modify: `calculator.py:348-375`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_calculator.py`:

```python
def test_bootstrap_returns_fallback_when_no_data(monkeypatch):
    import data as d
    monkeypatch.setattr(d, "DINAMIKA_MONTHLY_RETURNS", [])
    # Re-import so calculator sees the patched value
    import importlib, calculator as c
    importlib.reload(c)
    result = c.bootstrap_scenario_returns(num_months=12)
    assert result["positive"] > result["moderate"] > result["negative"]
    assert result["moderate"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_calculator.py \
  -k "test_bootstrap_returns_fallback" -v
```

Expected: FAIL (IndexError from `rng.choice([])`).

- [ ] **Step 3: Add guard in `calculator.py`**

Replace the opening of `bootstrap_scenario_returns` (after the docstring,
before `import random`):

```python
def bootstrap_scenario_returns(
    num_months, n_simulations=10_000, seed=None
):
    # Fall back to fixed rates when no historical price data is loaded.
    if not DINAMIKA_MONTHLY_RETURNS:
        return {"positive": 10.0, "moderate": 7.5, "negative": 3.0}

    import random
    rng = random.Random(seed)
    # ... rest of function unchanged ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_calculator.py \
  -k "test_bootstrap_returns_fallback" -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add calculator.py tests/test_calculator.py
git commit -m "fix: bootstrap falls back to fixed rates when pool is empty"
```

---

### Task 5 — Inject personal data into JS via Flask

`data.js` has `_DINAMIKA_PRICES` and `P3_COST_BASIS` hardcoded.
Flask will inject them as `window.LOCAL_DATA` so the static JS file
contains no personal numbers.

**Files:**
- Modify: `app.py` (pass `local_data` to template)
- Modify: `templates/index.html` (inject `window.LOCAL_DATA` script tag)
- Modify: `static/js/data.js` (read from window instead of literals)
- Modify: `static/js/calc.js` (guard empty pool in JS bootstrap)

- [ ] **Step 1: Pass `local_data` from `app.py`**

In `app.py`, after the `try: from local_config import OVERRIDES` block
(around line 64), add:

```python
# Load personal JS data from local_config if available
_lc_prices: list = []
_lc_cost_basis: float = 0.0
try:
    from local_config import _DINAMIKA_PRICES as _lc_prices
except (ImportError, AttributeError):
    pass
try:
    from local_config import P3_COST_BASIS as _lc_cost_basis
except (ImportError, AttributeError):
    pass

LOCAL_DATA = {
    "dinamika_prices": _lc_prices,
    "p3_cost_basis": _lc_cost_basis,
}
```

In the `index()` route, add `local_data=LOCAL_DATA` to the
`render_template(...)` call:

```python
resp = make_response(render_template(
    "index.html",
    plans=PLANS,
    p3_plans=P3_PLANS,
    defaults=d,
    constants=constants,
    urls=urls,
    projection=projection,
    plan_schedule_json=json.dumps(plan_schedule),
    apply_ceiling=apply_ceiling,
    local_data=LOCAL_DATA,   # <-- add this line
))
```

- [ ] **Step 2: Inject `window.LOCAL_DATA` in `index.html`**

In `templates/index.html`, inside `{% block scripts %}`, add this
**before** the `<script src="...data.js">` line:

```html
<script>
  /* Personal series data injected by Flask — empty when no local_config */
  window.LOCAL_DATA = {
    dinamikaPrices: {{ local_data.dinamika_prices | tojson }},
    p3CostBasis: {{ local_data.p3_cost_basis | tojson }},
  };
</script>
```

- [ ] **Step 3: Remove hardcoded personal data from `data.js`**

Replace lines 167–190 in `static/js/data.js` (the `_DINAMIKA_PRICES`
array, `DINAMIKA_MONTHLY_RETURNS` derivation, and `P3_COST_BASIS`) with:

```js
// Personal series — injected by Flask via window.LOCAL_DATA.
// Falls back to [] when no local_config.py is present.
const _DINAMIKA_PRICES =
  (window.LOCAL_DATA && window.LOCAL_DATA.dinamikaPrices) || [];

// 87 monthly returns derived from NAV prices
export const DINAMIKA_MONTHLY_RETURNS = _DINAMIKA_PRICES.slice(1).map(
  (p, i) => p / _DINAMIKA_PRICES[i] - 1
);

// Historical P3 cost basis before simulation window
export const P3_COST_BASIS =
  (window.LOCAL_DATA && window.LOCAL_DATA.p3CostBasis) || 0.0;
```

- [ ] **Step 4: Guard empty pool in `calc.js` bootstrap**

In `static/js/calc.js`, replace the opening of
`bootstrapScenarioReturns` (line ~299):

```js
export function bootstrapScenarioReturns(numMonths, nSims = 10_000) {
  const pool = DINAMIKA_MONTHLY_RETURNS;
  // Fall back to fixed rates when no historical price data is loaded.
  if (pool.length === 0) {
    return { positive: 10.0, moderate: 7.5, negative: 3.0 };
  }
  const poolLen = pool.length;
  // ... rest of function unchanged ...
```

- [ ] **Step 5: Smoke test**

```bash
python3 app.py &
sleep 2
# Scenario rates should appear in response (Monte Carlo runs OK)
curl -s http://localhost:5000 | grep -c "Monte Carlo"
kill %1
```

Expected: `1` (bootstrap note text is in the rendered HTML).

- [ ] **Step 6: Commit**

```bash
git add app.py templates/index.html \
        static/js/data.js static/js/calc.js
git commit -m \
  "feat: inject personal Dinamika series via window.LOCAL_DATA"
```

---

## Phase B — Loans as a standalone page

### File map

| Action  | Path |
|---------|------|
| Modify  | `static/js/loans.js` — read P2L from `#p2lBalance` |
| Create  | `templates/loans.html` — standalone loans page |
| Modify  | `app.py` — add `/loans` route |
| Modify  | `templates/index.html` — remove loans include, add link |

---

### Task 6 — Update `loans.js` to read P2L from its own input

Currently `allocateP2L()` reads `document.getElementById("balance")`
which is the P2L balance input on the pension page. The loans page will
have its own `#p2lBalance` input.

**Files:**
- Modify: `static/js/loans.js:79`

- [ ] **Step 1: Replace the balance read in `allocateP2L()`**

Find this line in `loans.js` (around line 79):

```js
  let remaining = parseFloat((g("balance") || {}).value) || 0;
```

Replace with:

```js
  // Read from loans-page input; fall back to pension-page #balance
  // (supports both standalone /loans and embedded use).
  const balEl = g("p2lBalance") || g("balance");
  let remaining = parseFloat((balEl || {}).value) || 0;
```

- [ ] **Step 2: Verify the change compiles (syntax check)**

```bash
node --input-type=module < static/js/loans.js 2>&1 | head -5
```

Expected: no output (no syntax errors — the file uses DOM APIs that
Node doesn't have, but syntax errors would show before any DOM access).

Actually, use a simpler check:

```bash
python3 -c "
import subprocess, sys
r = subprocess.run(['node', '--check', 'static/js/loans.js'])
sys.exit(r.returncode)
" && echo "OK"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add static/js/loans.js
git commit -m "fix: loans.js reads P2L from #p2lBalance with #balance fallback"
```

---

### Task 7 — Create `templates/loans.html`

Standalone page: header with a P2L balance input, the loans widget,
and a back-link to the pension page.

**Files:**
- Create: `templates/loans.html`

- [ ] **Step 1: Write `templates/loans.html`**

```html
{% extends "base.html" %}

{% block content %}
<main class="p-3 md:p-6">
  <div class="mx-auto max-w-2xl space-y-4">

    <!-- Back link -->
    <a href="/"
       class="inline-flex items-center gap-1 text-xs text-slate-400
              hover:text-slate-700 transition">
      ← Pensijas kalkulators
    </a>

    <section>
      <h1 class="text-xl font-bold tracking-tight text-slate-900">
        Kredītu kalkulators
      </h1>
      <p class="text-[11px] text-slate-400 mt-1">
        Hipotekārais un patēriņa kredīts · P2L scenāriji
      </p>
    </section>

    <!-- P2L balance input for standalone use -->
    <div class="rounded-3xl border border-slate-200 bg-white shadow-sm p-4">
      <div class="text-xs font-semibold text-slate-500 mb-2 uppercase
                  tracking-wider">
        2. pensiju līmeņa atlikums
      </div>
      <div class="flex items-center gap-3">
        <input id="p2lBalance" type="number" step="0.01" min="0"
               placeholder="Ievadi savu P2L atlikumu (€)"
               {% if defaults.balance %}
               value="{{ defaults.balance }}"
               {% endif %}
               class="flex-1 rounded-2xl border border-slate-200 bg-white
                      px-3 py-2 text-sm outline-none transition
                      focus:border-slate-500 focus:ring-2
                      focus:ring-slate-200" />
        <span class="text-sm text-slate-400">€</span>
      </div>
      <p class="mt-1.5 text-[10px] text-slate-400">
        Izmanto P2L scenārijus zemāk, lai redzētu, kā atlikums ietekmē
        kredītus.
      </p>
    </div>

    <!-- Loans widget -->
    {% include "_loans.html" %}

  </div>
</main>
{% endblock %}

{% block scripts %}
<script>
  /* Pre-fill P2L balance from ?p2l= query param if present */
  (function () {
    const params = new URLSearchParams(window.location.search);
    const v = params.get("p2l");
    if (v) {
      const el = document.getElementById("p2lBalance");
      if (el) { el.value = v; el.dispatchEvent(new Event("input")); }
    }
  })();
</script>
<script src="{{ url_for('static', filename='js/loans.js',
                        v=js_v) }}"></script>
<script src="{{ url_for('static', filename='js/accordion.js',
                        v=js_v) }}"></script>
{% endblock %}
```

- [ ] **Step 2: Verify template renders (no Jinja errors)**

```bash
python3 app.py &
sleep 2
curl -s http://localhost:5000/loans | grep -c "Kredītu kalkulators"
kill %1
```

Expected: `1`.

- [ ] **Step 3: Commit**

```bash
git add templates/loans.html
git commit -m "feat: add standalone /loans page with P2L balance input"
```

---

### Task 8 — Add `/loans` route to `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add the route**

After the closing `return resp` of the `index()` function, add:

```python
@app.route("/loans")
def loans():
    # Standalone loans calculator — only needs loan defaults
    d = DEFAULTS
    resp = make_response(render_template(
        "loans.html",
        defaults=d,
    ))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp
```

- [ ] **Step 2: Test route**

```bash
python3 app.py &
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/loans
kill %1
```

Expected: `200`.

- [ ] **Step 3: Test URL param pre-fill**

```bash
python3 app.py &
sleep 2
curl -s "http://localhost:5000/loans?p2l=20819.80" | \
  grep -c "p2lBalance"
kill %1
```

Expected: `1` (input element present in HTML).

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add /loans Flask route"
```

---

### Task 9 — Update pension page: remove loans, add link

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Remove the loans include**

In `templates/index.html`, find and delete this line:

```html
    {% include "_loans.html" %}
```

- [ ] **Step 2: Add a link to the loans page**

In `templates/index.html`, after `{% include "_ai_recommend.html" %}`,
add:

```html
    <!-- Link to standalone loans calculator -->
    <div class="text-center py-2">
      <a id="loansPageLink"
         href="/loans"
         class="inline-flex items-center gap-1.5 rounded-2xl border
                border-slate-200 bg-white px-4 py-2 text-sm font-medium
                text-slate-600 shadow-sm transition hover:border-slate-400
                hover:text-slate-900">
        Kredītu kalkulators →
      </a>
    </div>
```

- [ ] **Step 3: Wire P2L balance into the link via JS**

In `templates/index.html`, inside `{% block scripts %}`, add after the
existing `window.P2L_CONFIG` script block:

```html
<script>
  /* Keep loans-page link URL in sync with the current P2L balance */
  document.addEventListener("DOMContentLoaded", function () {
    const balEl  = document.getElementById("balance");
    const link   = document.getElementById("loansPageLink");
    if (!balEl || !link) return;
    function syncLink() {
      const v = parseFloat(balEl.value);
      link.href = "/loans" + (v > 0 ? "?p2l=" + v : "");
    }
    balEl.addEventListener("input",  syncLink);
    balEl.addEventListener("change", syncLink);
    syncLink();
  });
</script>
```

- [ ] **Step 4: Verify pension page no longer has loan widgets**

```bash
python3 app.py &
sleep 2
curl -s http://localhost:5000 | grep -c "mortBalance"
kill %1
```

Expected: `0`.

- [ ] **Step 5: Verify loans page still has them**

```bash
python3 app.py &
sleep 2
curl -s http://localhost:5000/loans | grep -c "mortBalance"
kill %1
```

Expected: `2` (one for mortgage, one for consumer credit).

- [ ] **Step 6: Full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add templates/index.html
git commit -m \
  "feat: move loans to /loans page; add link with live P2L param"
```

---

## Post-implementation checklist

- [ ] Open `http://localhost:5000` — confirm no loan inputs visible
- [ ] Click "Kredītu kalkulators →" — confirm URL contains `?p2l=<value>`
- [ ] On `/loans`, confirm mortgage inputs pre-fill from `local_config.py`
- [ ] On `/loans`, toggle P2L on mortgage — confirm cascade uses the
  `#p2lBalance` input value
- [ ] Remove `local_config.py` temporarily and restart server — confirm
  app loads with demo defaults and bootstrap shows fixed fallback rates
  (10% / 7.5% / 3%)
- [ ] `git status` — confirm `local_config.py` does not appear
