# CARLA Observability Toolkit — Data Schema v1

Schema version: v1  
Target: CARLA Python API 0.10.0  

**Decision:** v1 uses a “long” metric table (metric + value) to avoid schema churn as new metrics are added.

## Goals
- Support multiple runs
- Store time-series metrics + discrete events
- Align by simulation frame
- Keep simulation time as primary timeline, wall time optional

---

## Timestamp & Alignment Strategy

### Required time fields
- `frame` (int): simulation frame number (join key)
- `sim_time_s` (float): simulation elapsed seconds at `frame`

### Optional time fields
- `wall_time_utc_s` (float): epoch seconds for debugging/correlation

### Alignment rules
- Per-tick metrics use `world.get_snapshot()` for `frame` and `sim_time_s`
- Sensor callbacks use `SensorData.frame` and `SensorData.timestamp`
- Events inherit timing from the callback data + `frame`

---

## Object: Run
### Represents one simulation session.
#### Required Fields
| Field                | Type          | Description                    |
| -------------------- | ------------- | ------------------------------ |
| run_id               | string (UUID) | Unique identifier for this run |
| schema_version       | string        | Must equal `"v1"`              |
| carla.server_version | string        | CARLA server version           |
| carla.client_version | string        | CARLA Python client version    |
| carla.map_name       | string        | Map loaded during run          |


#### Optional fields
| Field                   | Type   | Description                      |
| ----------------------- | ------ | -------------------------------- |
| world_settings          | object | Snapshot of world settings       |
| started_wall_time_utc_s | float  | UTC epoch seconds when run began |
| tags                    | object | Arbitrary metadata tags          |


Example:
```json
{
  "schema_version": "v1",
  "run_id": "uuid",
  "carla": {
    "server_version": "0.10.0",
    "client_version": "0.10.0",
    "map_name": "Town10HD_Opt"
  },
  "world_settings": {
    "synchronous_mode": false,
    "fixed_delta_seconds": null,
    "no_rendering_mode": false
  },
  "started_wall_time_utc_s": 173xxxxxxx.x,
  "tags": { "purpose": "metrics-catalog-probe" }
}
```
## Object: MetricSample

### Represents one metric value at a specific simulation frame.
#### Required Fields
| Field      | Type                            | Description                                                    |
| ---------- | ------------------------------- | -------------------------------------------------------------- |
| run_id     | string                          | Foreign key to Run                                             |
| frame      | int                             | Simulation frame number (primary alignment key)                |
| sim_time_s | float                           | Simulation elapsed seconds                                     |
| metric     | string                          | Metric name (e.g. `"vehicle.speed"`)                           |
| value      | number | bool | string | object | Metric value                                                   |
| dtype      | string                          | Data type descriptor (`float`, `int`, `bool`, `vector3`, etc.) |


#### Optional fields
| Field           | Type   | Description                      |
| --------------- | ------ | -------------------------------- |
| unit            | string | Measurement unit (e.g., `"m/s"`) |
| source          | string | CARLA API source method          |
| actor_id        | int    | Actor associated with metric     |
| sensor_id       | int    | Sensor actor id                  |
| wall_time_utc_s | float  | Wall clock timestamp             |
| tags            | object | Additional metadata              |


Example:
```json
{
  "run_id": "uuid",
  "frame": 385128,
  "sim_time_s": 3929.9786,
  "metric": "vehicle.speed",
  "value": 0.00002676,
  "dtype": "float",
  "unit": "m/s",
  "source": "vehicle.get_velocity (magnitude)",
  "actor_id": 25
}
```

## Object: Event

### Represents a discrete event (collision, lane invasion, lifecycle event).
#### Required Fields
| Field      | Type   | Description                      |
| ---------- | ------ | -------------------------------- |
| run_id     | string | Foreign key to Run               |
| frame      | int    | Simulation frame                 |
| sim_time_s | float  | Simulation time                  |
| event_type | string | Event name (e.g., `"collision"`) |
| payload    | object | Event-specific data              |

#### Optional fields
| Field           | Type   | Description          |
| --------------- | ------ | -------------------- |
| actor_id        | int    | Primary actor        |
| sensor_id       | int    | Sensor actor         |
| other_actor_id  | int    | Secondary actor      |
| intensity       | float  | Event magnitude      |
| wall_time_utc_s | float  | Wall clock timestamp |
| tags            | object | Arbitrary metadata   |

Example:
```json
{
  "run_id": "uuid",
  "frame": 1050,
  "sim_time_s": 12.34,
  "event_type": "collision",
  "actor_id": 25,
  "other_actor_id": 345,
  "intensity": 120.5,
  "payload": {
    "normal_impulse": { "x": 1.2, "y": 0.4, "z": 0.0 }
  }
}
```