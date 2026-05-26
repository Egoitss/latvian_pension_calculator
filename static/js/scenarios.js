// Scenario engine: Monte Carlo bootstrap, scenario button state,
// pillarResult accumulator, combined 3-pillar display.
import { bootstrapScenarioReturns } from "./calc.js";

function g(id) { return document.getElementById(id); }

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

// Cached bootstrap results and active scenario name
let scenarioRates = { positive: null, moderate: null, negative: null };
let activeScenario = "moderate";
// Latest result from each pillar widget (keyed p1/p2/p3)
const pillarState = { p1: null, p2: null, p3: null };

const SCENARIO_LABELS = {
  positive: "Pozitīvais scenārijs",
  moderate: "Mērenais scenārijs",
  negative: "Negatīvais scenārijs",
};

const LABEL_COLORS = {
  positive: "text-xs font-medium text-emerald-600",
  moderate: "text-xs font-medium text-slate-500",
  negative: "text-xs font-medium text-red-600",
};

// Write the active return to the shared-state div and fire change so
// ui.js and pension3.js (which listen to this element ID) recalculate.
function activateScenario(name) {
  if (scenarioRates[name] == null) return;
  activeScenario = name;
  const el = g("scenarioReturn");
  if (el) {
    el.dataset.value = String(scenarioRates[name]);
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  applyButtonStyles(name);
  const lbl = g("activeScenarioLabel");
  if (lbl) {
    lbl.textContent = SCENARIO_LABELS[name];
    lbl.className = LABEL_COLORS[name];
  }
}

const BTN_BASE =
  "flex-1 rounded-2xl border px-2 py-2 text-sm font-semibold transition";

function applyButtonStyles(active) {
  const styles = {
    positive: {
      on:  BTN_BASE + " border-emerald-600 bg-emerald-600 text-white",
      off: BTN_BASE + " border-emerald-300 bg-white text-emerald-700" +
           " hover:bg-emerald-50",
    },
    moderate: {
      on:  BTN_BASE + " border-slate-900 bg-slate-900 text-white",
      off: BTN_BASE + " border-slate-300 bg-white text-slate-600" +
           " hover:bg-slate-50",
    },
    negative: {
      on:  BTN_BASE + " border-red-600 bg-red-600 text-white",
      off: BTN_BASE + " border-red-300 bg-white text-red-600" +
           " hover:bg-red-50",
    },
  };
  Object.entries(styles).forEach(([name, cls]) => {
    const btn = g(`btn${name.charAt(0).toUpperCase() + name.slice(1)}`);
    if (btn) btn.className = cls[name === active ? "on" : "off"];
  });
}

function updateRateLabels() {
  const note = g("bootstrapNote");
  if (!scenarioRates.moderate) {
    if (note) note.textContent = "Monte Carlo aprēķins notiek…";
    return;
  }
  if (g("rateLabelPositive"))
    g("rateLabelPositive").textContent  = `${scenarioRates.positive.toFixed(2)}%`;
  if (g("rateLabelModerate"))
    g("rateLabelModerate").textContent  = `${scenarioRates.moderate.toFixed(2)}%`;
  if (g("rateLabelNegative"))
    g("rateLabelNegative").textContent  = `${scenarioRates.negative.toFixed(2)}%`;
  if (note) note.textContent =
    "10 000 simulācijas · Dinamika 18-49 Feb 2019–Mai 2026";
}

function updateCombinedDisplay() {
  const { p1, p2, p3 } = pillarState;
  if (!p1 || !p2 || !p3) return;

  // Nominal capital: P1 NDC capital + P2 final balance + P3 net payout
  const totalCapital = p1.finalCapital + p2.finalBalance + p3.netPayout;
  // Real capital: inflation-adjusted sum (P3 real balance before tax)
  const totalReal = p1.realCapital + p2.realBalance + p3.realBalance;

  if (g("combinedTotal"))
    g("combinedTotal").textContent = fmtEur(totalCapital);
  if (g("combinedRealTotal"))
    g("combinedRealTotal").textContent = `Šodienas naudā: ${fmtEur(totalReal)}`;

  // Monthly payout: P1 NDC + P2 after-tax + P3 monthly
  const monthly     = p1.monthly + p2.monthlyAfterTax + p3.monthlyPayout;
  const realMonthly = p1.realMonthly + p2.realMonthlyAfterTax + p3.realMonthlyPayout;
  if (g("combinedMonthly"))
    g("combinedMonthly").textContent = fmtEur(monthly);
  if (g("combinedRealMonthly"))
    g("combinedRealMonthly").textContent = `Šodienas naudā: ${fmtEur(realMonthly)}`;

  // P2 investment return (gains €)
  if (g("combinedP2Earnings"))
    g("combinedP2Earnings").textContent = fmtEur(p2.earnings);

  // P3 net gains after 25.5% IIN tax = gains × 0.745
  if (g("combinedP3NetGains"))
    g("combinedP3NetGains").textContent = fmtEur(p3.gains * 0.745);

  // Per-pillar capital breakdown
  if (g("breakdownP1")) g("breakdownP1").textContent = fmtEur(p1.finalCapital);
  if (g("breakdownP2")) g("breakdownP2").textContent = fmtEur(p2.finalBalance);
  if (g("breakdownP3")) g("breakdownP3").textContent = fmtEur(p3.netPayout);
}

function readRetirementMonths() {
  const birthYear  = parseInt(g("birthYear")?.value)     || new Date().getFullYear() - 30;
  const birthMonth = parseInt(g("birthMonth")?.value)    || 1;
  const retAge     = parseInt(g("retirementAge")?.value) || 65;
  const now = new Date();
  let age = now.getFullYear() - birthYear;
  if (now.getMonth() + 1 < birthMonth) age -= 1;
  return Math.max(12, (retAge - Math.max(0, age)) * 12);
}

function runBootstrap() {
  const numMonths = readRetirementMonths();
  scenarioRates = bootstrapScenarioReturns(numMonths);
  updateRateLabels();
  activateScenario(activeScenario);
}

document.addEventListener("DOMContentLoaded", () => {
  g("btnPositive")?.addEventListener("click", () => activateScenario("positive"));
  g("btnModerate")?.addEventListener("click", () => activateScenario("moderate"));
  g("btnNegative")?.addEventListener("click", () => activateScenario("negative"));

  document.addEventListener("pillarResult", (evt) => {
    const { pillar, ...data } = evt.detail;
    pillarState[`p${pillar}`] = data;
    updateCombinedDisplay();
  });

  // Re-run bootstrap when retirement horizon changes
  ["birthYear", "birthMonth", "retirementAge"].forEach(id => {
    g(id)?.addEventListener("change", runBootstrap);
    g(id)?.addEventListener("input",  runBootstrap);
  });

  // Defer one tick: ensures ui.js/pension1.js/pension3.js DOMContentLoaded
  // handlers have registered their listeners before the first change event fires.
  setTimeout(runBootstrap, 0);
});
