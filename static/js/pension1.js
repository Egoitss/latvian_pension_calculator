// 1st-pillar NDC pension estimator
// Own inputs: p1Capital, p1RecordYears, p1RecordMonths, p1RevalRate
// Shared inputs: grossMonthly, salaryGrowth, inflation, retirementAge, birthYear, birthMonth
import { CONSTANTS, getGCoefficient } from "./data.js";

const { VSAOI_CEILING } = CONSTANTS;

// Long-run 1st-pillar contribution rate (14% of gross credited to NDC).
// Note: temporarily 15% in 2025–2028 by legislation; reverts to 14% in 2029.
const P1_RATE = 0.14;

// Scenario adjustment to the wage-linked NDC revaluation (pp): a
// weak/strong economy dampens/boosts indexation. Moderate is the
// neutral baseline set by the slider. Tunable.
const REVAL_DELTA = { negative: -2, moderate: 0, positive: 2 };
let scenarioName = "moderate";

function g(id) { return document.getElementById(id); }

// Effective revaluation = slider baseline shifted by the active
// scenario, floored at 0.
function effectiveReval() {
  const base = parseFloat(g("p1RevalRate")?.value) || 0;
  return Math.max(0, base + (REVAL_DELTA[scenarioName] || 0));
}

// Reflect the effective (scenario-adjusted) rate in the slider label.
function syncRevalDisplay() {
  const d = g("p1RevalDisplay");
  if (d) d.textContent = `${effectiveReval().toFixed(2)}%`;
}

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

function ageFromBirth(birthYear, birthMonth) {
  const now = new Date();
  let age = now.getFullYear() - birthYear;
  if (now.getMonth() + 1 < birthMonth) age -= 1;
  return Math.max(0, age);
}

// Year-by-year NDC capital accumulation — mirrors calculator.py:calculate_p1_projection
function calculateP1Projection({
  age, retirementAge, currentCapital,
  grossMonthly, salaryGrowth, revaluationRate,
}) {
  const safeAge = Math.max(0, Math.round(age));
  const safeRet = Math.max(safeAge, Math.round(retirementAge));
  let capital = Math.max(0, currentCapital);
  let annualGross = Math.max(0, grossMonthly) * 12;
  const growth = salaryGrowth / 100;
  const reval = revaluationRate / 100;
  const years = Math.max(0, safeRet - safeAge);

  const rows = [];
  for (let i = 0; i < years; i++) {
    // Revalue at year start, then credit this year's contributions
    capital *= (1 + reval);
    capital += Math.min(annualGross, VSAOI_CEILING) * P1_RATE;
    annualGross *= (1 + growth);
    rows.push({ age: safeAge + i + 1, balance: Math.round(capital) });
  }
  return { finalCapital: Math.round(capital), years, rows };
}

// Show insurance record eligibility status below the stāžs inputs
function updateEligibilityHint(totalMonths) {
  const hint = g("p1EligibilityHint");
  if (!hint) return;
  const years = Math.floor(totalMonths / 12);
  const months = totalMonths % 12;
  const label = months > 0 ? `${years} ${t("yrs")} ${months} ${t("mo.")}` : `${years} ${t("yrs")}`;
  if (totalMonths >= 20 * 12) {
    hint.textContent = `${t("Service record:")} ${label} ✓ (${t("min. 20 yrs")})`;
    hint.className = "text-[10px] text-emerald-600";
  } else if (totalMonths > 0) {
    hint.textContent = `${t("Service record:")} ${label} — ${t("insufficient (min. 20 yrs)")}`;
    hint.className = "text-[10px] text-amber-600";
  } else {
    hint.textContent = "";
  }
}

function recalc() {
  const capital = Math.round(parseFloat(g("p1Capital")?.value) || 0);

  // Always update eligibility hint regardless of capital
  const recordYears  = parseInt(g("p1RecordYears")?.value)  || 0;
  const recordMonths = parseInt(g("p1RecordMonths")?.value) || 0;
  updateEligibilityHint(recordYears * 12 + recordMonths);

  if (capital <= 0) {
    g("p1Results").classList.add("hidden");
    g("p1AnnualContrib").textContent = "—";
    // Emit zeroed result so the combined totals/chart drop the old
    // pillar-1 value instead of keeping a stale number on clear.
    document.dispatchEvent(new CustomEvent("pillarResult", {
      detail: {
        pillar: 1,
        finalCapital: 0, realCapital: 0,
        monthly: 0, realMonthly: 0, rows: [],
      },
    }));
    return;
  }

  const birthYear  = parseInt(g("birthYear")?.value)      || new Date().getFullYear() - 30;
  const birthMonth = parseInt(g("birthMonth")?.value)     || 1;
  const retAge     = parseInt(g("retirementAge")?.value)  || 65;
  const gross      = parseFloat(g("grossMonthly")?.value) || 0;
  const salGrowth  = parseFloat(g("salaryGrowth")?.value) || 0;
  const inflation  = parseFloat(g("inflation")?.value)    || 0;
  const revalRate  = effectiveReval();
  const age        = ageFromBirth(birthYear, birthMonth);

  // Annual 1st-pillar contribution at current gross
  const annualGross = Math.max(0, gross) * 12;
  const annualP1 = Math.min(annualGross, VSAOI_CEILING) * P1_RATE;
  g("p1AnnualContrib").textContent = fmtEur(annualP1);

  const { finalCapital, years, rows } = calculateP1Projection({
    age, retirementAge: retAge, currentCapital: capital,
    grossMonthly: gross, salaryGrowth: salGrowth,
    revaluationRate: revalRate,
  });

  const gCoef        = getGCoefficient(retAge);
  const monthly      = finalCapital / (gCoef * 12);
  const realDiscount = Math.pow(1 + inflation / 100, years);
  const realMonthly  = realDiscount > 0 ? monthly / realDiscount : monthly;

  g("p1FinalCapital").textContent = fmtEur(finalCapital);
  g("p1Monthly").textContent      = fmtEur(monthly);
  g("p1RealMonthly").textContent  = fmtEur(realMonthly);
  g("p1GDisplay").textContent     = `G = ${gCoef.toFixed(2)} ${t("yrs")}`;
  g("p1Results").classList.remove("hidden");

  const realCapital = realDiscount > 0
    ? Math.round(finalCapital / realDiscount) : Math.round(finalCapital);

  document.dispatchEvent(new CustomEvent("pillarResult", {
    detail: {
      pillar: 1,
      finalCapital: Math.round(finalCapital),
      realCapital,
      monthly:     Math.round(monthly),
      realMonthly: Math.round(realMonthly),
      rows,
    },
  }));
}

document.addEventListener("DOMContentLoaded", () => {
  const cap = g("p1Capital");
  if (cap) cap.addEventListener("blur", () => {
    const v = parseFloat(cap.value);
    if (!isNaN(v)) cap.value = Math.round(v);
  });

  const ownInputs = ["p1Capital", "p1RecordYears", "p1RecordMonths", "p1RevalRate"];
  const sharedInputs = [
    "birthYear", "birthMonth", "retirementAge",
    "grossMonthly", "salaryGrowth", "inflation",
  ];
  [...ownInputs, ...sharedInputs].forEach(id => {
    const el = g(id);
    if (el) ["input", "change"].forEach(evt => el.addEventListener(evt, recalc));
  });

  // Sync revaluation slider display label (shows the effective rate)
  const slider = g("p1RevalRate");
  if (slider) {
    slider.addEventListener("input", syncRevalDisplay);
    syncRevalDisplay();
  }

  // React to scenario buttons: shift NDC revaluation and recompute so
  // the 1st pillar moves with the chosen economic scenario.
  document.addEventListener("scenarioChange", (e) => {
    scenarioName = e.detail?.name || "moderate";
    syncRevalDisplay();
    recalc();
  });

  recalc();
});
