// Chart.js wrapper for the accumulation line chart

// Historical market peak-to-trough drawdown factors for crash scenarios
const DOT_COM_FACTOR = 0.51;    // MSCI World dotcom trough 2002-03: -49 %
const CRISIS_2008_FACTOR = 0.46; // MSCI World 2008 crisis trough: -54 %

// Register the annotation plugin (loaded via CDN before this module runs)
Chart.register(window["chartjs-plugin-annotation"]);

// Create and return a new Chart.js LineChart instance on the given canvas
export function initChart(canvasId) {
  const ctx = document.getElementById(canvasId).getContext("2d");

  return new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        // Annotation plugin config — populated on each drawChart call
        annotation: { annotations: {} },
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            // Show plan name alongside the age label in tooltips
            title(items) {
              const raw = items[0]?.raw;
              const plan = items[0]?.chart?.data?.activePlans?.[items[0].dataIndex];
              return plan
                ? `Vecums: ${items[0].label} • ${plan}`
                : `Vecums: ${items[0].label}`;
            },
            label(item) {
              return `${item.dataset.label}: ${
                new Intl.NumberFormat("lv-LV", {
                  style: "currency", currency: "EUR", maximumFractionDigits: 0,
                }).format(item.raw)
              }`;
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
        y: {
          grid: { color: "#e2e8f0" },
          ticks: {
            // Abbreviate axis labels: 1 200 000 → 1.2M €, 50 000 → 50k €
            callback(value) {
              if (value >= 1_000_000)
                return `${(value / 1_000_000).toFixed(1)}M €`;
              if (value >= 1_000)
                return `${Math.round(value / 1_000)}k €`;
              return `${Math.round(value)} €`;
            },
          },
        },
      },
    },
  });
}

// Populate chart datasets from projection rows and add plan-switch annotations
export function drawChart(chart, rows, planSchedule) {
  // X axis: age labels
  chart.data.labels = rows.map((r) => r.age);

  // Store active plan names for tooltip title callback
  chart.data.activePlans = rows.map((r) => r.activePlan);

  // Three datasets: contributions (blue), earnings (green), total (purple)
  chart.data.datasets = [
    {
      label: "Iemaksas",
      data: rows.map((r) => r.contributions),
      borderColor: "#2563eb",
      backgroundColor: "transparent",
      borderWidth: 3,
      pointRadius: 0,
    },
    {
      label: "Peļņa",
      data: rows.map((r) => r.earnings),
      borderColor: "#16a34a",
      backgroundColor: "transparent",
      borderWidth: 3,
      pointRadius: 0,
    },
    {
      label: "Kopā",
      data: rows.map((r) => r.total),
      borderColor: "#7c3aed",
      backgroundColor: "transparent",
      borderWidth: 4,
      pointRadius: 0,
    },
    {
      label: "Kopā (dotcom -49%)",
      data: rows.map((r) => r.total * DOT_COM_FACTOR),
      borderColor: "#d97706",
      backgroundColor: "transparent",
      borderWidth: 2,
      borderDash: [5, 5],
      pointRadius: 0,
    },
    {
      label: "Kopā (2008 krīze -54%)",
      data: rows.map((r) => r.total * CRISIS_2008_FACTOR),
      borderColor: "#dc2626",
      backgroundColor: "transparent",
      borderWidth: 2,
      borderDash: [5, 5],
      pointRadius: 0,
    },
  ];

  // Vertical annotation lines for each plan switch age
  const annotations = {};
  planSchedule.slice(1).forEach((entry, idx) => {
    annotations[`switch${idx}`] = {
      type: "line",
      xMin: entry.startsAtAge,
      xMax: entry.startsAtAge,
      borderColor: "#64748b",
      borderWidth: 1,
      borderDash: [4, 4],
      label: {
        display: true,
        content: `Maiņa: ${entry.startsAtAge}`,
        position: "start",
        color: "#64748b",
        font: { size: 11 },
      },
    };
  });
  chart.options.plugins.annotation.annotations = annotations;

  chart.update();
}
