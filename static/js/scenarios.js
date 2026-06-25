// Scenario engine: Monte Carlo bootstrap, scenario button state,
// pillarResult accumulator, combined 3-pillar display.
import { bootstrapScenarioReturns } from "./calc.js";

function g(id) { return document.getElementById(id); }

// Update the mobile bottom-bar value, fading it in only when it changes.
function setMobileBarValue(text) {
  const el = g("mobileBarValue");
  if (!el || el.textContent === text) return;
  el.textContent = text;
  el.classList.remove("mb-flash");
  void el.offsetWidth;            // restart the 200ms fade animation
  el.classList.add("mb-flash");
}

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
// Property equity at retirement (0 when no price entered)
let propEquity = 0;
let propEquityReal = 0;
// Year-by-year rows from each pillar (for the combined chart)
const pillarRows = { p1: null, p2: null, p3: null };
let propChartRows = [];

const SCENARIO_LABELS = {
  positive: t("Positive scenario"),
  moderate: t("Moderate scenario"),
  negative: t("Negative scenario"),
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
  const summaryBadge = g("summaryScenarioLabel");
  if (summaryBadge) {
    summaryBadge.className = "scenario-chip is-" + name;
    summaryBadge.textContent =
      name === "positive" ? t("Positive") :
      name === "negative" ? t("Negative") : t("Moderate");
  }
  document.dispatchEvent(new CustomEvent("scenarioChange", { detail: { name } }));
}

const BTN_BASE =
  "w-full rounded-2xl border px-2 py-2 text-sm font-semibold transition";

function applyButtonStyles(active) {
  const styles = {
    positive: {
      on:  BTN_BASE + " border-emerald-400 bg-emerald-600 text-white",
      off: BTN_BASE + " border-emerald-400 bg-white text-emerald-600" +
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
    if (note) note.textContent = t("Running Monte Carlo…");
    return;
  }
  if (g("rateLabelPositive"))
    g("rateLabelPositive").textContent  = `${scenarioRates.positive.toFixed(2)}%`;
  if (g("rateLabelModerate"))
    g("rateLabelModerate").textContent  = `${scenarioRates.moderate.toFixed(2)}%`;
  if (g("rateLabelNegative"))
    g("rateLabelNegative").textContent  = `${scenarioRates.negative.toFixed(2)}%`;
  if (note) note.textContent =
    t("10,000 simulations · Dinamika 18-49 Feb 2019–May 2026");
}

function updateCombinedDisplay() {
  const { p1, p2, p3 } = pillarState;
  if (!p1 || !p2 || !p3) return;

  // Nominal capital: P1 NDC + P2 + P3 + property equity at retirement
  const totalCapital =
    p1.finalCapital + p2.finalBalance + p3.netPayout + propEquity;
  // Real capital: inflation-adjusted sum including property real value
  const totalReal =
    p1.realCapital + p2.realBalance + p3.realBalance + propEquityReal;

  if (g("combinedTotal"))
    g("combinedTotal").textContent = fmtEur(totalCapital);
  if (g("combinedRealTotal"))
    g("combinedRealTotal").textContent = `${t("In today's money:")} ${fmtEur(totalReal)}`;

  // Capital label — update both card and sticky bar when property is included
  const capLabel = propEquity > 0 ? t("Net value") : t("Total capital");
  if (g("summaryCapital")) g("summaryCapital").textContent = fmtEur(totalCapital);
  if (g("summaryCapitalLabel")) g("summaryCapitalLabel").textContent = capLabel;
  if (g("combinedCapitalLabel")) g("combinedCapitalLabel").textContent = capLabel;

  // Monthly payout: P1 NDC + P2 after-tax + P3 monthly
  const monthly     = p1.monthly + p2.monthlyAfterTax + p3.monthlyPayout;
  const realMonthly = p1.realMonthly + p2.realMonthlyAfterTax + p3.realMonthlyPayout;
  // Lead with real (today's money); nominal is the secondary line.
  if (g("combinedRealMonthly"))
    g("combinedRealMonthly").textContent = fmtEur(realMonthly);
  if (g("combinedMonthly"))
    g("combinedMonthly").textContent = fmtEur(monthly);

  // Sticky bar
  if (g("summaryMonthly")) g("summaryMonthly").textContent = fmtEur(monthly);
  if (g("summaryRealMonthly")) g("summaryRealMonthly").textContent = fmtEur(realMonthly);
  setMobileBarValue(fmtEur(realMonthly));   // mobile bottom bar (today's money)

  // P2 investment return (gains €)
  if (g("combinedP2Earnings"))
    g("combinedP2Earnings").textContent = fmtEur(p2.earnings);

  // P3 net gains after 25.5% IIN tax = gains × 0.745
  if (g("combinedP3NetGains"))
    g("combinedP3NetGains").textContent = fmtEur(p3.gains * 0.745);

  // Per-pillar capital breakdown (property column shown only when price entered)
  if (g("breakdownP1")) g("breakdownP1").textContent = fmtEur(p1.finalCapital);
  if (g("breakdownP2")) g("breakdownP2").textContent = fmtEur(p2.finalBalance);
  if (g("breakdownP3")) g("breakdownP3").textContent = fmtEur(p3.netPayout);
  const propWrapper = g("breakdownPropWrapper");
  if (propWrapper) {
    propWrapper.classList.toggle("hidden", propEquity <= 0);
    if (g("breakdownProp")) g("breakdownProp").textContent = fmtEur(propEquity);
  }
}

// Merge all pillar year-series and dispatch to chart.js via ui.js listener
function updateCombinedChart() {
  const p2rows = pillarRows.p2;
  if (!p2rows || p2rows.length === 0) return;

  const infl = (parseFloat(g("inflation")?.value) || 4) / 100;
  const p1Map   = new Map((pillarRows.p1 || []).map(r => [r.age, r.balance]));
  const p3Map   = new Map((pillarRows.p3 || []).map(r => [r.age, r.balance]));
  const propMap = new Map(propChartRows.map(r => [r.age, r.balance]));

  const rows = p2rows.map((row, i) => {
    const p1   = p1Map.get(row.age)   || 0;
    const p2   = row.total;
    const p3   = p3Map.get(row.age)   || 0;
    const prop = propMap.get(row.age) || 0;
    // Cumulative sums for fill:'-1' stacked areas
    const cum1 = p1;
    const cum2 = p1 + p2;
    const cum3 = p1 + p2 + p3;
    const cum4 = p1 + p2 + p3 + prop;
    const deflator = Math.pow(1 + infl, i) || 1;
    return {
      age: row.age,
      activePlan: row.activePlan,
      cum1, cum2, cum3, cum4,
      realTotal: Math.round(cum4 / deflator),
    };
  });

  document.dispatchEvent(
    new CustomEvent("combinedChartData", { detail: { rows } })
  );
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

  document.addEventListener("propertyResult", ({ detail }) => {
    propEquity     = detail.retEquity     || 0;
    propEquityReal = detail.retEquityReal || 0;
    propChartRows  = detail.rows          || [];
    updateCombinedDisplay();
    updateCombinedChart();
  });

  document.addEventListener("pillarResult", (evt) => {
    const { pillar, rows, ...data } = evt.detail;
    pillarState[`p${pillar}`] = data;
    if (rows) pillarRows[`p${pillar}`] = rows;
    updateCombinedDisplay();
    updateCombinedChart();
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
