// 3rd-pillar voluntary pension estimator
// Own inputs: p3PlanName, p3Balance, p3Monthly, p3ContribGrowth
// Shared inputs: grossMonthly, inflation, retirementAge, birthYear, birthMonth
import { P3_CONSTANTS, getP3PlanByName, P3_COST_BASIS } from "./data.js";

function g(id) { return document.getElementById(id); }

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

function fmtEurDecimal(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 2,
  }).format(v);
}

function ageFromBirth(birthYear, birthMonth) {
  const now = new Date();
  let age = now.getFullYear() - birthYear;
  if (now.getMonth() + 1 < birthMonth) age -= 1;
  return Math.max(0, age);
}

// Mirrors calculator.py:calculate_p3_annual_refund
function calcAnnualRefund(grossMonthly, monthlyContrib) {
  const annualGross = Math.max(0, grossMonthly) * 12;
  const annualContrib = Math.max(0, monthlyContrib) * 12;
  const eligibleCap = Math.min(
    annualGross * P3_CONSTANTS.TAX_DEDUCTION_RATE,
    P3_CONSTANTS.TAX_DEDUCTION_CAP,
  );
  const eligible = Math.min(annualContrib, eligibleCap);
  return Math.round(eligible * P3_CONSTANTS.IIN_RATE * 100) / 100;
}

// Mirrors calculator.py:calculate_p3_projection
function calcProjection({
  age, retirementAge, currentBalance,
  monthlyContrib, contribGrowth, planReturn, inflation,
}) {
  const safeAge = Math.max(0, Math.round(age));
  const safeRet = Math.max(safeAge, Math.round(retirementAge));
  const years = Math.max(0, safeRet - safeAge);

  let balance = Math.max(0, currentBalance);
  let monthly = Math.max(0, monthlyContrib);
  const growth = contribGrowth / 100;
  const r = planReturn / 100;
  const infl = inflation / 100;
  let totalOwnContrib = 0;
  const rows = [];

  for (let i = 0; i < years; i++) {
    const annualContrib = monthly * 12;
    // Grow balance at net return rate, then credit annual contribution
    balance = balance * (1 + r) + annualContrib;
    totalOwnContrib += annualContrib;
    monthly *= (1 + growth);
    rows.push({ age: safeAge + i + 1, balance: Math.round(balance) });
  }

  const totalInvested = currentBalance + totalOwnContrib;
  const gains = Math.max(0, balance - totalInvested);
  const taxOnGains = gains * P3_CONSTANTS.PAYOUT_GAINS_TAX;
  const deflator = years > 0 ? Math.pow(1 + infl, years) : 1;
  const realBalance = deflator > 0 ? balance / deflator : balance;

  return {
    finalBalance: Math.round(balance),
    realBalance: Math.round(realBalance),
    totalOwnContrib: Math.round(totalOwnContrib),
    gains: Math.round(gains),
    taxOnGains: Math.round(taxOnGains),
    netPayout: Math.round(balance - taxOnGains),
    years,
    rows,
  };
}

function recalc() {
  const balance = parseFloat(g("p3Balance")?.value) || 0;
  const monthly = parseFloat(g("p3Monthly")?.value) || 0;
  const gross   = parseFloat(g("grossMonthly")?.value) || 0;

  // Always update refund display when contribution and gross are available
  if (monthly > 0 && gross > 0) {
    const refund = calcAnnualRefund(gross, monthly);
    g("p3AnnualRefund").textContent = fmtEurDecimal(refund);
  } else {
    g("p3AnnualRefund").textContent = "—";
  }

  if (balance <= 0 && monthly <= 0) {
    g("p3Results").classList.add("hidden");
    return;
  }

  const planName = g("p3PlanName")?.value || "";
  const plan = getP3PlanByName(planName);
  const scenarioEl = g("scenarioReturn");
  const scenarioRate = scenarioEl ? parseFloat(scenarioEl.dataset.value) : NaN;
  const planReturn = Number.isFinite(scenarioRate) ? scenarioRate : plan.return_5y;

  const birthYear     = parseInt(g("birthYear")?.value)      || new Date().getFullYear() - 30;
  const birthMonth    = parseInt(g("birthMonth")?.value)     || 1;
  const retAge        = parseInt(g("retirementAge")?.value)  || 65;
  const contribGrowth = parseFloat(g("p3ContribGrowth")?.value) || 0;
  const inflation     = parseFloat(g("inflation")?.value)    || 0;
  const age = ageFromBirth(birthYear, birthMonth);

  const result = calcProjection({
    age, retirementAge: retAge, currentBalance: balance,
    monthlyContrib: monthly, contribGrowth, planReturn, inflation,
  });

  // Use the true cost basis (all historical cash in) rather than the
  // current market balance so gains tax reflects the full investment gain.
  const costBasis = P3_COST_BASIS + result.totalOwnContrib;
  const accurateGains = Math.max(0, result.finalBalance - costBasis);
  const accurateTax   = accurateGains * P3_CONSTANTS.PAYOUT_GAINS_TAX;
  const netPayout     = result.finalBalance - accurateTax;

  // Monthly payout over the same period as P2
  const payoutYears = parseFloat(g("payoutYears")?.value) || 18;
  const payoutFactor = result.finalBalance > 0
    ? result.realBalance / result.finalBalance : 1;
  const monthlyPayout     = Math.round(netPayout / (payoutYears * 12));
  const realMonthlyPayout = Math.round(
    netPayout * payoutFactor / (payoutYears * 12)
  );

  g("p3FinalBalance").textContent       = fmtEur(result.finalBalance);
  g("p3NetPayout").textContent          = fmtEur(netPayout);
  g("p3RealBalance").textContent        = fmtEur(result.realBalance);
  g("p3GainsTax").textContent           = fmtEur(accurateTax);
  g("p3TotalContrib").textContent       = fmtEur(result.totalOwnContrib);
  g("p3MonthlyDisplay").textContent     = fmtEur(monthlyPayout);
  g("p3RealMonthlyDisplay").textContent = fmtEur(realMonthlyPayout);
  g("p3Results").classList.remove("hidden");

  document.dispatchEvent(new CustomEvent("pillarResult", {
    detail: {
      pillar: 3,
      finalBalance:     result.finalBalance,
      realBalance:      result.realBalance,
      gains:            accurateGains,
      netPayout,
      monthlyPayout,
      realMonthlyPayout,
      rows: result.rows,
    },
  }));
}

document.addEventListener("DOMContentLoaded", () => {
  const ownInputs = ["p3PlanName", "p3Balance", "p3Monthly", "p3ContribGrowth"];
  const sharedInputs = [
    "birthYear", "birthMonth", "retirementAge",
    "grossMonthly", "inflation", "payoutYears", "scenarioReturn",
  ];
  [...ownInputs, ...sharedInputs].forEach(id => {
    const el = g(id);
    if (el) ["input", "change"].forEach(evt => el.addEventListener(evt, recalc));
  });

  // Sync growth slider display label
  const slider = g("p3ContribGrowth");
  const display = g("p3GrowthDisplay");
  if (slider && display) {
    const sync = () => { display.textContent = `${parseFloat(slider.value).toFixed(1)}%`; };
    slider.addEventListener("input", sync);
    sync();
  }

  recalc();
});
