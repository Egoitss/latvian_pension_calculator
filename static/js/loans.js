// Loan widget logic — mortgage and consumer credit
// Primary inputs: balance + end year + bank margin + EURIBOR
// Monthly payment is derived. P2L allocation cascades: smallest balance first.

function g(id) { return document.getElementById(id); }

// Shared state: dynamic — `mort` and `cred` are server-rendered; extra
// loans are added at runtime via addLoan() and removed via removeLoan().
const loanState = {};

function emptyLoanRecord() {
  return { active: false, type: "term", balance: 0, totalRate: 0, months: 0, payment: 0 };
}

function annuityPayment(balance, annualRate, months) {
  if (months <= 0) return null;
  const r = annualRate / 100 / 12;
  if (r === 0) return balance / months;
  return balance * r / (1 - Math.pow(1 + r, -months));
}

function crossoverYear(balance, annualRate, payment) {
  const r = annualRate / 100 / 12;
  if (r === 0) return null;
  let b = balance;
  const startYear = new Date().getFullYear();
  for (let month = 0; month < 600; month++) {
    const interest  = b * r;
    const principal = payment - interest;
    if (principal <= 0) return null;
    if (principal >= interest) return startYear + Math.floor(month / 12);
    b -= principal;
    if (b <= 0) break;
  }
  return null;
}

function fmtMonths(months) {
  const total = Math.round(months);
  const y = Math.floor(total / 12);
  const m = total % 12;
  return m > 0 ? `${y} g. ${m} mēn.` : `${y} g.`;
}

function fmtEur(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 0,
  }).format(v);
}

function fmtEurDec(v) {
  return new Intl.NumberFormat("lv-LV", {
    style: "currency", currency: "EUR", maximumFractionDigits: 2,
  }).format(v);
}

function scenarioShorterTerm(balance, annualRate, payment, p2lAmt, origMonths) {
  const newBalance = balance - p2lAmt;
  if (newBalance <= 0) {
    return `Izmantojot P2L (${fmtEur(p2lAmt)}): kredīts tiktu dzēsts pilnībā.`;
  }
  const r = annualRate / 100 / 12;
  let newMonths;
  if (r === 0) {
    newMonths = newBalance / payment;
  } else {
    const inner = 1 - (newBalance * r / payment);
    if (inner <= 0) return "Nevar aprēķināt — maksājums pārāk mazs.";
    newMonths = -Math.log(inner) / Math.log(1 + r);
  }
  const savedMonths   = origMonths - newMonths;
  const origInterest  = payment * origMonths - balance;
  const newInterest   = payment * newMonths  - newBalance;
  const savedInterest = origInterest - newInterest;
  return `Izmantojot P2L (${fmtEur(p2lAmt)}):\n` +
    `Atmaksāt par ${fmtMonths(savedMonths)} ātrāk → kopā ${fmtMonths(newMonths)}\n` +
    `Ietaupīt procentos: ${fmtEur(savedInterest)}`;
}

function scenarioLowerPayment(balance, annualRate, origMonths, p2lAmt) {
  const newBalance = balance - p2lAmt;
  if (newBalance <= 0) {
    return `Izmantojot P2L (${fmtEur(p2lAmt)}): kredīts tiktu dzēsts pilnībā.`;
  }
  const newPayment  = annuityPayment(newBalance, annualRate, origMonths);
  if (!newPayment) return "Nevar aprēķināt.";
  const origPayment = annuityPayment(balance, annualRate, origMonths);
  const saved       = origPayment - newPayment;
  return `Izmantojot P2L (${fmtEur(p2lAmt)}):\n` +
    `Ikmēneša maksājums: ${fmtEurDec(newPayment)} (ietaupot ${fmtEurDec(saved)}/mēn.)\n` +
    `Termiņš paliek: ${fmtMonths(origMonths)}`;
}

// Cascade allocation across N loans: smallest active balance erased first
function allocateP2L() {
  const balEl = g("p2lBalance") || g("balance");
  let remaining = parseFloat((balEl || {}).value) || 0;
  const result = {};
  const active = Object.entries(loanState)
    .filter(([, s]) => s.active && s.balance > 0)
    .sort(([, a], [, b]) => a.balance - b.balance);
  Object.keys(loanState).forEach(k => { result[k] = 0; });
  for (const [prefix, s] of active) {
    if (remaining <= 0) break;
    const amt = Math.min(remaining, s.balance);
    result[prefix] = amt;
    remaining -= amt;
  }
  return result;
}

function renderP2L(prefix, p2lAmt) {
  const s = loanState[prefix];
  const container = g(`${prefix}ScenContainer`);
  if (!s.active || !s.balance || s.months <= 0) {
    container.classList.add("hidden");
    return;
  }
  container.classList.remove("hidden");

  const text = s.type === "term"
    ? scenarioShorterTerm(s.balance, s.totalRate, s.payment, p2lAmt, s.months)
    : scenarioLowerPayment(s.balance, s.totalRate, s.months, p2lAmt);

  const resultEl = g(`${prefix}ScenarioResult`);
  const textEl   = g(`${prefix}ScenarioText`);
  textEl.style.whiteSpace = "pre-line";
  textEl.textContent = text;
  resultEl.classList.remove("hidden");
}

function recalcP2L() {
  const alloc = allocateP2L();
  Object.keys(loanState).forEach(prefix => renderP2L(prefix, alloc[prefix] || 0));
}

const PILL_ACTIVE   = "rounded-xl border border-slate-900 bg-slate-900 px-3 py-1 text-[11px] font-medium text-white transition";
const PILL_INACTIVE = "rounded-xl border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-600 transition hover:border-slate-400";

function initCard(prefix) {
  loanState[prefix] = emptyLoanRecord();

  const balanceEl    = g(`${prefix}Balance`);
  const endMonthEl   = g(`${prefix}EndMonth`);
  const endYearEl    = g(`${prefix}EndYear`);
  const bankMarginEl = g(`${prefix}BankMargin`);
  const euriborEl    = g(`${prefix}Euribor`);
  const totalRateEl  = g(`${prefix}TotalRateDisplay`);
  const summaryEl    = g(`${prefix}Summary`);
  const paymentInputEl = g(`${prefix}MonthlyPayment`);
  const toggleEl     = g(`${prefix}P2LToggle`);
  const btnTerm      = g(`${prefix}ScenTypeTerm`);
  const btnPayment   = g(`${prefix}ScenTypePayment`);

  function setScenType(type) {
    loanState[prefix].type = type;
    btnTerm.className    = type === "term"    ? PILL_ACTIVE : PILL_INACTIVE;
    btnPayment.className = type === "payment" ? PILL_ACTIVE : PILL_INACTIVE;
    recalcP2L();
  }

  function recalc() {
    const balance    = parseFloat(balanceEl.value);
    const endYear    = parseInt(endYearEl.value);
    const bankMargin = parseFloat(bankMarginEl.value) || 0;
    const euribor    = parseFloat(euriborEl.value)    || 0;
    const totalRate  = bankMargin + euribor;

    totalRateEl.textContent = (bankMarginEl.value || euriborEl.value)
      ? `${totalRate.toFixed(2)}%` : "—";

    const now         = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    const endMonth    = parseInt(endMonthEl.value) || null;
    const months = endYear && endMonth
      ? (endYear * 12 + endMonth) - (currentYear * 12 + currentMonth)
      : endYear ? (endYear - currentYear) * 12 : null;

    if (!balance || balance <= 0 || !months || months <= 0) {
      summaryEl.classList.add("hidden");
      Object.assign(loanState[prefix], { balance: 0, totalRate, months: 0, payment: 0 });
      recalcP2L();
      return;
    }

    const computed = annuityPayment(balance, totalRate, months);
    if (!computed || computed <= 0) {
      summaryEl.classList.add("hidden");
      Object.assign(loanState[prefix], { balance: 0, totalRate, months: 0, payment: 0 });
      recalcP2L();
      return;
    }

    // Use actual payment from input if set, otherwise fill with computed value
    const existingPayment = parseFloat(paymentInputEl.value);
    const payment = existingPayment > 0 ? existingPayment : computed;
    if (!existingPayment) paymentInputEl.value = computed.toFixed(2);

    // Store computed values for cascade logic
    Object.assign(loanState[prefix], { balance, totalRate, months, payment });

    // Compact summary line 1: payment · term · interest · %
    const totalInt = Math.max(0, payment * months - balance);
    const intPct   = ((totalInt / balance) * 100).toFixed(0);
    g(`${prefix}RemainingTerm`).textContent  = fmtMonths(months);
    g(`${prefix}TotalInterest`).textContent  = fmtEur(totalInt);
    g(`${prefix}InterestPct`).textContent    = `${intPct}%`;

    // Summary line 2: this-month split · crossover
    const r             = totalRate / 100 / 12;
    const monthInterest = r > 0 ? balance * r : 0;
    const monthPrincipal = payment - monthInterest;
    g(`${prefix}MonthBreakdown`).textContent =
      `${fmtEurDec(monthInterest)} % + ${fmtEurDec(monthPrincipal)} pam.`;
    const cy = r > 0 ? crossoverYear(balance, totalRate, payment) : null;
    g(`${prefix}CrossoverYear`).textContent = cy ? `${cy}. g.` : "nekad";

    summaryEl.classList.remove("hidden");
    recalcP2L();
  }

  // Toggle: show/hide P2L section and re-run allocation
  toggleEl.addEventListener("change", () => {
    loanState[prefix].active = toggleEl.checked;
    recalcP2L();
  });

  btnTerm.addEventListener("click",    () => setScenType("term"));
  btnPayment.addEventListener("click", () => setScenType("payment"));

  ["input", "change"].forEach(evt => {
    balanceEl.addEventListener(evt, recalc);
    endMonthEl.addEventListener(evt, recalc);
    endYearEl.addEventListener(evt, recalc);
    bankMarginEl.addEventListener(evt, recalc);
    euriborEl.addEventListener(evt, recalc);
    paymentInputEl.addEventListener(evt, recalc);
  });
}

// Monotonic counter for dynamic loan prefixes (extra1, extra2, …)
let extraLoanCounter = 0;

// Wire up an accordion on a freshly inserted card (mirrors accordion.js logic)
function bindAccordion(card) {
  const triggerId = card.dataset.accordionTrigger;
  const trigger = triggerId ? document.getElementById(triggerId) : null;
  const header = card.querySelector(".accordion-header");
  if (header) {
    header.addEventListener("click", (e) => {
      // Don't toggle accordion when clicking the remove button
      if (e.target.closest("[data-remove-loan]")) return;
      card.classList.toggle("is-expanded");
    });
  }
  if (trigger) {
    const onInput = () => {
      const v = parseFloat(trigger.value);
      if (v > 0) card.classList.add("is-expanded");
    };
    trigger.addEventListener("input", onInput);
    trigger.addEventListener("change", onInput);
  }
}

// Add a new loan card cloned from #loanCardTemplate
function addLoan(title) {
  extraLoanCounter += 1;
  const prefix = `extra${extraLoanCounter}`;
  const tpl = g("loanCardTemplate");
  if (!tpl) return;

  // Substitute the controlled prefix in innerHTML; title is user-supplied
  // and inserted via textContent after parsing to avoid XSS.
  const html = tpl.innerHTML.replaceAll("__PREFIX__", prefix);
  const wrap = document.createElement("div");
  wrap.innerHTML = html;
  const card = wrap.firstElementChild;
  const titleEl = card.querySelector(".accordion-header h3");
  if (titleEl) titleEl.textContent = title;

  g("extraLoansContainer").appendChild(card);
  bindAccordion(card);
  initCard(prefix);

  // Wire remove button (only present on dynamic cards)
  const removeBtn = card.querySelector("[data-remove-loan]");
  if (removeBtn) {
    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      removeLoan(prefix, card);
    });
  }
}

function removeLoan(prefix, card) {
  delete loanState[prefix];
  card.remove();
  recalcP2L();
}

document.addEventListener("DOMContentLoaded", () => {
  initCard("mort");
  initCard("cred");
  // Trigger initial calculation for pre-filled values
  ["mort", "cred"].forEach(prefix => {
    const el = g(`${prefix}Balance`);
    if (el && el.value) el.dispatchEvent(new Event("input"));
  });

  // "+ Pievienot kredītu" button
  const addBtn = g("addLoanBtn");
  if (addBtn) {
    addBtn.addEventListener("click", () => {
      const title = prompt("Kredīta nosaukums:", "Cits kredīts");
      if (title === null) return;
      addLoan(title.trim() || "Cits kredīts");
    });
  }
});
