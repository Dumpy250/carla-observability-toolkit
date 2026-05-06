let chart = null;
let currentRunDataA = null;
let currentRunDataB = null;
let currentRunDirA = "";
let currentRunDirB = "";
let compareMode = false;
let availableRuns = [];

const NO_DATA_LABEL = "N/A";
const DEFAULT_DECIMAL_DIGITS = 3;
const CHART_LINE_WIDTH = 2;
const CHART_RUN_B_DASH = [8, 4];
const CHART_POINT_RADIUS = 0;
const CHART_LINE_TENSION = 0.15;
const RUN_SELECTOR_B_DEFAULT_OPTION = "<option value=''>Select Run B</option>";
const RUN_SELECTOR_B_NONE_OPTION = "<option value=''>No runs available</option>";
const RUN_SELECTOR_B_ERROR_OPTION = "<option value=''>Error loading runs</option>";

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

const METRIC_VALUE_EXTRACTORS = {
  speed(metricRow) {
    return metricRow.speed_mps === null || metricRow.speed_mps === undefined
      ? null
      : metricRow.speed_mps;
  },
  acceleration(metricRow) {
    const ax = metricRow.acceleration_x;
    const ay = metricRow.acceleration_y;
    const az = metricRow.acceleration_z;
    if ([ax, ay, az].some((value) => value === null || value === undefined)) {
      return null;
    }
    return Math.sqrt((ax * ax) + (ay * ay) + (az * az));
  },
  steering(metricRow) {
    return metricRow.steering === null || metricRow.steering === undefined
      ? null
      : metricRow.steering;
  },
  throttle(metricRow) {
    return metricRow.throttle === null || metricRow.throttle === undefined
      ? null
      : metricRow.throttle;
  },
  brake(metricRow) {
    return metricRow.brake === null || metricRow.brake === undefined
      ? null
      : metricRow.brake;
  },
};

function setStatus(message, isError = false) {
  const statusEl = document.getElementById("status");
  statusEl.textContent = message || "";
  statusEl.classList.toggle("error", isError);
}

function fmt(value, digits = DEFAULT_DECIMAL_DIGITS) {
  if (value === null || value === undefined) {
    return NO_DATA_LABEL;
  }
  if (typeof value !== "number") {
    return String(value);
  }
  return Number.isFinite(value) ? value.toFixed(digits) : NO_DATA_LABEL;
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

  if (!Object.prototype.hasOwnProperty.call(METRIC_VALUE_EXTRACTORS, metricKey)) {
    return null;
  }

  const yValue = METRIC_VALUE_EXTRACTORS[metricKey](metricRow);
  return yValue === null ? null : { x: metricRow.sim_time_s, y: yValue };
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
      borderWidth: CHART_LINE_WIDTH,
      borderDash: isRunB ? CHART_RUN_B_DASH : [],
      pointRadius: CHART_POINT_RADIUS,
      tension: CHART_LINE_TENSION,
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
    <div><strong>Run A ID:</strong> ${metadataA.run_id || NO_DATA_LABEL}</div>
    <div><strong>Run A Status:</strong> ${metadataA.status || NO_DATA_LABEL}</div>
  `;

  if (compareMode) {
    html += `
      <div class="metadata-separator"></div>
      <div><strong>Run B Dir:</strong> ${currentRunDirB || "Not selected"}</div>
      <div><strong>Run B ID:</strong> ${metadataB ? (metadataB.run_id || NO_DATA_LABEL) : NO_DATA_LABEL}</div>
      <div><strong>Run B Status:</strong> ${metadataB ? (metadataB.status || NO_DATA_LABEL) : NO_DATA_LABEL}</div>
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
    <div class="summary-label">Total Collisions</div><div>${summary.total_collisions ?? NO_DATA_LABEL}</div>
    <div class="summary-label">Run Duration (s)</div><div>${fmt(summary.run_duration_s)}</div>
    <div class="summary-label">Average Acceleration (m/s^2)</div><div>${fmt(summary.avg_acceleration_mps2)}</div>
    <div class="summary-label">Metric Rows</div><div>${summary.metric_row_count ?? NO_DATA_LABEL}</div>
    <div class="summary-label">Events</div><div>${summary.event_count ?? NO_DATA_LABEL}</div>
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
    const frame = event.frame ?? NO_DATA_LABEL;
    const simTime = event.sim_time_s === null || event.sim_time_s === undefined ? NO_DATA_LABEL : fmt(event.sim_time_s);
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

function formatDelta(aValue, bValue, digits = DEFAULT_DECIMAL_DIGITS) {
  const aNum = parseNumber(aValue);
  const bNum = parseNumber(bValue);
  if (aNum === null || bNum === null) {
    return NO_DATA_LABEL;
  }
  const delta = bNum - aNum;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(digits)}`;
}

function comparisonRowHtml(label, aValue, bValue, digits = DEFAULT_DECIMAL_DIGITS) {
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
    clearRunBState();
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
  selectorB.innerHTML = RUN_SELECTOR_B_DEFAULT_OPTION;

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

function clearRunBData() {
  currentRunDataB = null;
  currentRunDirB = "";
}

function clearRunBState(selectorB = null) {
  clearRunBData();
  if (selectorB) {
    selectorB.value = "";
  }
  renderAll();
}

function setRunsControlsEnabledState(selectorA, selectorB, compareToggle, enabled) {
  selectorA.disabled = !enabled;
  selectorB.disabled = !enabled;
  compareToggle.disabled = !enabled;
}

function setRunSelectorsPlaceholder(selectorA, selectorB, selectorAText, selectorBHtml) {
  selectorA.innerHTML = selectorAText;
  selectorB.innerHTML = selectorBHtml;
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
    clearRunBData();
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
      setRunsControlsEnabledState(selectorA, selectorB, compareToggle, false);
      setRunSelectorsPlaceholder(
        selectorA,
        selectorB,
        "<option>No runs available</option>",
        RUN_SELECTOR_B_NONE_OPTION
      );
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
    setRunsControlsEnabledState(selectorA, selectorB, compareToggle, false);
    setRunSelectorsPlaceholder(
      selectorA,
      selectorB,
      "<option>Error loading runs</option>",
      RUN_SELECTOR_B_ERROR_OPTION
    );
    renderAll();
    setStatus(`Failed to load runs: ${err.message}`, true);
  }
}

async function handleRunASelectorChange(selectorA) {
  if (!selectorA.value) {
    return;
  }
  await loadRunA(selectorA.value);
}

async function handleRunBSelectorChange(selectorB) {
  if (!compareMode) {
    return;
  }

  if (!selectorB.value) {
    clearRunBState();
    setStatus("Select Run B to compare.");
    return;
  }

  await loadRunB(selectorB.value);
}

async function handleCompareToggleChange(selectorB) {
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
}

function bindMetricToggleEvents() {
  const toggles = document.querySelectorAll("#metric-toggles input[type='checkbox']");
  toggles.forEach((toggle) => {
    toggle.addEventListener("change", () => {
      if (currentRunDataA) {
        renderChart();
      }
    });
  });
}

function bindEvents() {
  const selectorA = document.getElementById("run-selector");
  const selectorB = document.getElementById("run-selector-b");
  const compareToggle = document.getElementById("compare-toggle");

  selectorA.addEventListener("change", async () => handleRunASelectorChange(selectorA));
  selectorB.addEventListener("change", async () => handleRunBSelectorChange(selectorB));
  compareToggle.addEventListener("change", async () => handleCompareToggleChange(selectorB));
  bindMetricToggleEvents();
}

window.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  updateCompareControls();
  await loadRuns();
});
