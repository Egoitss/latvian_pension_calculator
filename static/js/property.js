// Property value estimator — reads main calculator + loan widget inputs
// CAGR source: Arco Real Estate / Latio market reviews 2010–2024

const APPRECIATION = { city: 0.062, valmiera: 0.055, rural: 0.025 };
const CRASH_RATE   = 0.60; // Latvia 2007–2010 worst case

let locType    = "city";
let renoTiming = "now";

function g(id) { return document.getElementById(id); }

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

function projectProp(price, rate, t) {
  return price * Math.pow(1 + rate, t);
}

// Simulate annuity amortization to find remaining balance after N months
function mortBalanceAt(futureMonths) {
  const bal  = parseFloat((g("mortBalance")        || {}).value) || 0;
  const pay  = parseFloat((g("mortMonthlyPayment") || {}).value) || 0;
  const marg = parseFloat((g("mortBankMargin")     || {}).value) || 0;
  const eur  = parseFloat((g("mortEuribor")        || {}).value) || 0;
  if (!bal || !pay) return 0;
  const r = (marg + eur) / 100 / 12;
  let b = bal;
  for (let m = 0; m < futureMonths; m++) {
    const interest  = r > 0 ? b * r : 0;
    const principal = pay - interest;
    if (principal <= 0) break;
    b -= principal;
    if (b <= 0) return 0;
  }
  return Math.max(0, b);
}

// Renovation multiplier derived from user reference case vs plain appreciation
function calcRenoMultiplier() {
  const buy   = parseFloat((g("propRefBuy")   || {}).value) || 0;
  const reno  = parseFloat((g("propRefReno")  || {}).value) || 0;
  const sell  = parseFloat((g("propRefSell")  || {}).value) || 0;
  const years = parseFloat((g("propRefYears") || {}).value) || 0;
  if (!buy || !reno || !sell || years <= 0) return null;
  // What the base property would have appreciated to without renovation
  const appreciated = buy * Math.pow(1 + APPRECIATION[locType], years);
  const valueAdded  = sell - appreciated;
  if (valueAdded <= 0 || reno <= 0) return null;
  return valueAdded / reno;
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
    g("propRenoResults").classList.add("hidden");
    return;
  }

  const rate     = APPRECIATION[locType];
  const inflRate = (parseFloat((g("inflation") || {}).value) || 4.16) / 100;
  const p2lBal   = parseFloat((g("balance")   || {}).value) || 0;
  const yRet     = yrsToRetirement();

  // Retirement year label for column header
  const bY   = parseInt((g("birthYear")     || {}).value) || 1982;
  const retA = parseInt((g("retirementAge") || {}).value) || 65;
  g("propRetYearHeader").textContent = `${bY + retA}. g.`;

  const mult = calcRenoMultiplier();
  g("propRefMultiplier").textContent = mult !== null ? mult.toFixed(2) : "—";

  const horizon = Math.max(1, parseInt((g("propHorizon") || {}).value) || 10);

  // Base projections: custom horizon column + retirement column
  const horizons = [horizon, yRet];
  const pfxs     = ["prop10", "propRet"];

  for (let i = 0; i < 2; i++) {
    const t   = horizons[i];
    const pfx = pfxs[i];

    const nominal = projectProp(price, rate, t);
    const real    = nominal / Math.pow(1 + inflRate, t);
    const mortBal = mortBalanceAt(Math.round(t * 12));
    const equity  = nominal - mortBal;

    const crashVal    = nominal * (1 - CRASH_RATE);
    const crashEquity = crashVal - mortBal;

    g(`${pfx}Nominal`).textContent      = fmtEur(nominal);
    g(`${pfx}Real`).textContent         = fmtEur(real);
    g(`${pfx}MortBal`).textContent      = mortBal > 100 ? fmtEur(mortBal) : "—";
    g(`${pfx}Equity`).textContent       = fmtEur(equity);
    g(`${pfx}CrashVal`).textContent     = fmtEur(crashVal);
    g(`${pfx}CrashEquity`).textContent  = fmtEur(crashEquity);
  }

  // Hide mortgage row when no mortgage is entered
  const hasMort = (parseFloat((g("mortBalance") || {}).value) || 0) > 0;
  g("propMortRow").classList.toggle("hidden", !hasMort);

  g("propResults").classList.remove("hidden");

  // Renovation section — needs valid multiplier and non-zero P2L balance
  if (mult === null || p2lBal <= 0) {
    g("propRenoResults").classList.add("hidden");
    return;
  }

  const renoBoost = p2lBal * mult;
  g("propP2LBalance").textContent = fmtEur(p2lBal);
  g("propRenoMult").textContent   = mult.toFixed(2);
  g("propRenoBoost").textContent  = fmtEur(renoBoost);

  for (let i = 0; i < 2; i++) {
    const t   = horizons[i];
    const pfx = pfxs[i];

    const baseNominal = projectProp(price, rate, t);
    let withReno;

    if (renoTiming === "now") {
      withReno = projectProp(price + renoBoost, rate, t);
    } else {
      // Renovate at retirement: boost applied at yRet, then appreciates further
      if (yRet > t) {
        // Renovation not yet applied at this horizon
        withReno = baseNominal;
      } else {
        const valAtRet = projectProp(price, rate, yRet) + renoBoost;
        withReno = valAtRet * Math.pow(1 + rate, t - yRet);
      }
    }

    const gain = withReno - baseNominal;
    g(`${pfx}WithReno`).textContent = fmtEur(withReno);
    g(`${pfx}RenoGain`).textContent = (gain > 0 ? "+" : "") + fmtEur(gain);
  }

  g("propRenoResults").classList.remove("hidden");
}

const PILL_ON  = "rounded-xl border border-slate-900 bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white transition";
const PILL_OFF = "rounded-xl border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 transition hover:border-slate-400";

function setLocType(type) {
  locType = type;
  g("propTypeCity").className     = type === "city"     ? PILL_ON : PILL_OFF;
  g("propTypeValmiera").className = type === "valmiera" ? PILL_ON : PILL_OFF;
  g("propTypeRural").className    = type === "rural"    ? PILL_ON : PILL_OFF;
  const notes = {
    city:     "~6.2% gadā nominālais (Rīga, 2010–2024 · Arco Real Estate / Latio)",
    valmiera: "~5.5% gadā nominālais (Valmiera, 2010–2024 · Arco / Latio; rūpn. bāze + maz jaunu projektu)",
    rural:    "~2.5% gadā nominālais (lauki/mazpilsētas, 2010–2024)",
  };
  g("propRateNote").textContent = notes[type];
  recalc();
}

function setRenoTiming(timing) {
  renoTiming = timing;
  g("propRenoNow").className        = timing === "now"        ? PILL_ON : PILL_OFF;
  g("propRenoRetirement").className = timing === "retirement" ? PILL_ON : PILL_OFF;
  recalc();
}

document.addEventListener("DOMContentLoaded", () => {
  g("propTypeCity").addEventListener("click",        () => setLocType("city"));
  g("propTypeValmiera").addEventListener("click",    () => setLocType("valmiera"));
  g("propTypeRural").addEventListener("click",       () => setLocType("rural"));
  g("propRenoNow").addEventListener("click",         () => setRenoTiming("now"));
  g("propRenoRetirement").addEventListener("click",  () => setRenoTiming("retirement"));

  const ownInputs = [
    "propPrice", "propHorizon", "propRefBuy", "propRefReno", "propRefSell", "propRefYears",
  ];
  const sharedInputs = [
    "inflation", "balance", "birthYear", "birthMonth", "retirementAge",
    "mortBalance", "mortBankMargin", "mortEuribor", "mortMonthlyPayment",
  ];
  [...ownInputs, ...sharedInputs].forEach(id => {
    const el = g(id);
    if (el) ["input", "change"].forEach(evt => el.addEventListener(evt, recalc));
  });

  // Initialise location type and price from server-side defaults
  const card = document.querySelector("[data-prop-type]");
  if (card) setLocType(card.dataset.propType);
  else recalc();
});
