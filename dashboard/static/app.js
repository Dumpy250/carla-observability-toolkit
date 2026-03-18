let chart = null;
let currentRunDataA = null;
let currentRunDataB = null;
let currentRunDirA = "";
let currentRunDirB = "";
let compareMode = false;
let availableRuns = [];

const metricConfig = {
  speed: { label: "Speed (m/s)", color: "#4db2ff" },
  acceleration: { label: "Acceleration |a| (m/s^2)", color: "#ff9f40" },
  steering: { label: "Steering", color: "#8ad66d" },
  throttle: { label: "Throttle", color: "#c792ea" },
  brake: { label: "Brake", color: "#ff6384" },
};

const comparisonFields = [
  { key: "max_speed_mps", label: "Max Speed (m/s)", digits: 3 },
  { key: "avg_speed_mps", label: "Average Speed (m/s)", digits: 3 },
  { key: "total_collisions", label: "Total Collisions", digits: 0 },
  { key: "run_duration_s", label: "Run Duration (s)", digits: 3 },
  { key: "avg_acceleration_mps2", label: "Average Acceleration (m/s^2)", digits: 3 },
  { key: "metric_row_count", label: "Metric Rows", digits: 0 },
  { key: "event_count", label: "Event Count", digits: 0 },
];

function setStatus(message, isError = false) {
  const statusEl = document.getElementById("status");
  statusEl.textContent = message || "";
  statusEl.classList.toggle("error", isError);
}

function fmt(value, digits = 3) {
  if (value === null || value === undefined) {
    return "N/A";
  }
  if (typeof value !== "number") {
    return String(value);
  }
  return Number.isFinite(value) ? value.toFixed(digits) : "N/A";
}

function parseNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  return value;
}

function hexToRgba(hex, alpha) {
  const normalized = hex.replace("#", "");
  if (normalized.length !== 6) {
    return hex;
  }
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function metricPoint(metricRow, metricKey) {
  if (metricRow.sim_time_s === null || metricRow.sim_time_s === undefined) {
    return null;
  }

  if (metricKey === "speed") {
    return metricRow.speed_mps === null || metricRow.speed_mps === undefined
      ? null
      : { x: metricRow.sim_time_s, y: metricRow.speed_mps };
  }

  if (metricKey === "acceleration") {
    const ax = metricRow.acceleration_x;
    const ay = metricRow.acceleration_y;
    const az = metricRow.acceleration_z;
    if ([ax, ay, az].some((value) => value === null || value === undefined)) {
      return null;
    }
    const magnitude = Math.sqrt((ax * ax) + (ay * ay) + (az * az));
    return { x: metricRow.sim_time_s, y: magnitude };
  }

  if (metricKey === "steering") {
    return metricRow.steering === null || metricRow.steering === undefined
      ? null
      : { x: metricRow.sim_time_s, y: metricRow.steering };
  }

  if (metricKey === "throttle") {
    return metricRow.throttle === null || metricRow.throttle === undefined
      ? null
      : { x: metricRow.sim_time_s, y: metricRow.throttle };
  }

  if (metricKey === "brake") {
    return metricRow.brake === null || metricRow.brake === undefined
      ? null
      : { x: metricRow.sim_time_s, y: metricRow.brake };
  }

  return null;
}

function buildDatasets(metrics, enabledMetricKeys, runSuffix, isRunB = false) {
  const datasets = [];

  for (const metricKey of enabledMetricKeys) {
    const points = metrics
      .map((row) => metricPoint(row, metricKey))
      .filter((point) => point !== null);

    if (points.length === 0) {
      continue;
    }

    const color = metricConfig[metricKey].color;
    datasets.push({
      label: `${metricConfig[metricKey].label} (${runSuffix})`,
      data: points,
      borderColor: isRunB ? hexToRgba(color, 0.7) : color,
      backgroundColor: isRunB ? hexToRgba(color, 0.25) : color,
      borderWidth: 2,
      borderDash: isRunB ? [8, 4] : [],
      pointRadius: 0,
      tension: 0.15,
    });
  }

  return datasets;
}

function getEnabledMetrics() {
  const checkboxes = document.querySelectorAll("#metric-toggles input[type='checkbox']");
  return Array.from(checkboxes)
    .filter((cb) => cb.checked)
    .map((cb) => cb.dataset.metric);
}

function renderChart() {
  const ctx = document.getElementById("run-chart");
  const enabled = getEnabledMetrics();

  const datasets = [];
  if (currentRunDataA) {
    datasets.push(...buildDatasets(currentRunDataA.metrics || [], enabled, "A"));
  }
  if (compareMode && currentRunDataB) {
    datasets.push(...buildDatasets(currentRunDataB.metrics || [], enabled, "B", true));
  }

  if (chart) {
    chart.destroy();
  }

  chart = new Chart(ctx, {
    type: "line",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      interaction: {
        mode: "nearest",
        intersect: false,
      },
      scales: {
        x: {
          type: "linear",
          title: {
            display: true,
            text: "Simulation Time (s)",
          },
          ticks: { color: "#9eb0c4" },
          grid: { color: "#2e3b4a" },
        },
        y: {
          title: {
            display: true,
            text: "Value",
          },
          ticks: { color: "#9eb0c4" },
          grid: { color: "#2e3b4a" },
        },
      },
      plugins: {
        legend: {
          labels: {
            color: "#e8edf3",
          },
        },
      },
    },
  });
}

function renderMetadata() {
  const content = document.getElementById("metadata-content");
  if (!currentRunDataA) {
    content.textContent = "No run selected.";
    return;
  }

  const metadataA = currentRunDataA.metadata || {};
  const metadataB = currentRunDataB ? currentRunDataB.metadata || {} : null;

  let html = `
    <div><strong>Run A Dir:</strong> ${currentRunDirA || "N/A"}</div>
    <div><strong>Run A ID:</strong> ${metadataA.run_id || "N/A"}</div>
    <div><strong>Run A Status:</strong> ${metadataA.status || "N/A"}</div>
  `;

  if (compareMode) {
    html += `
      <div class="metadata-separator"></div>
      <div><strong>Run B Dir:</strong> ${currentRunDirB || "Not selected"}</div>
      <div><strong>Run B ID:</strong> ${metadataB ? (metadataB.run_id || "N/A") : "N/A"}</div>
      <div><strong>Run B Status:</strong> ${metadataB ? (metadataB.status || "N/A") : "N/A"}</div>
    `;
  }

  content.innerHTML = html;
}

function renderSummary() {
  const content = document.getElementById("summary-content");
  if (!currentRunDataA) {
    content.textContent = "No run selected.";
    return;
  }

  const summary = currentRunDataA.summary || {};
  content.innerHTML = `
    <div class="summary-label">Max Speed (m/s)</div><div>${fmt(summary.max_speed_mps)}</div>
    <div class="summary-label">Average Speed (m/s)</div><div>${fmt(summary.avg_speed_mps)}</div>
    <div class="summary-label">Total Collisions</div><div>${summary.total_collisions ?? "N/A"}</div>
    <div class="summary-label">Run Duration (s)</div><div>${fmt(summary.run_duration_s)}</div>
    <div class="summary-label">Average Acceleration (m/s^2)</div><div>${fmt(summary.avg_acceleration_mps2)}</div>
    <div class="summary-label">Metric Rows</div><div>${summary.metric_row_count ?? "N/A"}</div>
    <div class="summary-label">Events</div><div>${summary.event_count ?? "N/A"}</div>
  `;
}

function renderEvents() {
  const events = currentRunDataA && Array.isArray(currentRunDataA.events) ? [...currentRunDataA.events] : [];
  const list = document.getElementById("events-list");

  events.sort((a, b) => {
    const ta = a.sim_time_s;
    const tb = b.sim_time_s;
    if (ta === null || ta === undefined) {
      return tb === null || tb === undefined ? (a.frame ?? 0) - (b.frame ?? 0) : 1;
    }
    if (tb === null || tb === undefined) {
      return -1;
    }
    return ta - tb;
  });

  list.innerHTML = "";

  if (events.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No events found for this run.";
    list.appendChild(li);
    return;
  }

  for (const event of events) {
    const li = document.createElement("li");
    const eventType = event.event_type || "unknown";
    const frame = event.frame ?? "N/A";
    const simTime = event.sim_time_s === null || event.sim_time_s === undefined ? "N/A" : fmt(event.sim_time_s);
    li.textContent = `${eventType} | frame=${frame} | sim_time_s=${simTime}`;
    list.appendChild(li);
  }
}

function normalizeEventType(eventType) {
  return String(eventType || "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}

function eventCountSummary(runData) {
  const events = Array.isArray(runData?.events) ? runData.events : [];
  let collisions = 0;
  let laneInvasions = 0;

  for (const event of events) {
    const eventType = normalizeEventType(event.event_type);
    if (eventType.includes("collision")) {
      collisions += 1;
    }
    if (eventType.includes("lane_invasion")) {
      laneInvasions += 1;
    }
  }

  return {
    total: events.length,
    collisions,
    laneInvasions,
  };
}

function formatDelta(aValue, bValue, digits = 3) {
  const aNum = parseNumber(aValue);
  const bNum = parseNumber(bValue);
  if (aNum === null || bNum === null) {
    return "N/A";
  }
  const delta = bNum - aNum;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(digits)}`;
}

function comparisonRowHtml(label, aValue, bValue, digits = 3) {
  return `
    <tr>
      <td>${label}</td>
      <td>${fmt(aValue, digits)}</td>
      <td>${fmt(bValue, digits)}</td>
      <td>${formatDelta(aValue, bValue, digits)}</td>
    </tr>
  `;
}

function renderComparisonPanel() {
  const panel = document.getElementById("comparison-panel");
  const content = document.getElementById("comparison-content");

  if (!compareMode) {
    panel.classList.add("hidden");
    content.textContent = "Enable compare mode and select Run B.";
    return;
  }

  panel.classList.remove("hidden");

  if (!currentRunDataA) {
    content.textContent = "Run A is not loaded.";
    return;
  }

  if (!currentRunDataB) {
    content.textContent = "Select Run B to compare.";
    return;
  }

  const summaryA = currentRunDataA.summary || {};
  const summaryB = currentRunDataB.summary || {};
  const eventsA = eventCountSummary(currentRunDataA);
  const eventsB = eventCountSummary(currentRunDataB);

  const summaryRows = comparisonFields
    .map((field) => comparisonRowHtml(field.label, summaryA[field.key], summaryB[field.key], field.digits))
    .join("");

  const eventRows = [
    comparisonRowHtml("Total Events", eventsA.total, eventsB.total, 0),
    comparisonRowHtml("Collision Events", eventsA.collisions, eventsB.collisions, 0),
    comparisonRowHtml("Lane Invasion Events", eventsA.laneInvasions, eventsB.laneInvasions, 0),
  ].join("");

  content.innerHTML = `
    <div class="comparison-run-labels">
      <span><strong>Run A:</strong> ${currentRunDirA}</span>
      <span><strong>Run B:</strong> ${currentRunDirB}</span>
    </div>
    <table class="comparison-table">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Run A</th>
          <th>Run B</th>
          <th>Delta (B - A)</th>
        </tr>
      </thead>
      <tbody>
        ${summaryRows}
        ${eventRows}
      </tbody>
    </table>
  `;
}

function renderAll() {
  renderMetadata();
  renderSummary();
  renderEvents();
  renderChart();
  renderComparisonPanel();
}

async function fetchJson(url) {
  const response = await fetch(url);
  let payload = null;
  try {
    payload = await response.json();
  } catch (_err) {
    payload = null;
  }

  if (!response.ok) {
    const errorMsg = payload && payload.error ? payload.error : `Request failed (${response.status})`;
    throw new Error(errorMsg);
  }

  return payload;
}

async function loadRunA(runDirName) {
  setStatus(`Loading Run A: ${runDirName}...`);
  try {
    const runData = await fetchJson(`/api/runs/${encodeURIComponent(runDirName)}`);
    currentRunDataA = runData;
    currentRunDirA = runDirName;
    renderAll();
    setStatus(`Loaded Run A: ${runDirName}`);
  } catch (err) {
    currentRunDataA = null;
    currentRunDirA = "";
    renderAll();
    setStatus(`Failed to load Run A: ${err.message}`, true);
  }
}

async function loadRunB(runDirName) {
  if (!runDirName) {
    currentRunDataB = null;
    currentRunDirB = "";
    renderAll();
    return;
  }

  setStatus(`Loading Run B: ${runDirName}...`);
  try {
    const runData = await fetchJson(`/api/runs/${encodeURIComponent(runDirName)}`);
    currentRunDataB = runData;
    currentRunDirB = runDirName;
    renderAll();
    setStatus(`Loaded Run B: ${runDirName}`);
  } catch (err) {
    currentRunDataB = null;
    currentRunDirB = "";
    renderAll();
    setStatus(`Failed to load Run B: ${err.message}`, true);
  }
}

function populateSelectors(runs) {
  const selectorA = document.getElementById("run-selector");
  const selectorB = document.getElementById("run-selector-b");

  selectorA.innerHTML = "";
  selectorB.innerHTML = "<option value=''>Select Run B</option>";

  runs.forEach((run) => {
    const runId = run.run_id || "no-run-id";
    const status = run.status || "unknown";
    const label = `${run.run_dir_name} (${runId}, ${status})`;

    const optionA = document.createElement("option");
    optionA.value = run.run_dir_name;
    optionA.textContent = label;
    selectorA.appendChild(optionA);

    const optionB = document.createElement("option");
    optionB.value = run.run_dir_name;
    optionB.textContent = label;
    selectorB.appendChild(optionB);
  });
}

function updateCompareControls() {
  const toggle = document.getElementById("compare-toggle");
  const runBControl = document.getElementById("run-b-control");
  const selectorB = document.getElementById("run-selector-b");

  compareMode = toggle.checked;
  runBControl.classList.toggle("hidden", !compareMode);
  runBControl.setAttribute("aria-hidden", String(!compareMode));
  selectorB.disabled = !compareMode;

  if (!compareMode) {
    currentRunDataB = null;
    currentRunDirB = "";
    selectorB.value = "";
  }

  renderAll();
}

async function loadRuns() {
  const selectorA = document.getElementById("run-selector");
  const selectorB = document.getElementById("run-selector-b");
  const compareToggle = document.getElementById("compare-toggle");

  setStatus("Loading runs...");

  try {
    const runs = await fetchJson("/api/runs");
    availableRuns = Array.isArray(runs) ? runs : [];

    if (availableRuns.length === 0) {
      selectorA.disabled = true;
      selectorB.disabled = true;
      compareToggle.disabled = true;
      selectorA.innerHTML = "<option>No runs available</option>";
      selectorB.innerHTML = "<option value=''>No runs available</option>";
      renderAll();
      setStatus("No runs found under runs/.");
      return;
    }

    selectorA.disabled = false;
    compareToggle.disabled = false;
    populateSelectors(availableRuns);

    const firstRun = availableRuns[0].run_dir_name;
    selectorA.value = firstRun;
    await loadRunA(firstRun);
  } catch (err) {
    selectorA.disabled = true;
    selectorB.disabled = true;
    compareToggle.disabled = true;
    selectorA.innerHTML = "<option>Error loading runs</option>";
    selectorB.innerHTML = "<option value=''>Error loading runs</option>";
    renderAll();
    setStatus(`Failed to load runs: ${err.message}`, true);
  }
}

function bindEvents() {
  const selectorA = document.getElementById("run-selector");
  const selectorB = document.getElementById("run-selector-b");
  const compareToggle = document.getElementById("compare-toggle");

  selectorA.addEventListener("change", async () => {
    if (!selectorA.value) {
      return;
    }
    await loadRunA(selectorA.value);
  });

  selectorB.addEventListener("change", async () => {
    if (!compareMode) {
      return;
    }

    if (!selectorB.value) {
      currentRunDataB = null;
      currentRunDirB = "";
      renderAll();
      setStatus("Select Run B to compare.");
      return;
    }

    await loadRunB(selectorB.value);
  });

  compareToggle.addEventListener("change", async () => {
    updateCompareControls();
    if (!compareMode) {
      setStatus("Compare mode disabled.");
      return;
    }

    if (!selectorB.value) {
      setStatus("Compare mode enabled. Select Run B to start comparison.");
      return;
    }

    await loadRunB(selectorB.value);
  });

  const toggles = document.querySelectorAll("#metric-toggles input[type='checkbox']");
  toggles.forEach((toggle) => {
    toggle.addEventListener("change", () => {
      if (currentRunDataA) {
        renderChart();
      }
    });
  });
}

window.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  updateCompareControls();
  await loadRuns();
});
