// PDF report: gathers calculator state, POSTs to /export/pdf, and
// triggers the browser download. Mirrors ai_recommend.js: caches the
// latest pillarResult so the report matches what's on screen.

function g(id) { return document.getElementById(id); }

// Latest result from each pillar widget, fed by pillarResult events.
const pillarCache = { p1: null, p2: null, p3: null };

// Latest property forecast, fed by propertyResult events. Property is a
// lump-sum asset (no monthly income) — it only enters the capital total.
const propCache = { retEquity: 0, retEquityReal: 0 };

// Read a number from an input; null if empty/invalid.
function readNum(id) {
  const el = g(id);
  if (!el) return null;
  const raw = String(el.value ?? "").trim();
  if (raw === "") return null;
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : null;
}

// Current age comes from the value ui.js already computed.
function readAge() {
  const n = parseInt(g("computedAge")?.textContent?.trim(), 10);
  return Number.isFinite(n) ? n : null;
}

// Active scenario, read from the highlighted scenario button.
function readScenario() {
  if (g("btnPositive")?.classList.contains("bg-emerald-600")) return "positive";
  if (g("btnNegative")?.classList.contains("bg-red-600")) return "negative";
  return "moderate";
}

// Assemble the payload — pillar monthly/capital plus combined totals,
// summed exactly like scenarios.js builds the on-screen hero card.
function buildPayload() {
  const p1 = pillarCache.p1 || {};
  const p2 = pillarCache.p2 || {};
  const p3 = pillarCache.p3 || {};
  const n = (v) => (Number.isFinite(v) ? v : 0);
  return {
    inputs: {
      age: readAge(),
      retirementAge: readNum("retirementAge"),
      grossMonthly: readNum("grossMonthly"),
      scenario: readScenario(),
    },
    pillars: {
      p1: { monthly: n(p1.monthly), capital: n(p1.finalCapital) },
      p2: { monthly: n(p2.monthlyAfterTax), capital: n(p2.finalBalance) },
      p3: { monthly: n(p3.monthlyPayout), capital: n(p3.netPayout) },
    },
    property: {
      retEquity: n(propCache.retEquity),
      retEquityReal: n(propCache.retEquityReal),
    },
    totals: {
      monthly: n(p1.monthly) + n(p2.monthlyAfterTax) + n(p3.monthlyPayout),
      realMonthly:
        n(p1.realMonthly) + n(p2.realMonthlyAfterTax)
        + n(p3.realMonthlyPayout),
      capital: n(p1.finalCapital) + n(p2.finalBalance) + n(p3.netPayout),
      realCapital:
        n(p1.realCapital) + n(p2.realBalance) + n(p3.realBalance),
    },
  };
}

// Sum the cached pillar results into combined totals (the same
// formula scenarios.js uses for the on-screen hero).
function captureTotals() {
  const p1 = pillarCache.p1 || {};
  const p2 = pillarCache.p2 || {};
  const p3 = pillarCache.p3 || {};
  const n = (v) => (Number.isFinite(v) ? v : 0);
  return {
    monthly: n(p1.monthly) + n(p2.monthlyAfterTax) + n(p3.monthlyPayout),
    realMonthly:
      n(p1.realMonthly) + n(p2.realMonthlyAfterTax)
      + n(p3.realMonthlyPayout),
    capital: n(p1.finalCapital) + n(p2.finalBalance) + n(p3.netPayout),
    propEquity: n(propCache.retEquity),
    propEquityReal: n(propCache.retEquityReal),
  };
}

const SCN_BTN = {
  positive: "btnPositive", moderate: "btnModerate",
  negative: "btnNegative",
};

// Compute totals for all three scenarios by cycling the scenario
// buttons. Runs synchronously so the browser never paints the
// intermediate states (no flicker); restores the active scenario.
function gatherScenarios(active) {
  const out = {};
  for (const name of ["positive", "moderate", "negative"]) {
    const btn = g(SCN_BTN[name]);
    if (btn) { btn.click(); out[name] = captureTotals(); }
  }
  const back = g(SCN_BTN[active]);
  if (back) back.click();
  return out;
}

// Save a blob to disk via a transient <a download> click.
function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadDocx(btn) {
  // Update only the label span so the button icon is preserved.
  const label = g("downloadDocxLabel") || btn;
  const original = label.textContent;
  btn.disabled = true;
  label.textContent = t("Preparing…");
  try {
    const active = readScenario();
    const scenarios = gatherScenarios(active);   // restores active
    const payload = buildPayload();
    payload.activeScenario = active;
    payload.scenarios = scenarios;
    // Respect the /lv prefix so the report is in the page language.
    const base = window.location.pathname.startsWith("/lv") ? "/lv" : "";
    const resp = await fetch(`${base}/export/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    saveBlob(await resp.blob(), "pension-report.pdf");
  } catch (err) {
    label.textContent = t("Download failed — try again");
    setTimeout(() => { label.textContent = original; }, 2500);
    return;
  } finally {
    btn.disabled = false;
  }
  label.textContent = original;
}

document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("pillarResult", (evt) => {
    const { pillar, rows, ...data } = evt.detail;
    pillarCache[`p${pillar}`] = data;
  });
  document.addEventListener("propertyResult", ({ detail }) => {
    propCache.retEquity = detail.retEquity || 0;
    propCache.retEquityReal = detail.retEquityReal || 0;
  });
  const btn = g("downloadDocxBtn");
  if (btn) btn.addEventListener("click", () => downloadDocx(btn));
});
