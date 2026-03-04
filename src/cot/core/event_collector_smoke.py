from __future__ import annotations

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.carla_client import make_client
from cot.core.event_collector import EventCollector
from cot.core.logger import RunLogger
from cot.core.metric_bus import MetricBus, TelemetryMessage
from cot.core.vehicle_spawner import VehicleSpawner


def main() -> None:
    client = make_client()
    world = client.get_world()
    bus = MetricBus()
    logger = RunLogger(bus, run_id="smoke")

    spawner = VehicleSpawner(world)
    vehicle = None
    for _ in range(100):
        vehicle = spawner.find_ego_vehicle()
        if vehicle is not None and vehicle.attributes.get("role_name") == "hero":
            break
        world.wait_for_tick(1.0)
    if vehicle is None or vehicle.attributes.get("role_name") != "hero":
        raise RuntimeError(
            "Hero vehicle not found. Start CARLA manual_control.py first, then rerun this smoke test."
        )

    collector = EventCollector(world, vehicle, bus, run_id="smoke")

    def handler(msg: TelemetryMessage) -> None:
        print(f"{msg.topic} frame={msg.frame} payload={msg.payload}")

    bus.subscribe("metric.event.", handler)

    print("Drive into something to trigger collision; cross lane marking to trigger lane invasion.")

    try:
        for _ in range(600):
            world.wait_for_tick(1.0)
    finally:
        if hasattr(collector, "close") and callable(collector.close):
            collector.close()
        logger.close()
        bus.close(drain=True)
        print("event collector smoke complete")


if __name__ == "__main__":
    main()
