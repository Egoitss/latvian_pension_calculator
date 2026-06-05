// Chart.js wrapper for the accumulation line chart

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
              const fmt = (v) => new Intl.NumberFormat("lv-LV", {
                style: "currency", currency: "EUR",
                maximumFractionDigits: 0,
              }).format(v);
              const ds  = item.chart.data.datasets;
              const idx = item.dataIndex;
              // Datasets 1-3 are cumulative; subtract previous to get pillar value
              if (item.datasetIndex >= 1 && item.datasetIndex <= 3) {
                const prev = ds[item.datasetIndex - 1].data[idx] || 0;
                const val  = item.raw - prev;
                if (val <= 0) return null;
                return `${item.dataset.label}: ${fmt(val)}`;
              }
              return `${item.dataset.label}: ${fmt(item.raw)}`;
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

// Populate chart with combined multi-pillar rows + plan-switch annotations.
// rows come from scenarios.js updateCombinedChart() — each row has:
//   { age, activePlan, cum1, cum2, cum3, cum4, realTotal }
// where cum1=P1, cum2=P1+P2, cum3=+P3, cum4=+Property (cumulative sums).
// fill:'-1' fills the gap between each line and the one below = each pillar's area.
export function drawChart(chart, rows, planSchedule) {
  chart.data.labels     = rows.map((r) => r.age);
  chart.data.activePlans = rows.map((r) => r.activePlan);

  chart.data.datasets = [
    {
      label: "1. līmenis",
      data: rows.map((r) => r.cum1),
      fill: "origin",
      backgroundColor: "rgba(99,102,241,0.35)",
      borderColor: "rgba(79,70,229,0.7)",
      borderWidth: 1.5,
      tension: 0.3,
      pointRadius: 0,
    },
    {
      label: "2. līmenis",
      data: rows.map((r) => r.cum2),
      fill: "-1",
      backgroundColor: "rgba(148,163,184,0.45)",
      borderColor: "rgba(100,116,139,0.7)",
      borderWidth: 1.5,
      tension: 0.3,
      pointRadius: 0,
    },
    {
      label: "3. līmenis",
      data: rows.map((r) => r.cum3),
      fill: "-1",
      backgroundColor: "rgba(167,139,250,0.35)",
      borderColor: "rgba(139,92,246,0.7)",
      borderWidth: 1.5,
      tension: 0.3,
      pointRadius: 0,
    },
    {
      label: "Nekustamais īpašums",
      data: rows.map((r) => r.cum4),
      fill: "-1",
      backgroundColor: "rgba(251,191,36,0.35)",
      borderColor: "rgba(245,158,11,0.7)",
      borderWidth: 1.5,
      tension: 0.3,
      pointRadius: 0,
    },
    {
      label: "Šodienas naudā",
      data: rows.map((r) => r.realTotal),
      fill: false,
      borderColor: "rgba(100,116,139,0.5)",
      borderWidth: 1.5,
      borderDash: [5, 4],
      tension: 0.3,
      pointRadius: 0,
    },
  ];

  // Annotations: retirement marker + plan-switch lines
  const annotations = {};
  if (rows.length > 0) {
    annotations["retirement"] = {
      type: "line",
      xMin: rows[rows.length - 1].age,
      xMax: rows[rows.length - 1].age,
      borderColor: "rgba(100,116,139,0.6)",
      borderWidth: 1.5,
      borderDash: [6, 3],
      label: {
        display: true,
        content: "Pensija",
        position: "end",
        color: "#64748b",
        backgroundColor: "rgba(241,245,249,0.9)",
        font: { size: 10, weight: "600" },
        padding: { x: 6, y: 3 },
      },
    };
  }
  planSchedule.slice(1).forEach((entry, idx) => {
    annotations[`switch${idx}`] = {
      type: "line",
      xMin: entry.startsAtAge, xMax: entry.startsAtAge,
      borderColor: "#64748b", borderWidth: 1, borderDash: [4, 4],
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
