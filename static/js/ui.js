// UI orchestration: reads inputs → runs calc → updates DOM and chart
import { PLANS, getPlanByName, CONSTANTS } from "./data.js";
import {
  toNumber, formatPct, formatEur,
  getAnnualReturn, shouldApplyVsaoiCeiling,
  buildPlanSchedule, calculateProjection, estimateLifetimeCommission,
  survivalProbability,
  survivalToRetirement, survivalOverall,
} from "./calc.js";
import { initChart, drawChart } from "./chart.js";

// Grab an element by id (throws at startup if the id is missing)
function el(id) { return document.getElementById(id); }

// Gender state — toggled by ♂/♀ buttons, used for survival probability
let gender = "men";
// Last computed plan schedule — used by the combinedChartData listener
let lastPlanSchedule = [];

// Compute completed years of age from birth year and month (1-indexed)
function ageFromBirth(birthYear, birthMonth) {
  const now = new Date();
  let age = now.getFullYear() - birthYear;
  if (now.getMonth() + 1 < birthMonth) age -= 1;
  return Math.max(0, age);
}

// Project retirement age: 65 baseline (2025) + ~1 yr per decade trend beyond that
function projectedRetirementAge(birthYear) {
  const BASE_AGE = 65, BASE_YEAR = 2025, RATE = 0.1;
  if (birthYear + BASE_AGE <= BASE_YEAR) return BASE_AGE;
  return Math.round((BASE_AGE + RATE * (birthYear - BASE_YEAR)) / (1 - RATE));
}

// Read all form input values into a plain object
function readInputs() {
  const birthYear  = toNumber(el("birthYear").value,  new Date().getFullYear() - 30);
  const birthMonth = toNumber(el("birthMonth").value, 1);
  return {
    age:               ageFromBirth(birthYear, birthMonth),
    retirementAge:     toNumber(el("retirementAge").value, 65),
    balance:           toNumber(el("balance").value, 0),
    grossMonthly:      toNumber(el("grossMonthly").value, 0),
    selectedPlanName:  el("selectedPlan").value,
    manualReturn:      toNumber(el("manualReturn").value, 8),
    salaryGrowth:      toNumber(el("salaryGrowth").value, 0),
    inflation:         toNumber(el("inflation").value, 0),
    payoutYears:       toNumber(el("payoutYears").value, 18),
    enableSwitching:   el("enableSwitching").checked,
    switchOneAge:      toNumber(el("switchOneAge").value, 50),
    switchOnePlanName: el("switchOnePlan").value,
    switchTwoAge:      toNumber(el("switchTwoAge").value, 60),
    switchTwoPlanName: el("switchTwoPlan").value,
    p2lRate:         toNumber(el("p2lRate").value, 6) / 100,
    p2AlreadyEarned: toNumber(el("p2AlreadyEarned")?.value, 0),
  };
}

// Toggle the VSAOI ceiling status box styling and label
function updateVsaoi(applyCeiling) {
  const box = el("vsaoiBox");
  // classList operations are order-independent and idempotent
  box.classList.toggle("border-slate-500", applyCeiling);
  box.classList.toggle("bg-slate-500", applyCeiling);
  box.classList.toggle("text-white", applyCeiling);
  box.classList.toggle("border-slate-200", !applyCeiling);
  box.classList.toggle("bg-white", !applyCeiling);
  box.classList.toggle("text-slate-700", !applyCeiling);
  // Description text: readable on both light and mid-grey backgrounds
  const desc = el("vsaoiDesc");
  desc.classList.toggle("text-white/70", applyCeiling);
  desc.classList.toggle("text-slate-500", !applyCeiling);
  el("vsaoiStatus").textContent = applyCeiling
    ? "Ieslēgti automātiski" : "Izslēgti automātiski";
}

// Update the current annual contribution display beneath the VSAOI box
function updateAnnualContribution(grossMonthly, applyCeiling, p2lRate) {
  const annual = Math.max(0, grossMonthly) * 12;
  const base = applyCeiling
    ? Math.min(annual, CONSTANTS.VSAOI_CEILING) : annual;
  el("annualContribution").textContent = formatEur(base * p2lRate);
}

// Show/hide the manual return slider based on plan type
function updateManualReturnVisibility(plan) {
  const field = el("manualReturnField");
  field.classList.toggle("hidden", !plan?.manual);
}

// Show/hide the switch rows based on the checkbox state
function updateSwitchRowsVisibility(enabled) {
  el("switchRows").classList.toggle("hidden", !enabled);
}

// Master update: read inputs → recalculate → refresh all DOM outputs
function onInputChange(chart) {
  const inputs = readInputs();
  const plan = getPlanByName(inputs.selectedPlanName);

  updateManualReturnVisibility(plan);
  updateSwitchRowsVisibility(inputs.enableSwitching);
  el("computedAge").textContent = inputs.age;

  // Retirement year display
  const bYear  = toNumber(el("birthYear").value,  new Date().getFullYear() - 30);
  const bMonth = toNumber(el("birthMonth").value, 1);
  const MONTHS_LV = ["janvārī","februārī","martā","aprīlī","maijā","jūnijā",
                     "jūlijā","augustā","septembrī","oktobrī","novembrī","decembrī"];
  el("retirementYearDisplay").textContent =
    `${MONTHS_LV[bMonth - 1]}, ${bYear + inputs.retirementAge}. g.`;

  // Slider display labels
  el("manualReturnDisplay").textContent = formatPct(inputs.manualReturn);
  el("salaryGrowthDisplay").textContent = formatPct(inputs.salaryGrowth);
  el("inflationDisplay").textContent = formatPct(inputs.inflation);
  el("p2lRateDisplay").textContent = formatPct(inputs.p2lRate * 100);

  const applyCeiling = shouldApplyVsaoiCeiling({
    age: inputs.age, retirementAge: inputs.retirementAge,
    grossMonthly: inputs.grossMonthly, salaryGrowth: inputs.salaryGrowth,
  });
  lastPlanSchedule = buildPlanSchedule({
    age: inputs.age, retirementAge: inputs.retirementAge,
    selectedPlanName: inputs.selectedPlanName,
    manualReturn: inputs.manualReturn,
    enableSwitching: inputs.enableSwitching,
    switchOneAge: inputs.switchOneAge, switchOnePlanName: inputs.switchOnePlanName,
    switchTwoAge: inputs.switchTwoAge, switchTwoPlanName: inputs.switchTwoPlanName,
  });

  // Apply scenario return if scenarios.js has set a value
  const scenarioEl = el("scenarioReturn");
  const scenarioRate = scenarioEl
    ? parseFloat(scenarioEl.dataset.value) : NaN;
  const effectiveSchedule = Number.isFinite(scenarioRate)
    ? lastPlanSchedule.map(e => ({ ...e, planName: "Manuāls pieņēmums" }))
    : lastPlanSchedule;
  const effectiveManualReturn = Number.isFinite(scenarioRate)
    ? scenarioRate : inputs.manualReturn;

  const projection = calculateProjection({
    ...inputs,
    applyCeiling,
    planSchedule: effectiveSchedule,
    manualReturn: effectiveManualReturn,
  });

  updateVsaoi(applyCeiling);
  // Annual contribution uses the current legal rate (6%), not the slider avg
  updateAnnualContribution(inputs.grossMonthly, applyCeiling, CONSTANTS.P2L_RATE);

  document.dispatchEvent(new CustomEvent("pillarResult", {
    detail: {
      pillar: 2,
      finalBalance:        projection.final.total,
      realBalance:         projection.final.realTotal,
      earnings:            projection.final.earnings + inputs.p2AlreadyEarned,
      monthlyAfterTax:     Math.round(projection.monthlyPayoutAfterTax),
      realMonthlyAfterTax: Math.round(projection.realMonthlyAfterTax),
      rows:                projection.rows,
    },
  }));
  el("p2FinalBalance").textContent = formatEur(projection.final.total);
  el("p2Monthly").textContent      = formatEur(Math.round(projection.monthlyPayoutAfterTax));
  el("p2RealMonthly").textContent  = formatEur(Math.round(projection.realMonthlyAfterTax));
  el("survivalToPension").textContent =
    `~${Math.round(survivalToRetirement(gender, inputs.age) * 100)}%`;
  el("survivalAt5").textContent  =
    `~${Math.round(survivalOverall(gender, inputs.age, 5)  * 100)}%`;
  el("survivalAt10").textContent =
    `~${Math.round(survivalOverall(gender, inputs.age, 10) * 100)}%`;
  el("survivalPct").textContent  =
    `~${Math.round(survivalOverall(gender, inputs.age, inputs.payoutYears) * 100)}%`;

  const chartPeriodEl = document.getElementById("chartPeriod");
  if (chartPeriodEl) chartPeriodEl.textContent = `${projection.years} gadiem`;
}


// Clipboard helper with textarea fallback for non-secure contexts
async function copyToClipboard(text) {
  let copied = false;
  try {
    if (window.isSecureContext && navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (_) { /* fall through to textarea fallback */ }

  if (!copied) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      Object.assign(ta.style, { position: "fixed", top: "0", left: "0", opacity: "0" });
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      copied = document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (_) { /* ignore */ }
  }

  // Show Latvian feedback message
  const feedback = el("copyFeedback");
  feedback.classList.remove("hidden", "bg-emerald-50", "text-emerald-700",
                             "bg-amber-50", "text-amber-700");
  if (copied) {
    feedback.classList.add("bg-emerald-50", "text-emerald-700");
    feedback.textContent = "Saite nokopēta";
  } else {
    feedback.classList.add("bg-amber-50", "text-amber-700");
    feedback.textContent =
      "Kopēšana nav atļauta šajā skatā — iezīmē saiti un nokopē manuāli";
  }
  setTimeout(() => feedback.classList.add("hidden"), copied ? 1800 : 3500);
}

// Wire up all inputs and initialise the chart on page load
document.addEventListener("DOMContentLoaded", () => {
  const chart = initChart("projectionChart");

  // Gender toggle buttons — update state and re-run calculation
  const GENDER_ACTIVE =
    "flex-1 rounded-2xl border px-3 py-2 text-sm font-medium transition" +
    " text-center border-slate-900 bg-slate-900 text-white";
  const GENDER_INACTIVE =
    "flex-1 rounded-2xl border px-3 py-2 text-sm font-medium transition" +
    " text-center border-slate-200 bg-white text-slate-600" +
    " hover:border-slate-400";
  function setGender(g) {
    gender = g;
    el("genderMale").className   = g === "men"   ? GENDER_ACTIVE : GENDER_INACTIVE;
    el("genderFemale").className = g === "women" ? GENDER_ACTIVE : GENDER_INACTIVE;
    onInputChange(chart);
  }
  el("genderMale").addEventListener("click",   () => setGender("men"));
  el("genderFemale").addEventListener("click", () => setGender("women"));

  // Auto-populate retirement age from projected trend when birth year changes
  function syncRetirementAge() {
    const by = toNumber(el("birthYear").value, new Date().getFullYear() - 30);
    const projected = projectedRetirementAge(by);
    el("retirementAge").value = projected;
    const noteEl = document.getElementById("projectedRetAge");
    if (noteEl) noteEl.textContent = projected;
  }
  ["input", "change"].forEach(evt =>
    el("birthYear").addEventListener(evt, syncRetirementAge)
  );

  // Input ids that trigger full recalculation on change
  const inputIds = [
    "birthYear", "birthMonth", "retirementAge", "balance", "p2AlreadyEarned",
    "grossMonthly", "selectedPlan", "manualReturn", "salaryGrowth",
    "inflation", "p2lRate", "payoutYears", "enableSwitching",
    "switchOneAge", "switchOnePlan",
    "switchTwoAge", "switchTwoPlan",
    "scenarioReturn",
  ];
  inputIds.forEach((id) => {
    el(id).addEventListener("input", () => onInputChange(chart));
    el(id).addEventListener("change", () => onInputChange(chart));
  });

  // Copy buttons identified by data-copy attribute pointing to an input id
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.copy);
      if (target) copyToClipboard(target.value);
    });
  });

  // Chart redraws when scenarios.js has merged all pillar rows
  document.addEventListener("combinedChartData", ({ detail }) => {
    drawChart(chart, detail.rows, lastPlanSchedule);
  });

  // Sync retirement age from birth year before first calculation
  syncRetirementAge();
  // Run initial update to populate all outputs from default values
  onInputChange(chart);
});
