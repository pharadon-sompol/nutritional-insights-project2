const apiUrl = window.APP_CONFIG?.API_URL || "/api/insights";
const palette = ["#2563eb", "#16a34a", "#7c3aed", "#ea580c", "#0891b2", "#64748b"];
const charts = {};
let latestPayload = null;

const elements = {
  notice: document.querySelector("#notice"),
  filter: document.querySelector("#diet-filter"),
  refresh: document.querySelector("#refresh-button"),
  reset: document.querySelector("#reset-button"),
  search: document.querySelector("#recipe-search")
};

function setNotice(message, type = "") {
  elements.notice.textContent = message;
  elements.notice.className = `notice ${type}`.trim();
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-CA", { maximumFractionDigits: 2 }).format(value);
}

function makeChart(id, configuration) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), configuration);
}

function renderMetrics(payload) {
  document.querySelector("#recipe-count").textContent = formatNumber(payload.summary.recipeCount);
  document.querySelector("#diet-count").textContent = payload.summary.dietTypeCount;
  document.querySelector("#average-protein").textContent = formatNumber(payload.summary.averageProtein);
  document.querySelector("#execution-time").textContent = formatNumber(payload.metadata.functionExecutionMs);
  document.querySelector("#view-title").textContent = payload.selectedDiet === "all" ? "All diet types" : payload.selectedDiet;
  document.querySelector("#data-source").textContent = `Source: ${payload.metadata.source}`;
  document.querySelector("#processed-at").textContent = `Updated: ${new Date(payload.metadata.processedAtUtc).toLocaleString()}`;
}

function renderFilter(payload) {
  const selected = payload.selectedDiet;
  elements.filter.innerHTML = '<option value="all">All diet types</option>';
  payload.availableDiets.forEach((diet) => {
    const option = document.createElement("option");
    option.value = diet;
    option.textContent = diet;
    option.selected = diet === selected;
    elements.filter.append(option);
  });
}

function renderCharts(payload) {
  const averages = payload.averageMacronutrients;
  makeChart("macro-chart", {
    type: "bar",
    data: {
      labels: averages.map((item) => item.diet),
      datasets: [
        { label: "Protein", data: averages.map((item) => item.protein), backgroundColor: palette[0], borderRadius: 6 },
        { label: "Carbs", data: averages.map((item) => item.carbs), backgroundColor: palette[1], borderRadius: 6 },
        { label: "Fat", data: averages.map((item) => item.fat), backgroundColor: palette[2], borderRadius: 6 }
      ]
    },
    options: chartOptions("Average grams")
  });

  const distribution = payload.recipeDistribution;
  makeChart("distribution-chart", {
    type: "doughnut",
    data: {
      labels: distribution.map((item) => item.diet),
      datasets: [{ data: distribution.map((item) => item.recipes), backgroundColor: palette, borderColor: "#ffffff", borderWidth: 3 }]
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } } } }
  });

  const grouped = Object.groupBy ? Object.groupBy(payload.scatterPoints, (point) => point.diet) : payload.scatterPoints.reduce((result, point) => ((result[point.diet] ||= []).push(point), result), {});
  makeChart("scatter-chart", {
    type: "scatter",
    data: {
      datasets: Object.entries(grouped).map(([diet, points], index) => ({
        label: diet,
        data: points.map((point) => ({ x: point.carbs, y: point.protein, recipe: point.recipe })),
        backgroundColor: palette[index % palette.length]
      }))
    },
    options: {
      ...chartOptions("Protein (g)"),
      scales: { x: { title: { display: true, text: "Carbohydrates (g)" }, grid: { color: "#e5e7eb" } }, y: { title: { display: true, text: "Protein (g)" }, grid: { color: "#e5e7eb" } } },
      plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } }, tooltip: { callbacks: { label: (context) => `${context.raw.recipe}: ${context.raw.y}g protein, ${context.raw.x}g carbs` } } }
    }
  });

  renderHeatmap(payload.correlationMatrix);
}

function chartOptions(yTitle) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "nearest", intersect: false },
    plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } } },
    scales: { x: { grid: { display: false } }, y: { beginAtZero: true, title: { display: true, text: yTitle }, grid: { color: "#e5e7eb" } } }
  };
}

function renderHeatmap(matrix) {
  const root = document.querySelector("#heatmap");
  root.innerHTML = '<div></div>' + matrix.labels.map((label) => `<div class="heat-label">${label}</div>`).join("");
  matrix.values.forEach((row, rowIndex) => {
    root.insertAdjacentHTML("beforeend", `<div class="heat-label">${matrix.labels[rowIndex]}</div>`);
    row.forEach((value) => {
      const intensity = Math.max(0.08, Math.abs(value));
      const color = value >= 0 ? `rgba(37,99,235,${intensity})` : `rgba(220,38,38,${intensity})`;
      root.insertAdjacentHTML("beforeend", `<div class="heat-cell" style="background:${color}">${Number(value).toFixed(2)}</div>`);
    });
  });
}

function renderRecipes(recipes, query = "") {
  const normalized = query.trim().toLowerCase();
  const matches = recipes.filter((item) => `${item.recipe} ${item.cuisine} ${item.diet}`.toLowerCase().includes(normalized));
  document.querySelector("#recipe-table").innerHTML = matches.length
    ? matches.map((item) => `<tr><td>${escapeHtml(item.recipe)}</td><td><span class="diet-pill">${escapeHtml(item.diet)}</span></td><td>${escapeHtml(item.cuisine)}</td><td>${formatNumber(item.protein)} g</td></tr>`).join("")
    : '<tr><td colspan="4">No matching recipes found.</td></tr>';
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value;
  return node.innerHTML;
}

async function loadDashboard(diet = elements.filter.value || "all") {
  elements.refresh.disabled = true;
  setNotice("Loading and processing data in the Azure Function…");
  try {
    const url = new URL(apiUrl, window.location.href);
    if (diet !== "all") url.searchParams.set("diet", diet);
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The cloud API returned an error.");
    latestPayload = payload;
    renderMetrics(payload);
    renderFilter(payload);
    renderCharts(payload);
    renderRecipes(payload.topRecipes, elements.search.value);
    setNotice(`Cloud data loaded successfully in ${payload.metadata.functionExecutionMs} ms.`, "success");
  } catch (error) {
    setNotice(`${error.message} Check the Function URL in config.js and confirm CORS is enabled.`, "error");
  } finally {
    elements.refresh.disabled = false;
  }
}

elements.filter.addEventListener("change", () => loadDashboard(elements.filter.value));
elements.refresh.addEventListener("click", () => loadDashboard(elements.filter.value));
elements.reset.addEventListener("click", () => { elements.search.value = ""; loadDashboard("all"); });
elements.search.addEventListener("input", () => latestPayload && renderRecipes(latestPayload.topRecipes, elements.search.value));

window.addEventListener("DOMContentLoaded", () => loadDashboard());
