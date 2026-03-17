let chart = null;
let currentRunData = null;

const metricConfig = {
  speed: { label: "Speed (m/s)", color: "#4db2ff" },
  acceleration: { label: "Acceleration |a| (m/s^2)", color: "#ff9f40" },
  steering: { label: "Steering", color: "#8ad66d" },
  throttle: { label: "Throttle", color: "#c792ea" },
  brake: { label: "Brake", color: "#ff6384" },
};

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

function buildDatasets(metrics, enabledMetricKeys) {
  const datasets = [];

  for (const metricKey of enabledMetricKeys) {
    const points = metrics
      .map((row) => metricPoint(row, metricKey))
      .filter((point) => point !== null);

    if (points.length === 0) {
      continue;
    }

    datasets.push({
      label: metricConfig[metricKey].label,
      data: points,
      borderColor: metricConfig[metricKey].color,
      backgroundColor: metricConfig[metricKey].color,
      borderWidth: 2,
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

function renderChart(runData) {
  const enabled = getEnabledMetrics();
  const datasets = buildDatasets(runData.metrics || [], enabled);
  const ctx = document.getElementById("run-chart");

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

function renderMetadata(runData, runDirName) {
  const metadata = runData.metadata || {};
  const content = document.getElementById("metadata-content");

  const runId = metadata.run_id || "N/A";
  const status = metadata.status || "N/A";

  content.innerHTML = `
    <div><strong>Run Dir:</strong> ${runDirName}</div>
    <div><strong>Run ID:</strong> ${runId}</div>
    <div><strong>Status:</strong> ${status}</div>
  `;
}

function renderSummary(runData) {
  const summary = runData.summary || {};
  const content = document.getElementById("summary-content");

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

function renderEvents(runData) {
  const events = Array.isArray(runData.events) ? [...runData.events] : [];
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

function renderRun(runData, runDirName) {
  currentRunData = runData;
  renderMetadata(runData, runDirName);
  renderSummary(runData);
  renderEvents(runData);
  renderChart(runData);
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

async function loadRunDetails(runDirName) {
  setStatus(`Loading run: ${runDirName}...`);
  try {
    const runData = await fetchJson(`/api/runs/${encodeURIComponent(runDirName)}`);
    renderRun(runData, runDirName);
    setStatus(`Loaded run: ${runDirName}`);
  } catch (err) {
    setStatus(`Failed to load run: ${err.message}`, true);
  }
}

async function loadRuns() {
  const selector = document.getElementById("run-selector");
  setStatus("Loading runs...");

  try {
    const runs = await fetchJson("/api/runs");
    selector.innerHTML = "";

    if (!Array.isArray(runs) || runs.length === 0) {
      selector.disabled = true;
      selector.innerHTML = "<option>No runs available</option>";
      setStatus("No runs found under runs/.");
      return;
    }

    selector.disabled = false;
    runs.forEach((run) => {
      const option = document.createElement("option");
      option.value = run.run_dir_name;
      const runId = run.run_id || "no-run-id";
      const status = run.status || "unknown";
      option.textContent = `${run.run_dir_name} (${runId}, ${status})`;
      selector.appendChild(option);
    });

    await loadRunDetails(runs[0].run_dir_name);
  } catch (err) {
    selector.disabled = true;
    selector.innerHTML = "<option>Error loading runs</option>";
    setStatus(`Failed to load runs: ${err.message}`, true);
  }
}

function bindEvents() {
  const selector = document.getElementById("run-selector");
  selector.addEventListener("change", () => {
    if (!selector.value) {
      return;
    }
    loadRunDetails(selector.value);
  });

  const toggles = document.querySelectorAll("#metric-toggles input[type='checkbox']");
  toggles.forEach((toggle) => {
    toggle.addEventListener("change", () => {
      if (currentRunData) {
        renderChart(currentRunData);
      }
    });
  });
}

window.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  await loadRuns();
});
