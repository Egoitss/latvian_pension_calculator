// Pure calculation functions — mirrors calculator.py, no DOM access
import {
  CONSTANTS, getPlanByName, historicalP2lRate, HISTORICAL_INFLATION,
  SURVIVAL_FROM_67, SURVIVAL_TO_67,
  DINAMIKA_MONTHLY_RETURNS,
} from "./data.js";

const {
  VSAOI_CEILING, P2L_RATE, DEFAULT_RETURN,
  PENSION_TAX_FREE_THRESHOLD, PENSION_TAX_RATE,
} = CONSTANTS;

// Safe numeric coercion with a fallback for non-finite values
export function toNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

// Format a number as a percentage string with two decimal places
export function formatPct(value) {
  return `${toNumber(value, 0).toFixed(2)}%`;
}

// Format a number as a locale EUR currency string (no decimals)
export function formatEur(value) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(value);
}

// Resolve the annual return % for a plan object
export function getAnnualReturn(plan, manualReturn) {
  if (!plan) return DEFAULT_RETURN;
  if (plan.manual) return toNumber(manualReturn, DEFAULT_RETURN);
  if (plan.benchmark) return toNumber(plan.assumption_return, DEFAULT_RETURN);
  // Prefer 5-year return, fall back to 3-year
  if (plan.return_5y != null) return toNumber(plan.return_5y, DEFAULT_RETURN);
  if (plan.return_3y != null) return toNumber(plan.return_3y, DEFAULT_RETURN);
  return DEFAULT_RETURN;
}

// Return true if current or projected annual gross will exceed the VSAOI cap
export function shouldApplyVsaoiCeiling(
  { age, retirementAge, grossMonthly, salaryGrowth }
) {
  const safeAge = Math.max(0, Math.round(toNumber(age, 35)));
  const safeRet = Math.max(safeAge, Math.round(toNumber(retirementAge, 65)));
  let annualGross = Math.max(0, toNumber(grossMonthly, 0)) * 12;
  const growth = toNumber(salaryGrowth, 0) / 100;
  const years = Math.max(0, safeRet - safeAge);

  for (let i = 0; i <= years; i++) {
    if (annualGross > VSAOI_CEILING) return true;
    annualGross *= 1 + growth;
  }
  return false;
}

// Build a sorted array of {startsAtAge, planName} switch schedule entries
export function buildPlanSchedule({
  age, retirementAge, selectedPlanName, manualReturn,
  enableSwitching, switchOneAge, switchOnePlanName,
  switchTwoAge, switchTwoPlanName,
}) {
  const safeAge = Math.max(0, Math.round(toNumber(age, 35)));
  const safeRet = Math.max(safeAge, Math.round(toNumber(retirementAge, 65)));

  const schedule = [{ startsAtAge: safeAge, planName: selectedPlanName }];

  if (enableSwitching) {
    // Clamp each switch age between current+1 and retirement
    const first = Math.max(
      safeAge + 1, Math.min(safeRet, Math.round(toNumber(switchOneAge, 50)))
    );
    const second = Math.max(
      first + 1, Math.min(safeRet, Math.round(toNumber(switchTwoAge, 60)))
    );
    if (first < safeRet) schedule.push({ startsAtAge: first, planName: switchOnePlanName });
    if (second < safeRet) schedule.push({ startsAtAge: second, planName: switchTwoPlanName });
  }

  return schedule.sort((a, b) => a.startsAtAge - b.startsAtAge);
}

// Return the most-recently-started schedule entry for the given age
export function getActiveScheduleEntry(schedule, age) {
  let active = schedule[0];
  for (const entry of schedule) {
    if (age >= entry.startsAtAge) active = entry;
  }
  return active;
}

// Year-by-year accumulation from current age to retirement
export function calculateProjection({
  age, retirementAge, balance, grossMonthly,
  salaryGrowth, inflation, payoutYears,
  applyCeiling, planSchedule, manualReturn,
  p2lRate = P2L_RATE,
}) {
  const safeAge = Math.max(0, Math.round(toNumber(age, 35)));
  const safeRet = Math.max(safeAge, Math.round(toNumber(retirementAge, 65)));
  let currentBalance = Math.max(0, toNumber(balance, 0));
  let annualGross = Math.max(0, toNumber(grossMonthly, 0)) * 12;
  const growth = toNumber(salaryGrowth, 0) / 100;
  const infl = toNumber(inflation, 0) / 100;
  const safePayoutYrs = Math.max(1, toNumber(payoutYears, 18));
  const years = Math.max(0, safeRet - safeAge);

  // Seed year-0 row with the opening balance
  let cumulativeContributions = currentBalance;
  const rows = [{
    age: safeAge, year: 0,
    annualGross: Math.round(annualGross),
    annualContribution: 0, annualReturn: 0,
    activePlan: getPlanByName(planSchedule[0].planName).name,
    contributions: Math.round(cumulativeContributions),
    earnings: 0,
    total: Math.round(currentBalance),
    realTotal: Math.round(currentBalance),
  }];

  for (let i = 1; i <= years; i++) {
    const currentAge = safeAge + i;
    const entry = getActiveScheduleEntry(planSchedule, currentAge);
    const plan = getPlanByName(entry.planName);
    const rate = getAnnualReturn(plan, manualReturn) / 100;

    // Cap contribution base at VSAOI ceiling if applicable
    const contribBase = applyCeiling
      ? Math.min(annualGross, VSAOI_CEILING) : annualGross;
    const annualContribution = Math.max(0, contribBase * p2lRate);
    cumulativeContributions += annualContribution;

    // Compound for the year
    currentBalance = (currentBalance + annualContribution) * (1 + rate);
    const realDiscount = Math.pow(1 + infl, i);
    const realTotal = realDiscount > 0 ? currentBalance / realDiscount : currentBalance;

    rows.push({
      age: currentAge, year: i,
      annualGross: Math.round(annualGross),
      annualContribution: Math.round(annualContribution),
      annualReturn: rate * 100,
      activePlan: plan.name,
      contributions: Math.round(cumulativeContributions),
      earnings: Math.round(currentBalance - cumulativeContributions),
      total: Math.round(currentBalance),
      realTotal: Math.round(realTotal),
    });
    annualGross *= 1 + growth;
  }

  // Compute monthly payout and apply pension income tax
  const final = rows[rows.length - 1];
  const payoutMonths = safePayoutYrs * 12;
  const monthlyPayout = final.total / payoutMonths;
  const realMonthlyPayout = final.realTotal / payoutMonths;

  const taxable = Math.max(0, monthlyPayout - PENSION_TAX_FREE_THRESHOLD);
  const monthlyTax = taxable * PENSION_TAX_RATE;
  const monthlyPayoutAfterTax = monthlyPayout - monthlyTax;

  const realTaxable = Math.max(0, realMonthlyPayout - PENSION_TAX_FREE_THRESHOLD);
  const realMonthlyTax = realTaxable * PENSION_TAX_RATE;
  const realMonthlyAfterTax = realMonthlyPayout - realMonthlyTax;

  return {
    rows, final, years,
    monthlyPayout, realMonthlyPayout,
    monthlyTax, monthlyPayoutAfterTax,
    realMonthlyTax, realMonthlyAfterTax,
  };
}

// Back-calculate the implied average annual return from historical contributions
export function calculateImpliedReturn({
  startYear, startSalary, currentSalary, currentBalance, actualContributions,
}) {
  const currentYear = new Date().getFullYear();
  const startYr = Math.round(toNumber(startYear, 0));
  const salary0 = Math.max(0, toNumber(startSalary, 0));
  const salaryNow = Math.max(0, toNumber(currentSalary, 0));
  const balance = Math.max(0, toNumber(currentBalance, 0));

  // Reject inputs that are missing or outside the valid P2L era
  if (startYr < 2001 || startYr >= currentYear || salary0 <= 0 || balance <= 0) {
    return null;
  }
  const N = currentYear - startYr;

  // Derive salary growth from the two known endpoints — avoids slider mismatch
  const growth = salaryNow > 0
    ? Math.pow(salaryNow / salary0, 1 / N) - 1
    : 0;

  // Reconstruct undiscounted contribution total for optional scaling
  let reconTotal = 0;
  let ag = salary0 * 12;
  for (let i = 0; i < N; i++) {
    reconTotal += Math.min(ag, VSAOI_CEILING) * historicalP2lRate(startYr + i);
    ag *= 1 + growth;
  }
  const actual = Math.max(0, toNumber(actualContributions, 0));
  // Scale factor: if user supplies actual total, adjust each year proportionally
  const scale = actual > 0 && reconTotal > 0 ? actual / reconTotal : 1.0;

  // Forward value of all P2L contributions compounded to today at `r`
  function fv(r) {
    let total = 0;
    let annualGross = salary0 * 12;
    for (let i = 0; i < N; i++) {
      const p2lRate = historicalP2lRate(startYr + i);
      const contribBase = Math.min(annualGross, VSAOI_CEILING);
      // Mid-year contribution scaled to match actual total if provided
      total += contribBase * p2lRate * scale * Math.pow(1 + r, N - i - 0.5);
      annualGross *= 1 + growth;
    }
    return total;
  }

  // Bisect in [-10 %, +100 %] to find r where fv(r) = balance
  let lo = -0.10, hi = 1.00;
  for (let iter = 0; iter < 80; iter++) {
    const mid = (lo + hi) / 2;
    if (fv(mid) < balance) lo = mid; else hi = mid;
    if (hi - lo < 1e-7) break;
  }
  const rNom = (lo + hi) / 2;

  // Compute geometric-mean annual inflation over the accumulation period
  let cumulativeInfl = 1.0;
  for (let i = 0; i < N; i++) {
    cumulativeInfl *= 1 + (HISTORICAL_INFLATION[startYr + i] ?? 0.025);
  }
  const avgInfl = Math.pow(cumulativeInfl, 1 / N) - 1;
  const rReal = (1 + rNom) / (1 + avgInfl) - 1;

  return {
    nominal: rNom * 100,
    real: rReal * 100,
    reconContributions: Math.round(reconTotal * scale),
    avgInflation: avgInfl * 100,
    salaryGrowth: growth * 100,
  };
}

// Estimate total lifetime management fees paid to the plan provider
export function estimateLifetimeCommission(rows, feeTotalPct) {
  if (feeTotalPct == null) return null;
  let total = 0;
  for (let i = 1; i < rows.length; i++) {
    // Approximate average balance during the year
    const avgBalance = (rows[i - 1].total + rows[i].total) / 2;
    total += avgBalance * (feeTotalPct / 100);
  }
  return total;
}

// Interpolate survival probability for payoutYears from the SURVIVAL_FROM_67 table
export function survivalProbability(gender, payoutYears) {
  const table = SURVIVAL_FROM_67[gender] ?? SURVIVAL_FROM_67.men;
  for (let i = 1; i < table.length; i++) {
    const [y0, s0] = table[i - 1];
    const [y1, s1] = table[i];
    if (payoutYears <= y1) {
      const t = (payoutYears - y0) / (y1 - y0);
      return s0 + t * (s1 - s0);
    }
  }
  return table[table.length - 1][1];
}

// Probability that a person of currentAge reaches age 67 (SURVIVAL_TO_67 table)
export function survivalToRetirement(gender, currentAge) {
  if (currentAge >= 67) return 1.0;
  const table = SURVIVAL_TO_67[gender] ?? SURVIVAL_TO_67.men;
  for (let i = 1; i < table.length; i++) {
    const [a0, s0] = table[i - 1];
    const [a1, s1] = table[i];
    if (currentAge <= a1) {
      const t = (currentAge - a0) / (a1 - a0);
      return s0 + t * (s1 - s0);
    }
  }
  return table[table.length - 1][1];
}

// Overall probability from current age: reach pension AND survive N more years into it
export function survivalOverall(gender, currentAge, yearsIntoPension) {
  return survivalToRetirement(gender, currentAge) *
         survivalProbability(gender, yearsIntoPension);
}

// Monte Carlo bootstrap: 10 000 simulations of numMonths monthly returns
// drawn with replacement from DINAMIKA_MONTHLY_RETURNS.
// Returns { positive, moderate, negative } as annualized % rates.
// Float64Array used for fast native sort.
export function bootstrapScenarioReturns(numMonths, nSims = 10_000) {
  const pool = DINAMIKA_MONTHLY_RETURNS;
  const poolLen = pool.length;
  const multipliers = new Float64Array(nSims);

  for (let s = 0; s < nSims; s++) {
    let mult = 1.0;
    for (let m = 0; m < numMonths; m++) {
      mult *= 1.0 + pool[Math.floor(Math.random() * poolLen)];
    }
    multipliers[s] = mult;
  }

  multipliers.sort();
  const exp = 12.0 / Math.max(1, numMonths);

  function pctRate(p) {
    const idx = Math.max(0, Math.min(nSims - 1, Math.floor(p * nSims)));
    return Math.round((Math.pow(multipliers[idx], exp) - 1) * 10000) / 100;
  }

  return {
    positive: pctRate(0.90),
    moderate: pctRate(0.50),
    negative: pctRate(0.10),
  };
}
