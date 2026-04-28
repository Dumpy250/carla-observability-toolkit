from __future__ import annotations

from math import sqrt

import carla

from cot.bus.metric_bus import MetricBus, TelemetryMessage


class EventCollector:
    """Collects discrete CARLA events and publishes them to MetricBus."""

    def __init__(
        self,
        world: carla.World,
        vehicle: carla.Vehicle,
        metric_bus: MetricBus,
        run_id: str,
    ) -> None:
        self.world = world
        self.vehicle = vehicle
        self.metric_bus = metric_bus
        self.run_id = run_id
        self._collision_sensor: carla.Sensor | None = None
        self._lane_invasion_sensor: carla.Sensor | None = None
        self._attach_sensors()

    def _attach_sensors(self) -> None:
        blueprint_library = self.world.get_blueprint_library()

        collision_bp = blueprint_library.find("sensor.other.collision")
        lane_invasion_bp = blueprint_library.find("sensor.other.lane_invasion")

        sensor_transform = carla.Transform()
        self._collision_sensor = self.world.spawn_actor(
            collision_bp,
            sensor_transform,
            attach_to=self.vehicle,
        )
        self._lane_invasion_sensor = self.world.spawn_actor(
            lane_invasion_bp,
            sensor_transform,
            attach_to=self.vehicle,
        )

        self._collision_sensor.listen(self._on_collision)
        self._lane_invasion_sensor.listen(self._on_lane_invasion)

    def _on_collision(self, event: carla.CollisionEvent) -> None:
        other_actor = getattr(event, "other_actor", None)
        other_actor_type = other_actor.type_id if other_actor is not None else None

        impulse = event.normal_impulse
        impulse_magnitude = sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)

        payload = {
            "run_id": self.run_id,
            "frame": event.frame,
            "type": "collision",
            "other_actor": other_actor_type,
            "impulse": impulse_magnitude,
        }

        print(
            f"[event] collision frame={event.frame} other={other_actor_type} "
            f"impulse={impulse_magnitude:.3f}"
        )
        self._publish("metric.event.collision", event.frame, payload)

    def _on_lane_invasion(self, event: carla.LaneInvasionEvent) -> None:
        markings = [str(marking.type) for marking in event.crossed_lane_markings]

        payload = {
            "run_id": self.run_id,
            "frame": event.frame,
            "type": "lane_invasion",
            "markings": markings,
        }

        print(f"[event] lane_invasion frame={event.frame} markings={markings}")
        self._publish("metric.event.lane_invasion", event.frame, payload)

    def _publish(self, topic: str, frame: int, payload: dict) -> None:
        sim_time_s = self.world.get_snapshot().timestamp.elapsed_seconds
        try:
            self.metric_bus.publish(
                topic=topic,
                run_id=self.run_id,
                frame=frame,
                sim_time_s=sim_time_s,
                payload=payload,
            )
        except TypeError:
            self.metric_bus.publish(
                TelemetryMessage(
                    topic=topic,
                    run_id=self.run_id,
                    frame=frame,
                    sim_time_s=sim_time_s,
                    payload=payload,
                )
            )

    def close(self) -> None:
        """Stop and destroy attached sensors."""
        if self._collision_sensor is not None:
            try:
                self._collision_sensor.stop()
            except Exception:
                pass
            try:
                self._collision_sensor.destroy()
            except Exception:
                pass
            self._collision_sensor = None

        if self._lane_invasion_sensor is not None:
            try:
                self._lane_invasion_sensor.stop()
            except Exception:
                pass
            try:
                self._lane_invasion_sensor.destroy()
            except Exception:
                pass
            self._lane_invasion_sensor = None
