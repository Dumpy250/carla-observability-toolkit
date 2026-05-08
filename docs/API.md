# CARLA Observability Toolkit API (Proof of Concept)

## Purpose

The CARLA Observability Toolkit API provides run data to the React dashboard.
It reads generated run artifacts from `runs/` and exposes:

- A run list endpoint for discovery.
- A run details endpoint for metadata, summary statistics, telemetry metrics, and events.

The React frontend consumes these endpoints through frontend/src/services/runsApi.js.

Base URL (local default): `http://127.0.0.1:5000`

See also:
- docs/state_diagram_v1.png
- docs/run_model.md
- 
## Architecture Context

The Flask backend acts as a lightweight API layer between generated CARLA run artifacts and the React dashboard frontend.  
Run data is loaded from the filesystem and transformed into API responses consumed by the dashboard views.

## Endpoint: `GET /api/runs`

### Description

Returns available run directories, sorted newest first, with lightweight metadata used by the frontend run picker.

### Example request

```http
GET /api/runs HTTP/1.1
Host: 127.0.0.1:5000
```

### Example response

```json
[
  {
    "run_dir_name": "run_2026-05-07_21-34-18",
    "run_id": "a9e8f6c2-5f6d-4f2f-ae3b-cd4f2a7b1234",
    "status": "completed"
  },
  {
    "run_dir_name": "run_2026-05-07_20-58-43",
    "run_id": "1a22b333-44cc-55dd-66ee-777f88889990",
    "status": "completed"
  }
]
```

### Response fields

| Field | Type | Description |
|---|---|---|
| `run_dir_name` | string | Name of the run directory under `runs/`; used as the path parameter for run details. |
| `run_id` | string or null | Run identifier from `metadata.json` (null if unavailable). |
| `status` | string or null | Run status from `metadata.json` (null if unavailable). |

## Endpoint: `GET /api/runs/<run_dir_name>`

### Description

Returns full details for one run directory, including raw loaded artifacts and computed summary statistics.

### Example request

```http
GET /api/runs/run_2026-05-07_21-34-18 HTTP/1.1
Host: 127.0.0.1:5000
```

### Example response structure

```json
{
  "metadata": {
    "run_id": "a9e8f6c2-5f6d-4f2f-ae3b-cd4f2a7b1234",
    "status": "completed",
    "started_at": "2026-05-07T21:34:18Z",
    "ended_at": "2026-05-07T21:40:02Z"
  },
  "summary": {
    "max_speed_mps": 17.4,
    "avg_speed_mps": 9.8,
    "total_collisions": 1,
    "run_duration_s": 344.1,
    "avg_acceleration_mps2": 2.2,
    "metric_row_count": 1964,
    "event_count": 14
  },
  "metrics": [
    {
      "frame": 18211,
      "sim_time_s": 1342.1,
      "speed_mps": 10.3,
      "acceleration_x": 0.5,
      "acceleration_y": 0.0,
      "acceleration_z": 0.0,
      "steering": 0.04,
      "throttle": 0.38,
      "brake": 0.0,
      "position_x": 118.2,
      "position_y": 42.7,
      "position_z": 0.3,
      "heading": 91.6
    }
  ],
  "events": [
    {
      "run_id": "a9e8f6c2-5f6d-4f2f-ae3b-cd4f2a7b1234",
      "frame": 18350,
      "event_type": "collision",
      "sim_time_s": 1348.6,
      "payload": {
        "type": "collision",
        "frame": 18350,
        "sim_time_s": 1348.6,
        "other_actor_id": 245
      }
    }
  ]
}
```

### Response fields

#### `metadata` (object)

Metadata loaded directly from `metadata.json` for the selected run. This object is run-defined and may contain additional keys.

Common keys include:

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Unique run identifier. |
| `status` | string | Run lifecycle state (for example `completed`). |

#### `summary` (object)

Computed aggregate statistics from `metrics` and `events`.

| Field | Type | Description |
|---|---|---|
| `max_speed_mps` | number or null | Maximum observed speed. |
| `avg_speed_mps` | number or null | Mean observed speed. |
| `total_collisions` | integer | Count of events where `event_type == "collision"`. |
| `run_duration_s` | number or null | Duration based on metric timestamps (`max(sim_time_s) - min(sim_time_s)`). |
| `avg_acceleration_mps2` | number or null | Mean acceleration magnitude from `(x,y,z)` vectors. |
| `metric_row_count` | integer | Number of metric rows loaded. |
| `event_count` | integer | Number of events loaded. |

#### `metrics` (array<object>)

Time-series telemetry rows loaded from `metrics.csv`.

| Field | Type |
|---|---|
| `frame` | integer or null |
| `sim_time_s` | number or null |
| `speed_mps` | number or null |
| `acceleration_x` | number or null |
| `acceleration_y` | number or null |
| `acceleration_z` | number or null |
| `steering` | number or null |
| `throttle` | number or null |
| `brake` | number or null |
| `position_x` | number or null |
| `position_y` | number or null |
| `position_z` | number or null |
| `heading` | number or null |

#### `events` (array<object>)

Run events loaded from `events.json`.

| Field | Type | Description |
|---|---|---|
| `run_id` | string or null | Event run identifier when available. |
| `frame` | integer or null | Simulation frame for the event. |
| `event_type` | string or null | Normalized type field from event payload (`type`). |
| `sim_time_s` | number or null | Simulation timestamp for the event. |
| `payload` | object | Original event object content from `events.json`. |

## Common Error Responses

### `400 Bad Request` - invalid run directory name

```json
{
  "error": "Invalid run directory name"
}
```

### `404 Not Found` - run not found

```json
{
  "error": "Run not found: run_2026-05-07_21-34-18"
}
```

### `500 Internal Server Error` - failed to load run

```json
{
  "error": "Failed to load run: <loader exception message>"
}
```

## Usage Notes

- Start backend API server with:
  - `python backend/app.py`
- Ensure generated run artifacts exist under `runs/`.
- The React frontend consumes these endpoints automatically.

Implementation references:
- backend/app.py
- src/cot/core/run_loader.py
- src/cot/core/run_statistics.py