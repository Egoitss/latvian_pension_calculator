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

  const rate      = PROPERTY_SCENARIO_RATES[activeScenario][locType];
  const inflRate  = (parseFloat((g("inflation") || {}).value) || 4.16) / 100;
  const yRet      = yrsToRetirement();
  // Negative scenario: apply 2007–2010-style crash at t=0 before appreciation
  const basePrice = activeScenario === "negative" ? price * (1 - CRASH_RATE) : price;

  // Retirement year label
  const bY   = parseInt((g("birthYear")     || {}).value) || 1982;
  const retA = parseInt((g("retirementAge") || {}).value) || 65;
  g("propRetYearHeader").textContent = `${bY + retA}. g.`;

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
  city:     "~6.2% gadā nominālais (Rīga, 2010–2024 · Arco/Latio)",
  valmiera: "~5.5% gadā nominālais (Valmiera, 2010–2024 · Arco/Latio; maz jaunu projektu)",
  rural:    "~2.5% gadā nominālais (lauki, 2010–2024)",
};

const SCENARIO_BADGE = {
  positive: { cls: "bg-emerald-100 text-emerald-700", label: "Pozitīvais" },
  moderate: { cls: "bg-slate-100 text-slate-600",     label: "Mērenais"   },
  negative: { cls: "bg-red-100 text-red-600",         label: "Negatīvais" },
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
  const label = scenario === "positive" ? "pozitīvais scenārijs" : "negatīvais scenārijs";
  return `~${pct}% gadā (${label})`;
}

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

  document.addEventListener("scenarioChange", ({ detail }) => {
    activeScenario = detail.name;
    setLocType(locType);
  });

  // Restore location type from localStorage; fall back to server default
  const card = document.querySelector("[data-prop-type]");
  const savedType = loadPropType();
  setLocType(savedType || (card ? card.dataset.propType : "city"));
});
