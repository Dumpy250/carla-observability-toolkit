from __future__ import annotations

from math import sqrt

import carla

from .metric_bus import MetricBus, TelemetryMessage
from .vehicle_spawner import VehicleSpawner


class VehicleMetricsCollector:
    """Collects vehicle telemetry from CARLA each simulation tick.

    This collector is responsible for finding the ego vehicle and publishing
    vehicle state metrics to the MetricBus.
    """

    def __init__(self, metric_bus: MetricBus, world: carla.World, run_id: str) -> None:
        self.metric_bus = metric_bus
        self.world = world
        self.run_id = run_id
        self._spawner = VehicleSpawner(world)

    def tick(self, snapshot):
        """Handles one CARLA simulation tick and publishes vehicle state telemetry."""
        ego_vehicle = self._spawner.find_first_vehicle()
        if ego_vehicle is None:
            return

        if not getattr(ego_vehicle, "is_alive", True):
            return

        try:
            v = ego_vehicle.get_velocity()
            speed_mps = sqrt(v.x**2 + v.y**2 + v.z**2)

            a = ego_vehicle.get_acceleration()

            transform = ego_vehicle.get_transform()
            location = transform.location
            rotation = transform.rotation

            control = ego_vehicle.get_control()

            metrics = {
                "speed_mps": speed_mps,
                "acceleration": {
                    "x": a.x,
                    "y": a.y,
                    "z": a.z,
                },
                "steering": control.steer,
                "throttle": control.throttle,
                "brake": control.brake,
                "position": {
                    "x": location.x,
                    "y": location.y,
                    "z": location.z,
                },
                "heading": rotation.yaw,
            }
        except RuntimeError as exc:
            if not getattr(ego_vehicle, "is_alive", True):
                return
            raise RuntimeError(
                f"Vehicle telemetry extraction failed for run_id={self.run_id}, "
                f"frame={snapshot.frame}: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Vehicle telemetry extraction failed for run_id={self.run_id}, frame={snapshot.frame}: {exc}"
            ) from exc

        try:
            self.metric_bus.publish(
                topic="metric.vehicle.state",
                run_id=self.run_id,
                frame=snapshot.frame,
                sim_time_s=snapshot.timestamp.elapsed_seconds,
                payload=metrics,
            )
        except TypeError:
            self.metric_bus.publish(
                TelemetryMessage(
                    topic="metric.vehicle.state",
                    run_id=self.run_id,
                    frame=snapshot.frame,
                    sim_time_s=snapshot.timestamp.elapsed_seconds,
                    payload=metrics,
                )
            )
