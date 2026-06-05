// AI recommendation: collects calculator state and POSTs to /api/recommend.
// Listens to pillarResult events to keep the latest pillar values cached.

function g(id) { return document.getElementById(id); }

// Read a number from an input field; null if empty/invalid
function readNum(id) {
  const el = g(id);
  if (!el) return null;
  const raw = String(el.value ?? "").trim();
  if (raw === "") return null;
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : null;
}

// Cache of latest pillar results dispatched via pillarResult events
const pillarCache = { p1: null, p2: null, p3: null };

// Years between today and retirement (rounded down)
function yearsToRetirement() {
  const by = readNum("birthYear") ?? new Date().getFullYear() - 30;
  const bm = readNum("birthMonth") ?? 1;
  const ra = readNum("retirementAge") ?? 65;
  const now = new Date();
  const months = (by + ra) * 12 + bm - (now.getFullYear() * 12 + now.getMonth() + 1);
  return Math.max(0, Math.round(months / 12));
}

// Read current age from the displayed value (already computed by ui.js)
function readAge() {
  const txt = g("computedAge")?.textContent?.trim();
  const n = parseInt(txt, 10);
  return Number.isFinite(n) ? n : null;
}

// Read which scenario button is active by checking solid background classes
function readScenario() {
  const el = g("scenarioReturn");
  if (!el) return "moderate";
  // Gender button + scenario buttons mirror state — check the button with
  // both border + bg variants for the active scenario
  const moderate = g("btnModerate");
  if (moderate && moderate.classList.contains("bg-slate-900")) return "moderate";
  if (g("btnPositive")?.classList.contains("bg-emerald-600")) return "positive";
  if (g("btnNegative")?.classList.contains("bg-red-600")) return "negative";
  return "moderate";
}

// Read gender from the styled male/female toggle
function readGender() {
  return g("genderMale")?.classList.contains("bg-slate-900") ? "vīrietis" : "sieviete";
}

// Build the payload the Flask endpoint expects
function buildPayload(temperature) {
  return {
    temperature,
    age: readAge(),
    retirementAge: readNum("retirementAge"),
    yearsToRetirement: yearsToRetirement(),
    gender: readGender(),
    scenario: readScenario(),
    p1: {
      capital: readNum("p1Capital") ?? 0,
      monthly: pillarCache.p1?.monthly ?? 0,
      finalCapital: pillarCache.p1?.finalCapital ?? 0,
    },
    p2: {
      balance: readNum("balance") ?? 0,
      monthlyAfterTax: pillarCache.p2?.monthlyAfterTax ?? 0,
      finalBalance: pillarCache.p2?.finalBalance ?? 0,
    },
    p3: {
      balance: readNum("p3Balance") ?? 0,
      monthly: readNum("p3Monthly") ?? 0,
      finalBalance: pillarCache.p3?.finalBalance ?? 0,
      monthlyPayout: pillarCache.p3?.monthlyPayout ?? 0,
    },
  };
}

async function generateRecommendation() {
  const btn = g("aiGenerateBtn");
  const loading = g("aiLoading");
  const output = g("aiOutput");
  const error = g("aiError");
  const usage = g("aiUsage");
  const temperature = parseFloat(g("aiTemperature").value);

  // Reset UI: show loading, hide previous output/error
  btn.disabled = true;
  loading.classList.remove("hidden");
  output.classList.add("hidden");
  error.classList.add("hidden");
  usage.classList.add("hidden");

  try {
    const resp = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload(temperature)),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);

    output.textContent = data.text || "(tukša atbilde)";
    output.classList.remove("hidden");
    if (data.usage) {
      usage.textContent =
        `${data.usage.input_tokens} ievades + ${data.usage.output_tokens} izvades token. · `;
      usage.classList.remove("hidden");
    }
  } catch (err) {
    error.textContent = `Kļūda: ${err.message}`;
    error.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    loading.classList.add("hidden");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = g("aiGenerateBtn");
  if (!btn) return;

  // Temperature slider live display
  const tempInput = g("aiTemperature");
  const tempDisplay = g("aiTempDisplay");
  tempInput?.addEventListener("input", () => {
    tempDisplay.textContent = parseFloat(tempInput.value).toFixed(1);
  });

  btn.addEventListener("click", generateRecommendation);

  // Listen for pillar results so we have fresh data when AI is invoked
  document.addEventListener("pillarResult", (evt) => {
    const { pillar, ...data } = evt.detail;
    pillarCache[`p${pillar}`] = data;
  });
});
