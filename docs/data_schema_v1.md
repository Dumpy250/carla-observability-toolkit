# CARLA Observability Toolkit — Data Schema v1

Schema version: v1  
Target: CARLA Python API 0.10.0  

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

### Required fields
- `run_id` (string, uuid)
- `schema_version` (string) = "v1"
- `carla.server_version` (string)
- `carla.client_version` (string)
- `carla.map_name` (string)

### Optional fields
- `world_settings` (object)
- `started_wall_time_utc_s` (float)
- `tags` (object)

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
# Object: MetricSample
**Required fields**
- run_id (string)
- frame (int)
- sim_time_s (float)
- metric (string)
- value (number|bool|string|object)
- dtype (string)

# Optional fields
- unit (string)
- source (string)
- actor_id (int)
- sensor_id (int)
- wall_time_utc_s (float)
- tags (object)

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

# Object: Event
**Required fields**
- run_id (string)
- frame (int)
- sim_time_s (float)
- event_type (string)
- payload (object)

**Optional fields**
- actor_id (int)
- sensor_id (int)
- other_actor_id (int)
- intensity (float)
- wall_time_utc_s (float)
- tags (object)

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