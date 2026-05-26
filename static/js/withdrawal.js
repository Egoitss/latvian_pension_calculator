// 2nd-pillar withdrawal assessment: Keep / Withdraw+Invest / Mūža pensija
// Driven by pillarResult events; no server round-trips.
import { ANNUITY_DIVISOR, CONSTANTS } from "./data.js";

const { PENSION_TAX_FREE_THRESHOLD, PENSION_TAX_RATE } = CONSTANTS;

function g(id) { return document.getElementById(id); }

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

function calcAge(birthYear, birthMonth) {
  const now = new Date();
  let age = now.getFullYear() - birthYear;
  if (now.getMonth() + 1 < birthMonth) age -= 1;
  return Math.max(0, age);
}

function applyPensionTax(monthly) {
  const taxable = Math.max(0, monthly - PENSION_TAX_FREE_THRESHOLD);
  return monthly - taxable * PENSION_TAX_RATE;
}

// Fix 1: removed unused p1 field
const state = { p2: null };
let activeGender = "male";

function readInputs() {
  // Fix 5: added radix 10 to all parseInt calls
  const birthYear   = parseInt(g("birthYear")?.value, 10)      || new Date().getFullYear() - 40;
  const birthMonth  = parseInt(g("birthMonth")?.value, 10)     || 1;
  const retAge      = parseInt(g("retirementAge")?.value, 10)  || 67;
  const payoutYears = parseInt(g("payoutYears")?.value, 10)    || 18;
  const p2Current   = parseFloat(g("balance")?.value)          || 0;
  const propPrice   = parseFloat(g("propPrice")?.value)        || 0;
  const mortBal     = parseFloat(g("mortBalance")?.value)      || 0;
  const mortMarg    = parseFloat(g("mortBankMargin")?.value)   || 0;
  const mortEur     = parseFloat(g("mortEuribor")?.value)      || 0;
  const taxRatePct  = parseFloat(g("wdlTaxRate")?.value)       || 25.5;
  const altRetPct   = parseFloat(g("wdlAltReturn")?.value)     || 8.0;
  const earlyMode   = g("wdlEarlyToggle")?.checked ?? false;

  const age        = calcAge(birthYear, birthMonth);
  const years      = Math.max(0, retAge - age);
  const homeEquity = Math.max(0, propPrice - mortBal);
  const mortRate   = mortMarg + mortEur;

  return {
    retAge, payoutYears, p2Current, homeEquity, mortRate,
    taxRate: taxRatePct / 100,
    altReturn: altRetPct / 100,
    earlyMode, age, years,
  };
}

function computeScenarios(inp, p2) {
  const { retAge, payoutYears, taxRate, altReturn, earlyMode, years, p2Current } = inp;

  const scA = {
    capital:    p2?.finalBalance ?? 0,
    monthlyNet: p2?.monthlyAfterTax ?? 0,
  };

  const withdrawBase = earlyMode ? p2Current : (p2?.finalBalance ?? 0);
  const netWithdraw  = withdrawBase * (1 - taxRate);
  // Fix 3: -1: withdrawal assumed at start of final accumulation year
  const investYears  = earlyMode ? Math.max(0, years - 1) : 0;
  const investedFV   = netWithdraw * Math.pow(1 + altReturn, investYears);
  const bMonthly     = investedFV / Math.max(1, payoutYears * 12);
  const scB = { withdrawBase, netWithdraw, investedFV, monthly: bMonthly, investYears };

  const divisorTbl = ANNUITY_DIVISOR[activeGender] || ANNUITY_DIVISOR.male;
  const clampedAge = Math.max(62, Math.min(69, retAge));
  // Fix 2: clampedAge is always in [62..69] so key always exists; no fallback needed
  const divisor    = divisorTbl[clampedAge];
  const cMonthly   = (p2?.finalBalance ?? 0) / divisor;
  const scC = {
    monthly:      cMonthly,
    monthlyNet:   applyPensionTax(cMonthly),
    divisor,
    breakEvenAge: retAge + Math.round(divisor / 12),
  };

  return { scA, scB, scC };
}

// Fix 4: named constants for recommendation thresholds
const ANNUITY_BETTER_THRESHOLD = 1.05; // 5% better monthly before annuity preferred
const EQUITY_CUSHION = 100_000;        // below this equity level, longevity risk matters more

function computeRecommendation(s, inp) {
  const { earlyMode, homeEquity, mortRate, altReturn, payoutYears } = inp;
  const { scA, scB, scC } = s;
  const oppCost = scA.monthlyNet - scB.monthly;

  if (earlyMode) {
    if (mortRate > altReturn * 100) {
      return {
        winner: "withdraw",
        title:  "Hipotēkas daļēja dzēšana",
        body:   `Hipotēkas likme ${mortRate.toFixed(2)} % pārsniedz jūsu investīciju` +
                ` pieņēmumu ${(altReturn * 100).toFixed(1)} %. Daļa neto summas` +
                ` ${fmtEur(scB.netWithdraw)} varētu samazināt aizdevuma slogu,` +
                " taču apsveriet, ka fondā iemaksu pieaugums var pārsniegt" +
                " hipotēkas procentu ietaupījumu.",
      };
    }
    return {
      winner: "keep",
      title:  "Saglabāt fondā",
      body:   `Izņemot tagad (neto ${fmtEur(scB.netWithdraw)}), jūs zaudētu aptuveni` +
              ` ${fmtEur(oppCost)} mēnesī pensijā — kapitāls fondā aug bez` +
              ` ienākuma nodokļa, bet izņemtajai summai jāmaksā nodoklis tagad` +
              ` un vēl jāpārspēj fonda ienesīgums.`,
    };
  }

  // Fix 4: use named constants instead of magic numbers
  const annuityIsBetter  = scC.monthlyNet > scA.monthlyNet * ANNUITY_BETTER_THRESHOLD;
  const hasEquityCushion = homeEquity >= EQUITY_CUSHION;

  if (annuityIsBetter && !hasEquityCushion) {
    return {
      winner: "annuity",
      title:  "Mūža pensija (polise)",
      body:   `Apdrošināšanas polise nodrošina aptuveni` +
              ` ${fmtEur(scC.monthlyNet - scA.monthlyNet)} vairāk mēnesī` +
              ` un garantē izmaksu uz mūžu. Izdevīgi, ja dzīvosiet vairāk nekā` +
              ` ${Math.round(scC.divisor / 12)} g. pēc pensijas` +
              ` (līdz ${scC.breakEvenAge} g.).`,
    };
  }
  return {
    winner: "keep",
    title:  "Programmētā izmaksa",
    body:   `Jūsu nekustamā īpašuma pašu kapitāls (${fmtEur(homeEquity)}) un` +
            " valsts pensija (1. līmenis) veido drošības rezervi. Programmētā" +
            ` izmaksa ${payoutYears} gadu garumā saglabā mantojamību un` +
            " elastību. Mūža pensija jāapsver, ja prioritāte ir" +
            " ilgdzīvotāja riska novēršana.",
  };
}

function updateDisplay(s, rec) {
  const { scA, scB, scC } = s;

  g("wdlACapital")   && (g("wdlACapital").textContent   = fmtEur(scA.capital));
  g("wdlAMonthly")   && (g("wdlAMonthly").textContent   = fmtEur(scA.monthlyNet));
  g("wdlBNet")       && (g("wdlBNet").textContent       = fmtEur(scB.netWithdraw));
  g("wdlBFV")        && (g("wdlBFV").textContent        = fmtEur(scB.investedFV));
  g("wdlBMonthly")   && (g("wdlBMonthly").textContent   = fmtEur(scB.monthly));
  g("wdlCMonthly")   && (g("wdlCMonthly").textContent   = fmtEur(scC.monthlyNet));
  g("wdlCBreakEven") && (g("wdlCBreakEven").textContent = `${scC.breakEvenAge} g.`);
  g("wdlRecTitle")   && (g("wdlRecTitle").textContent   = rec.title);
  g("wdlRecBody")    && (g("wdlRecBody").textContent    = rec.body);

  const cardMap = { keep: "wdlCardA", withdraw: "wdlCardB", annuity: "wdlCardC" };
  ["wdlCardA", "wdlCardB", "wdlCardC"].forEach(id => {
    const el = g(id);
    if (!el) return;
    el.classList.remove("ring-2", "ring-emerald-500");
    el.classList.add("border-slate-200");
  });
  const winEl = g(cardMap[rec.winner]);
  if (winEl) {
    winEl.classList.add("ring-2", "ring-emerald-500");
    winEl.classList.remove("border-slate-200");
  }
}

function recalc() {
  if (!state.p2) return;
  const inp = readInputs();
  const s   = computeScenarios(inp, state.p2);
  const rec = computeRecommendation(s, inp);
  updateDisplay(s, rec);
  g("wdlCard")?.classList.remove("hidden");
}

// Fix 6: helper to sync a percent slider to its label
function wirePercentLabel(inputId, labelId) {
  const inp = g(inputId);
  const lbl = g(labelId);
  if (!inp || !lbl) return;
  const sync = () => { lbl.textContent = `${parseFloat(inp.value).toFixed(1)} %`; };
  inp.addEventListener("input", sync);
  sync();
}

document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("pillarResult", ({ detail }) => {
    // Fix 1: removed unused p1 branch
    if (detail.pillar === 2) state.p2 = detail;
    recalc();
  });

  g("genderMale")?.addEventListener("click",   () => { activeGender = "male";   recalc(); });
  g("genderFemale")?.addEventListener("click", () => { activeGender = "female"; recalc(); });

  // Fix 7: merged two forEach loops into one
  [
    "wdlTaxRate", "wdlAltReturn",
    "balance", "retirementAge", "birthYear", "birthMonth",
    "payoutYears", "inflation", "propPrice",
    "mortBalance", "mortBankMargin", "mortEuribor",
  ].forEach(id => {
    const el = g(id);
    if (!el) return;
    ["input", "change"].forEach(evt => el.addEventListener(evt, recalc));
  });

  g("wdlEarlyToggle")?.addEventListener("change", recalc);

  // Fix 6: deduplicated slider sync using helper
  wirePercentLabel("wdlTaxRate",   "wdlTaxDisplay");
  wirePercentLabel("wdlAltReturn", "wdlAltReturnDisplay");
});
