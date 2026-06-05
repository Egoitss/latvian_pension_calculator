# localStorage Personal Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all personal financial form values out of the
`local_config.py` / `OVERRIDES` pattern into browser localStorage,
making it structurally impossible to leak personal data via git.

**Architecture:** A new `storage.js` ES module owns all localStorage
read/write. `ui.js` calls `loadInputs()` on init and saves after each
change. `property.js` restores the location-type button. Flask's
`OVERRIDES` merge is deleted — `DEFAULTS` holds demo values only. Key
inputs (`balance`, `grossMonthly`) lose their server-rendered `value`
and gain a `placeholder` so they appear as gray shadows until the user
types. `local_config.py` is reduced to NAV series + P3 cost basis (not
sensitive form values).

**Tech Stack:** Vanilla ES modules, Web Storage API, Python/Flask, Jinja2.

---

## File map

| Action | File | What changes |
|--------|------|-------------|
| Create | `static/js/storage.js` | localStorage save/load for all inputs + gender + propType |
| Modify | `static/js/ui.js` | import; `saveGender` in `setGender`; init sequence |
| Modify | `static/js/property.js` | import; `savePropType` in `setLocType`; restore on init |
| Modify | `templates/_pension2.html` | `balance` → placeholder only |
| Modify | `templates/_controls.html` | `grossMonthly` → placeholder only |
| Modify | `app.py:80-84` | delete OVERRIDES try/except (5 lines) |
| Modify | `local_config.example.py` | remove OVERRIDES section, keep NAV/cost-basis |
| Modify | `README.md` | replace security note with localStorage explanation |

---

### Task 1 — Create `static/js/storage.js`

**Files:**
- Create: `static/js/storage.js`

No pytest tests for browser localStorage. Smoke-tested manually in Task 7.

- [ ] **Step 1: Write `static/js/storage.js`**

```javascript
// localStorage persistence for all calculator inputs.
// Imported by ui.js and property.js — runs once (ES module singleton).

// All tracked input IDs mapped to the element property to read/write.
// "value" covers text, number, range, and select elements.
// "checked" covers checkboxes.
const INPUTS = {
  birthYear:        "value",
  birthMonth:       "value",
  retirementAge:    "value",
  balance:          "value",
  p2AlreadyEarned:  "value",
  grossMonthly:     "value",
  selectedPlan:     "value",
  manualReturn:     "value",
  salaryGrowth:     "value",
  inflation:        "value",
  p2lRate:          "value",
  payoutYears:      "value",
  enableSwitching:  "checked",
  switchOneAge:     "value",
  switchOnePlan:    "value",
  switchTwoAge:     "value",
  switchTwoPlan:    "value",
  p1Capital:        "value",
  p1RecordYears:    "value",
  p1RecordMonths:   "value",
  p1RevalRate:      "value",
  p3Balance:        "value",
  p3Monthly:        "value",
  p3ContribGrowth:  "value",
  p3PlanName:       "value",
  propPrice:        "value",
};

const KEY          = "pensija_v1";
const GENDER_KEY   = "pensija_gender";
const PROPTYPE_KEY = "pensija_proptype";

// Read all tracked inputs and persist to localStorage.
export function saveInputs() {
  const data = {};
  for (const [id, prop] of Object.entries(INPUTS)) {
    const el = document.getElementById(id);
    if (!el) continue;
    const val = el[prop];
    // Skip empty optional inputs — leave them blank on restore too.
    if (val === "" || val === null || val === undefined) continue;
    data[id] = val;
  }
  try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (_) {}
}

// Fill all tracked inputs from localStorage without firing DOM events.
// Must be called before onInputChange() so the first calc uses saved values.
export function loadInputs() {
  let data;
  try {
    data = JSON.parse(localStorage.getItem(KEY) || "null");
  } catch (_) { return; }
  if (!data) return;
  for (const [id, prop] of Object.entries(INPUTS)) {
    if (!(id in data)) continue;
    const el = document.getElementById(id);
    if (el) el[prop] = data[id];
  }
}

export function saveGender(g) {
  try { localStorage.setItem(GENDER_KEY, g); } catch (_) {}
}
export function loadGender() {
  try { return localStorage.getItem(GENDER_KEY) || "men"; }
  catch (_) { return "men"; }
}

export function savePropType(type) {
  try { localStorage.setItem(PROPTYPE_KEY, type); } catch (_) {}
}
export function loadPropType() {
  try { return localStorage.getItem(PROPTYPE_KEY) || null; }
  catch (_) { return null; }
}

// Auto-save whenever any tracked input changes.
document.addEventListener("DOMContentLoaded", () => {
  for (const id of Object.keys(INPUTS)) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.addEventListener("change", saveInputs);
    el.addEventListener("input",  saveInputs);
  }
});
```

- [ ] **Step 2: Verify line count**

```bash
wc -l static/js/storage.js
```

Expected: ≤ 80 lines.

- [ ] **Step 3: Commit**

```bash
git add static/js/storage.js
git commit -m "feat: add storage.js — localStorage persistence for all inputs"
```

---

### Task 2 — Wire `storage.js` into `ui.js`

**Files:**
- Modify: `static/js/ui.js`

Three targeted edits: add import, add `saveGender` call, update init tail.

- [ ] **Step 1: Add import at top of `ui.js`**

Find the last import line (currently `import { initChart, drawChart } from "./chart.js";`).
Add one line immediately after:

```javascript
import { loadInputs, loadGender, saveGender } from "./storage.js";
```

- [ ] **Step 2: Add `saveGender` inside `setGender`**

Find the `setGender` function (the one that takes `g` and updates button
classes). Add `saveGender(g)` as the second line:

```javascript
function setGender(g) {
  gender = g;
  saveGender(g);
  el("genderMale").className   = g === "men"   ? GENDER_ACTIVE : GENDER_INACTIVE;
  el("genderFemale").className = g === "women" ? GENDER_ACTIVE : GENDER_INACTIVE;
  onInputChange(chart);
}
```

- [ ] **Step 3: Update the DOMContentLoaded init tail**

Find the last two lines of the DOMContentLoaded handler:

```javascript
  // Sync retirement age from birth year before first calculation
  syncRetirementAge();
  // Run initial update to populate all outputs from default values
  onInputChange(chart);
```

Replace with:

```javascript
  // Restore gender button state from localStorage (no recalc yet)
  gender = loadGender();
  el("genderMale").className   = gender === "men"   ? GENDER_ACTIVE : GENDER_INACTIVE;
  el("genderFemale").className = gender === "women" ? GENDER_ACTIVE : GENDER_INACTIVE;
  // Compute projected retirement age as a baseline default
  syncRetirementAge();
  // Restore saved inputs — overwrites syncRetirementAge if retirementAge was saved
  loadInputs();
  // Run initial calculation with fully restored values
  onInputChange(chart);
```

- [ ] **Step 4: Start server, check console**

```bash
python3 app.py
```

Open http://localhost:5001 in browser → DevTools Console → expect zero errors.

- [ ] **Step 5: Commit**

```bash
git add static/js/ui.js
git commit -m "feat: ui.js — restore gender + all inputs from localStorage on init"
```

---

### Task 3 — Wire `storage.js` into `property.js`

**Files:**
- Modify: `static/js/property.js`

Two targeted edits: add import + `savePropType`, update init.

- [ ] **Step 1: Add import at top of `property.js`**

Find the existing import (line 3: `import { PROPERTY_SCENARIO_RATES } from "./data.js";`).
Add one line immediately after:

```javascript
import { savePropType, loadPropType } from "./storage.js";
```

- [ ] **Step 2: Add `savePropType` inside `setLocType`**

Find `function setLocType(type)`. Add `savePropType(type)` as the second line:

```javascript
function setLocType(type) {
  locType = type;
  savePropType(type);
  g("propTypeCity").className     = type === "city"     ? PILL_ON : PILL_OFF;
  g("propTypeValmiera").className = type === "valmiera" ? PILL_ON : PILL_OFF;
  g("propTypeRural").className    = type === "rural"    ? PILL_ON : PILL_OFF;
  g("propRateNote").textContent = buildRateNote(activeScenario, type);
  updateScenarioBadge();
  recalc();
}
```

- [ ] **Step 3: Update the DOMContentLoaded init tail**

Find the last 3 lines of the DOMContentLoaded handler:

```javascript
  // Initialise location type and price from server-side defaults
  const card = document.querySelector("[data-prop-type]");
  if (card) setLocType(card.dataset.propType);
  else recalc();
```

Replace with:

```javascript
  // Restore location type from localStorage; fall back to server default
  const card = document.querySelector("[data-prop-type]");
  const savedType = loadPropType();
  setLocType(savedType || (card ? card.dataset.propType : "city"));
```

- [ ] **Step 4: Commit**

```bash
git add static/js/property.js
git commit -m "feat: property.js — restore propType from localStorage on init"
```

---

### Task 4 — Convert sensitive inputs to placeholder-only

Removing the server-rendered `value` from `balance` and `grossMonthly`
makes them visually empty on first visit (gray hint text only). localStorage
fills them on return visits. This is the "shadow" effect.

**Files:**
- Modify: `templates/_pension2.html`
- Modify: `templates/_controls.html`

- [ ] **Step 1: Convert `balance` in `_pension2.html`**

Find the `balance` input (around line 54):

```html
          <input id="balance" type="number" step="0.01"
                 value="{{ defaults.balance }}"
                 class="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2
                        text-sm outline-none transition focus:border-slate-500
                        focus:ring-2 focus:ring-slate-200" />
```

Replace with (add `placeholder`, remove `value`):

```html
          <input id="balance" type="number" step="0.01"
                 placeholder="{{ defaults.balance }}"
                 class="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2
                        text-sm outline-none transition focus:border-slate-500
                        focus:ring-2 focus:ring-slate-200" />
```

- [ ] **Step 2: Convert `grossMonthly` in `_controls.html`**

Find the `grossMonthly` input (around line 79):

```html
        <input id="grossMonthly" type="number" step="any"
               value="{{ defaults.gross_monthly }}"
               class="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2
                      text-sm outline-none transition focus:border-slate-500
                      focus:ring-2 focus:ring-slate-200" />
```

Replace with:

```html
        <input id="grossMonthly" type="number" step="any"
               placeholder="{{ defaults.gross_monthly }}"
               class="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2
                      text-sm outline-none transition focus:border-slate-500
                      focus:ring-2 focus:ring-slate-200" />
```

- [ ] **Step 3: Verify first-visit empty state in browser**

Open http://localhost:5001 in a fresh private window. Confirm:
- `grossMonthly` and `balance` show gray hint text, not black values
- Pension section shows "—" until a value is typed (expected)

- [ ] **Step 4: Commit**

```bash
git add templates/_pension2.html templates/_controls.html
git commit -m "feat: balance + grossMonthly as placeholder shadows (not pre-filled)"
```

---

### Task 5 — Remove OVERRIDES from `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Delete the OVERRIDES block**

Find and remove exactly these 5 lines (around line 80, between `DEFAULTS = {...}` and
the `LOCAL_DATA` block):

```python
try:
    from local_config import OVERRIDES
    DEFAULTS = {**DEFAULTS, **OVERRIDES}
except ImportError:
    pass
```

- [ ] **Step 2: Verify server starts and serves demo values**

```bash
python3 app.py
```

Open http://localhost:5001. Confirm `balance` and `grossMonthly` show
gray placeholder text (not any value from your `local_config.py`).
The sliders should show their DEFAULTS values (salaryGrowth=2, inflation=2.5, etc.).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "refactor: remove OVERRIDES merge — personal form values now in localStorage"
```

---

### Task 6 — Simplify `local_config.example.py`

**Files:**
- Modify: `local_config.example.py` (full rewrite — shorter)

- [ ] **Step 1: Rewrite the file**

```python
# Copy this file to local_config.py and fill in your own values.
# local_config.py is gitignored — it will never be committed.
#
# You only need this file for personalised Monte Carlo simulations using
# your own Dinamika 18-49 NAV history.
# All form values (balance, salary, birth year, etc.) are saved
# automatically in your browser's localStorage — they never leave your
# machine or touch the server.

# Historical Dinamika 18-49 NAV prices (monthly, from Swedbank CSV export).
# Must have at least 2 values. Leave as [] to use fixed fallback rates
# (10% / 7.5% / 3%) for the three scenario buttons.
_DINAMIKA_PRICES = []

# Your P3 cost basis accumulated BEFORE the simulation window (EUR).
# Set to 0.0 if all contributions happen within the simulation period.
P3_COST_BASIS = 0.0
```

- [ ] **Step 2: Commit**

```bash
git add local_config.example.py
git commit -m "docs: simplify local_config.example — OVERRIDES no longer needed"
```

---

### Task 7 — Manual smoke-test

No code changes. End-to-end verification of localStorage persistence.

- [ ] **Step 1: Clear any stale localStorage**

DevTools → Application → Storage → localStorage → delete `pensija_v1`,
`pensija_gender`, `pensija_proptype`.

- [ ] **Step 2: First-visit state**

Reload http://localhost:5001.

Expected:
- `balance` and `grossMonthly`: empty, gray placeholder text visible
- Sliders: demo values (salaryGrowth 2%, inflation 2.5%)
- P1/P3/Property accordions: collapsed, inputs empty

- [ ] **Step 3: Enter values and verify persistence**

Type `2500` in grossMonthly and `15000` in balance. Press Tab.

Expected: calculator shows P2L results. Refresh page.

Expected after refresh: `grossMonthly` shows `2500`, `balance` shows `15000`
(restored from localStorage). `pensija_v1` key visible in DevTools.

- [ ] **Step 4: Gender and propType persistence**

Click ♀ Sieviete, click Valmiera. Refresh.

Expected: ♀ button active, Valmiera button active after refresh.
DevTools: `pensija_gender` = `"women"`, `pensija_proptype` = `"valmiera"`.

- [ ] **Step 5: Incognito isolation**

Open the URL in a new incognito window.

Expected: empty inputs (gray placeholders), not your personal values.

- [ ] **Step 6: Verify `local_config.py` OVERRIDES are gone**

Restart server. If your `local_config.py` still has an `OVERRIDES` dict,
confirm the page ignores it — the form is driven by localStorage only.

---

### Task 8 — Update `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the Security note section**

Find:

```markdown
## Security note

`local_config.py` contains personal financial data and is listed in
`.gitignore`. Never force-add it or override `.gitignore`. All values in
committed files are imaginary demo figures.
```

Replace with:

```markdown
## Personal data

Form values (salary, balances, birth year, etc.) are saved automatically
in browser localStorage — they never touch the server or appear in git.
On first visit the form shows empty inputs with gray demo hints; your
saved values load on every return visit. Clearing browser storage resets
to demo defaults.

`local_config.py` is only needed to supply historical Dinamika 18-49 NAV
prices for personalised Monte Carlo simulations. Without it the three
scenario buttons use fixed fallback rates (10% / 7.5% / 3%).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README — localStorage replaces local_config OVERRIDES"
```
