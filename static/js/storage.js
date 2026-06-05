// localStorage persistence for all calculator inputs.
// Imported by ui.js and property.js — runs once (ES module singleton).

// All tracked input IDs mapped to the element property to read/write.
// "value" covers text, number, range, and select elements.
// "checked" covers checkboxes.
const INPUTS = {
  birthYear:        "value",
  birthMonth:       "value",
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

// Bump version string to invalidate stored data when input IDs change.
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

export function saveGender(gender) {
  try { localStorage.setItem(GENDER_KEY, gender); } catch (_) {}
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
