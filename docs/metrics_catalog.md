# CARLA Observability Toolkit — Metrics Catalog (v1)
Target: CARLA Python API 0.10.0  
Scope: Vehicle, World, Sensors, Events  
Note: “Tick” refers to `world.tick()` / `world.on_tick(callback)` cadence.

---
## 0) Timebase & Cadence Notes

- In asynchronous mode (`world.get_settings().synchronous_mode == False`), `world.get_snapshot().timestamp.delta_seconds` varies per tick.
- In synchronous mode, `fixed_delta_seconds` defines tick duration; `delta_seconds` should match it.
- Sensor streams provide `SensorData.frame` and `SensorData.timestamp` in seconds.

## 1.1 Actor Identity & Metadata

(Actor = carla.Actor; Vehicle inherits Actor)

| Metric                            | Units | Type            | Update     | Source                                        |
| --------------------------------- | ----: | --------------- | ---------- | --------------------------------------------- |
| actor.id                          |     - | int             | static     | `vehicle.id`                                  |
| actor.type_id                     |     - | string          | static     | `vehicle.type_id`                             |
| actor.is_alive                    |  bool | bool            | per tick   | `vehicle.is_alive`                            |
| actor.is_active                   |  bool | bool            | per tick   | `vehicle.is_active`                           |
| actor.actor_state                 |     - | enum            | per tick   | `vehicle.actor_state`                         |
| actor.attributes                  |     - | dict            | static     | `vehicle.attributes`                          |
| actor.bounding_box.extent.(x,y,z) |     m | vector3 (float) | static-ish | `vehicle.bounding_box.extent` *(half-extent)* |

Bounding box extent represents half-dimensions of the actor in meters.

### 1.2 Vehicle State

(Actor = carla.Vehicle)

| Metric                           | Units | Type  | Update   | Source                                   |   |                        |   |                          |
| -------------------------------- | ----: | ----- | -------- | ---------------------------------------- | - | ---------------------- | - | ------------------------ |
| vehicle.transform.location.x     |     m | float | per tick | `vehicle.get_transform().location.x`     |   |                        |   |                          |
| vehicle.transform.location.y     |     m | float | per tick | `vehicle.get_transform().location.y`     |   |                        |   |                          |
| vehicle.transform.location.z     |     m | float | per tick | `vehicle.get_transform().location.z`     |   |                        |   |                          |
| vehicle.transform.rotation.pitch |   deg | float | per tick | `vehicle.get_transform().rotation.pitch` |   |                        |   |                          |
| vehicle.transform.rotation.yaw   |   deg | float | per tick | `vehicle.get_transform().rotation.yaw`   |   |                        |   |                          |
| vehicle.transform.rotation.roll  |   deg | float | per tick | `vehicle.get_transform().rotation.roll`  |   |                        |   |                          |
| vehicle.velocity.x               |   m/s | float | per tick | `vehicle.get_velocity().x`               |   |                        |   |                          |
| vehicle.velocity.y               |   m/s | float | per tick | `vehicle.get_velocity().y`               |   |                        |   |                          |
| vehicle.velocity.z               |   m/s | float | per tick | `vehicle.get_velocity().z`               |   |                        |   |                          |
| vehicle.speed                    |   m/s | float | per tick | `                                        |   | vehicle.get_velocity() |   | ` *(computed magnitude)* |
| vehicle.acceleration.x           |  m/s² | float | per tick | `vehicle.get_acceleration().x`           |   |                        |   |                          |
| vehicle.acceleration.y           |  m/s² | float | per tick | `vehicle.get_acceleration().y`           |   |                        |   |                          |
| vehicle.acceleration.z           |  m/s² | float | per tick | `vehicle.get_acceleration().z`           |   |                        |   |                          |
| vehicle.angular_velocity.x       | rad/s | float | per tick | `vehicle.get_angular_velocity().x`       |   |                        |   |                          |
| vehicle.angular_velocity.y       | rad/s | float | per tick | `vehicle.get_angular_velocity().y`       |   |                        |   |                          |
| vehicle.angular_velocity.z       | rad/s | float | per tick | `vehicle.get_angular_velocity().z`       |   |                        |   |                          |


### 1.3 Control Inputs (Actor = `carla.Vehicle`)
| Metric                    | Units | Type  | Update   | Source                                    |
| ------------------------- | ----: | ----- | -------- | ----------------------------------------- |
| control.throttle          |  0..1 | float | per tick | `vehicle.get_control().throttle`          |
| control.steer             | -1..1 | float | per tick | `vehicle.get_control().steer`             |
| control.brake             |  0..1 | float | per tick | `vehicle.get_control().brake`             |
| control.hand_brake        |  bool | bool  | per tick | `vehicle.get_control().hand_brake`        |
| control.reverse           |  bool | bool  | per tick | `vehicle.get_control().reverse`           |
| control.manual_gear_shift |  bool | bool  | per tick | `vehicle.get_control().manual_gear_shift` |
| control.gear              |     - | int   | per tick | `vehicle.get_control().gear`              |


### 1.4 Physics & Geometry
| Metric                           | Units | Type    | Update     | Source                                                    |
| -------------------------------- | ----: | ------- | ---------- | --------------------------------------------------------- |
| vehicle.physics.mass             |    kg | float   | static-ish | `vehicle.get_physics_control().mass`                      |
| vehicle.physics.drag_coefficient |     - | float   | static-ish | `vehicle.get_physics_control().drag_coefficient`          |
| vehicle.physics.max_rpm          |   rpm | float   | static-ish | `vehicle.get_physics_control().max_rpm`                   |
| vehicle.physics.moi              | kg·m² | vector3 | static-ish | `vehicle.get_physics_control().moment_of_inertia`         |
| vehicle.wheels.count             |     - | int     | static-ish | `len(vehicle.get_physics_control().wheels)`               |
| vehicle.wheel[i].radius          |     m | float   | static-ish | `vehicle.get_physics_control().wheels[i].radius`          |
| vehicle.wheel[i].max_steer_angle |   deg | float   | static-ish | `vehicle.get_physics_control().wheels[i].max_steer_angle` |


### 1.5 Autopilot / Traffic Manager
| Metric                      | Units | Type | Update     | Source                                   |
| --------------------------- | ----: | ---- | ---------- | ---------------------------------------- |
| vehicle.autopilot_enabled   |  bool | bool | on change  | track calls to `vehicle.set_autopilot()` |
| vehicle.tm_port             |  port | int  | static-ish | port used when enabling autopilot        |
| vehicle.is_at_traffic_light |  bool | bool | per tick   | `vehicle.is_at_traffic_light()`          |
| vehicle.traffic_light_state |     - | enum | per tick   | `vehicle.get_traffic_light_state()`      |


> Note: Traffic Manager “state” is not broadly exposed as a queryable object; treat it as configuration + behavior observed via vehicle control/trajectory unless you find accessible TM getters.

### 1.6 World / Simulation
| Metric                             |  Units | Type         | Update     | Source                                              |
| ---------------------------------- | -----: | ------------ | ---------- | --------------------------------------------------- |
| world.frame                        |  frame | int          | per tick   | `world.get_snapshot().frame`                        |
| world.timestamp.elapsed_seconds    |      s | float        | per tick   | `world.get_snapshot().timestamp.elapsed_seconds`    |
| world.timestamp.delta_seconds      |      s | float        | per tick   | `world.get_snapshot().timestamp.delta_seconds`      |
| world.timestamp.platform_timestamp |      s | float        | per tick   | `world.get_snapshot().timestamp.platform_timestamp` |
| world.map.name                     |      - | string       | static-ish | `world.get_map().name`                              |
| world.settings.synchronous_mode    |   bool | bool         | on change  | `world.get_settings().synchronous_mode`             |
| world.settings.fixed_delta_seconds |      s | float / None | on change  | `world.get_settings().fixed_delta_seconds`          |
| world.settings.no_rendering_mode   |   bool | bool         | on change  | `world.get_settings().no_rendering_mode`            |
| world.weather.*                    | varies | object       | on change  | `world.get_weather()`                               |

---

## 2) Sensor Streams (continuous data + metadata)

### 2.1 Collision Sensor (Actor = `carla.Sensor`)
| Metric | Units | Type | Update | Source |
|---|---:|---|---|---|
| collision.event.count | - | int | per callback | increment in `sensor.listen(callback)` |

### 2.2 Lane Invasion Sensor
| Metric | Units | Type | Update | Source |
|---|---:|---|---|---|
| lane_invasion.event.count | - | int | per callback | increment in `sensor.listen(callback)` |

### 2.3 GNSS Sensor
| Metric | Units | Type | Update | Source |
|---|---:|---|---|---|
| gnss.lat | deg | float | per callback | `GNSSMeasurement.latitude` |
| gnss.lon | deg | float | per callback | `GNSSMeasurement.longitude` |
| gnss.alt | m | float | per callback | `GNSSMeasurement.altitude` |

### 2.4 IMU Sensor
| Metric | Units | Type | Update | Source |
|---|---:|---|---|---|
| imu.accel.x | m/s² | float | per callback | `IMUMeasurement.accelerometer.x` |
| imu.accel.y | m/s² | float | per callback | `IMUMeasurement.accelerometer.y` |
| imu.accel.z | m/s² | float | per callback | `IMUMeasurement.accelerometer.z` |
| imu.gyro.x | rad/s | float | per callback | `IMUMeasurement.gyroscope.x` |
| imu.gyro.y | rad/s | float | per callback | `IMUMeasurement.gyroscope.y` |
| imu.gyro.z | rad/s | float | per callback | `IMUMeasurement.gyroscope.z` |
| imu.compass | rad | float | per callback | `IMUMeasurement.compass` |

### 2.5 LiDAR Sensor (metadata only for v1)
| Metric | Units | Type | Update | Source |
|---|---:|---|---|---|
| lidar.points_per_frame | - | int | per callback | `len(LidarMeasurement)` or `measurement.raw_data` length logic |
| lidar.frame | frame | int | per callback | `measurement.frame` |
| lidar.timestamp | s | float | per callback | `measurement.timestamp` |

### 2.6 Camera Sensor (metadata only for v1)
| Metric | Units | Type | Update | Source |
|---|---:|---|---|---|
| camera.image_width | px | int | static-ish | blueprint attribute (e.g., `image_size_x`) |
| camera.image_height | px | int | static-ish | blueprint attribute (e.g., `image_size_y`) |
| camera.fov | deg | float | static-ish | blueprint attribute `fov` |
| camera.frame | frame | int | per callback | `Image.frame` |
| camera.timestamp | s | float | per callback | `Image.timestamp` |

---

## 3) Discrete Events (callbacks / lifecycle)

### 3.1 Collision Event (`carla.CollisionEvent`)
| Field                        | Units | Type    | Source                 |   |                |   |                |
| ---------------------------- | ----: | ------- | ---------------------- | - | -------------- | - | -------------- |
| event.frame                  | frame | int     | `event.frame`          |   |                |   |                |
| event.timestamp              |     s | float   | `event.timestamp`      |   |                |   |                |
| event.other_actor_id         |     - | int     | `event.other_actor.id` |   |                |   |                |
| event.normal_impulse.(x,y,z) |   N·s | vector3 | `event.normal_impulse` |   |                |   |                |
| event.intensity              |   N·s | float   | `                      |   | normal_impulse |   | ` *(computed)* |


### 3.2 Lane Invasion Event (`carla.LaneInvasionEvent`)
| Event Field | Units | Type | Source |
|---|---:|---|---|
| event.frame | frame | int | `event.frame` |
| event.timestamp | s | float | `event.timestamp` |
| event.crossed_lane_markings | - | list/enum | `event.crossed_lane_markings` |

### 3.3 Actor Spawn / Destruction (World-level)
| Event | Trigger | Notes |
|---|---|---|
| actor_spawned | detected via world snapshot actor set diff OR custom spawn wrapper | requires tracking previous actor IDs |
| actor_destroyed | detected via world snapshot actor set diff OR custom destroy wrapper | same |

### 3.4 Simulation / Run Lifecycle (Toolkit-level)
| Event | Trigger | Notes |
|---|---|---|
| run_started | when your RunManager starts | v2 sprint implements |
| run_stopped | when your RunManager stops | v2 sprint implements |
| sim_connected | when `carla.Client` connects | can log once per session |
