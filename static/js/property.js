// Property value estimator — reads main calculator inputs
// CAGR source: Arco Real Estate / Latio market reviews 2010–2024
import { PROPERTY_SCENARIO_RATES } from "./data.js";
import { savePropType, loadPropType } from "./storage.js";

const CRASH_RATE = 0.60; // Latvia 2007–2010 worst case

let locType        = "city";
let activeScenario = "moderate";

function g(id) { return document.getElementById(id); }

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

function projectProp(price, rate, t) {
  return price * Math.pow(1 + rate, t);
}

// Fractional years from now until retirement
function yrsToRetirement() {
  const now  = new Date();
  const curY = now.getFullYear();
  const curM = now.getMonth() + 1;
  const bY   = parseInt((g("birthYear")     || {}).value) || 1982;
  const bM   = parseInt((g("birthMonth")    || {}).value) || 8;
  const retA = parseInt((g("retirementAge") || {}).value) || 65;
  return Math.max(0, ((bY + retA) * 12 + bM - curY * 12 - curM) / 12);
}

function recalc() {
  const price = parseFloat((g("propPrice") || {}).value);
  if (!price || price <= 0) {
    g("propResults").classList.add("hidden");
    document.dispatchEvent(new CustomEvent("propertyResult", {
      detail: { retEquity: 0, retEquityReal: 0, rows: [] },
    }));
    return;
  }

  const rate      = (parseFloat(g("propRate")?.value) || 0) / 100;
  const inflRate  = (parseFloat((g("inflation") || {}).value) || 4.16) / 100;
  const yRet      = yrsToRetirement();
  // Negative scenario: apply 2007–2010-style crash at t=0 before appreciation
  const basePrice = activeScenario === "negative" ? price * (1 - CRASH_RATE) : price;

  // Retirement year label
  const bY   = parseInt((g("birthYear")     || {}).value) || 1982;
  const retA = parseInt((g("retirementAge") || {}).value) || 65;
  g("propRetYearHeader").textContent = `${bY + retA}. ${t("g.")}`;

  // Project to retirement — mortgage assumed paid off by then
  const nominal = projectProp(basePrice, rate, yRet);
  const real    = nominal / Math.pow(1 + inflRate, yRet);

  // Integer-year series for the chart (age → property value)
  const fullYears = Math.ceil(yRet);
  const startAge  = bY + retA - fullYears;
  const propRows  = [];
  for (let i = 0; i <= fullYears; i++) {
    propRows.push({
      age:     startAge + i,
      balance: Math.round(projectProp(basePrice, rate, i)),
    });
  }

  g("propRetNominal").textContent = fmtEur(nominal);
  g("propRetReal").textContent    = fmtEur(real);

  g("propCrashNote")?.classList.toggle("hidden", activeScenario !== "negative");

  document.dispatchEvent(new CustomEvent("propertyResult", {
    detail: { retEquity: nominal, retEquityReal: real, rows: propRows },
  }));

  g("propResults").classList.remove("hidden");
}

const PILL_ON  = "rounded-xl border border-slate-900 bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white transition";
const PILL_OFF = "rounded-xl border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 transition hover:border-slate-400";

const MODERATE_NOTES = {
  city:     t("~6.2% per year nominal (Riga, 2010–2024 · Arco/Latio)"),
  valmiera: t("~5.5% per year nominal (Valmiera, 2010–2024 · Arco/Latio; few new projects)"),
  rural:    t("~2.5% per year nominal (rural, 2010–2024)"),
};

const SCENARIO_BADGE = {
  positive: { cls: "bg-emerald-100 text-emerald-700", label: t("Positive") },
  moderate: { cls: "bg-slate-100 text-slate-600",     label: t("Moderate") },
  negative: { cls: "bg-red-100 text-red-600",         label: t("Negative") },
};

function updateScenarioBadge() {
  const badge = g("propScenarioBadge");
  if (!badge) return;
  const { cls, label } = SCENARIO_BADGE[activeScenario];
  badge.className = `rounded-full px-1.5 py-0.5 text-[10px] font-medium ${cls}`;
  badge.textContent = label;
}

function buildRateNote(scenario, loc) {
  if (scenario === "moderate") return MODERATE_NOTES[loc];
  const pct   = (PROPERTY_SCENARIO_RATES[scenario][loc] * 100).toFixed(1);
  const label = scenario === "positive" ? t("positive scenario") : t("negative scenario");
  return `~${pct}% ${t("per year")} (${label})`;
}

// Show the slider's current % in the label.
function updatePropRateDisplay() {
  const el = g("propRate"), disp = g("propRateDisplay");
  if (el && disp) disp.textContent = `${parseFloat(el.value).toFixed(1)}%`;
}

// Point the slider at the current scenario × location rate. The user
// can then fine-tune it; the projection always reads the slider.
function syncRateSlider() {
  const el = g("propRate");
  if (!el) return;
  el.value = (PROPERTY_SCENARIO_RATES[activeScenario][locType] * 100)
    .toFixed(1);
  updatePropRateDisplay();
}

function setLocType(type) {
  locType = type;
  savePropType(type);
  g("propTypeCity").className     = type === "city"     ? PILL_ON : PILL_OFF;
  g("propTypeValmiera").className = type === "valmiera" ? PILL_ON : PILL_OFF;
  g("propTypeRural").className    = type === "rural"    ? PILL_ON : PILL_OFF;
  g("propRateNote").textContent = buildRateNote(activeScenario, type);
  updateScenarioBadge();
  syncRateSlider();
  recalc();
}

document.addEventListener("DOMContentLoaded", () => {
  g("propTypeCity").addEventListener("click",     () => setLocType("city"));
  g("propTypeValmiera").addEventListener("click", () => setLocType("valmiera"));
  g("propTypeRural").addEventListener("click",    () => setLocType("rural"));

  const sharedInputs = [
    "propPrice", "inflation", "birthYear", "birthMonth", "retirementAge",
  ];
  sharedInputs.forEach(id => {
    const el = g(id);
    if (el) ["input", "change"].forEach(evt => el.addEventListener(evt, recalc));
  });

  // Slider: user fine-tunes the appreciation rate → redisplay + recalc.
  const slider = g("propRate");
  if (slider) ["input", "change"].forEach(evt =>
    slider.addEventListener(evt, () => {
      updatePropRateDisplay();
      recalc();
    }));

  document.addEventListener("scenarioChange", ({ detail }) => {
    activeScenario = detail.name;
    setLocType(locType);
  });

  // Restore location type from localStorage; fall back to server default
  const card = document.querySelector("[data-prop-type]");
  const savedType = loadPropType();
  setLocType(savedType || (card ? card.dataset.propType : "city"));
});
