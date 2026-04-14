# CARLA Observability Toolkit
Work in progress.

An observability and telemetry system for the CARLA autonomous driving simulator, designed to capture, validate, and analyze simulation runs as reproducible datasets.

This project adds structured logging, metrics collection, and experiment instrumentation to CARLA simulation runs. The goal is to make simulation experiments easier to analyze, reproduce, and visualize.

The toolkit transforms CARLA simulation runs into structured, validated datasets that can be analyzed, compared, and visualized.

The system is built around a run-centric data model, where each simulation execution produces a self-contained dataset that can be validated, analyzed, and visualized.

---

## Project Goals

The toolkit focuses on three main areas:

- **Simulation Telemetry**
  - Vehicle metrics (speed, acceleration, steering)
  - Event logging (collisions, run lifecycle events)
  - Sensor data summaries

- **Structured Logging**
  - JSON event logs
  - CSV metrics output
  - Time-series compatible data

- **Experiment Analysis**
  - Run metadata tracking
  - Dataset generation from simulation runs
  - Visualization through a lightweight dashboard

---

## Current Status

Current development includes:

- Metric bus architecture
- Event logging pipeline
- CSV metrics export
- Simulation run instrumentation
- Dashboard prototype

---

## System Architecture

The toolkit is organized as a run-centric observability pipeline:

![img.png](img.png)

Primary modules:

- `cot.core.metric_bus` – in-process pub/sub backbone
- `cot.core.event_collector` – event ingestion
- `cot.core.vehicle_metrics_collector` – vehicle telemetry
- `cot.core.logger` – artifact persistence
- `cot.core.run_data_loader` – artifact parsing
- `cot.core.run_statistics` – run summary metrics
- `cot.core.run_validator` – integrity validation

---

## How It Works

- **Collectors**
  - Transform CARLA data into structured telemetry messages
  - Include `run_id`, `frame`, `sim_time_s`

- **MetricBus**
  - Routes telemetry via topic-based pub/sub
  - Decouples producers from consumers

- **Logging**
  - `RunLogger` writes:
    - `metadata.json`
    - `metrics.csv`
    - `events.json`

- **Run Artifacts**
  - Self-contained datasets per run

- **Validation**
  - Ensures correctness and consistency across artifacts

---

## Getting Started

### Prerequisites

- Python 3.10+
- CARLA running on `localhost:2000`
- Active ego/hero vehicle

---

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

# Running the Client
Generate simulation runs interactively:

```powershell
python src/cot/client/run_controls_smoke.py
```

### Controls

- `F5` — start run
- `F6` — stop run

Stopping a run creates:
```
  runs/<run_dir>/
  metadata.json
  metrics.csv
  events.json
```

### Example Output

Each run produces:

- metrics.csv
- events.json
- metadata.json

## Validation

Single Run

```powershell
python scripts/validate_run.py
```

Multi-run Smoke Test

```powershell
python scripts/validate_runs.py
python scripts/validate_runs.py --last 3
python scripts/validate_runs.py --all
```

Generating a Summary Report

```powershell
python scripts/generate_experiment_report.py <run_name>
```

Generates:
- summary_report.json

---

# Running the Web Dashboard

The toolkit includes a lightweight web dashboard for visualizing and comparing runs.
Start the Dashboard

```powershell
python dashboard/app.py
```

Open in browser:
`http://127.0.0.1:5000`

---

## Dashboard Features

# Run Selection
- Select Run A from dropdown
- Loads full dataset

---

## Metric Visualization
- Time-series charts:
  - Speed
  - Acceleration
  - Steering
  - Throttle
  - Brake
- Toggle metric on/off

---

## Event Timeline
- Displays ordered events
- Sorted by simulation time

---

## Summary Statistics
- Max speed
- Average speed
- Total collisions
- Run duration
- Event counts

---

## Run Comparison
- Enable "Compare"
- Select Run B
- View:
  - Side-by-side stats
  - Delta values
  - Overlaid charts

---

## API Endpoints
- `GET /api/runs`
- `GET /api/runs/<run> → full run data`

---

# Demo Workflow
1. Start CARLA Server
2. Run a client such as manual_control.py from the python examples in Carla. A vehicle needs to be spawned.
3. Run the COT client via

```powershell
python src/cot/client/run_controls_smoke.py
```

4. Generate a run F5 to start the run and F6 to stop it.
5. Validate

```powershell
python scripts/validate_run.py
```

6. View in dashboard

```powershell
python dashboard/app.py
```

---

## Road map
- Real-time streaming
- Advanced analytics
- Multi-run comparisons
- Reproducibility tooling

---

# Tech Stack
- Python
- CARLA
- Flask
- Chart.js
- JSON / CSV

---

# Author
Cameron Basham
Software Engineering Student