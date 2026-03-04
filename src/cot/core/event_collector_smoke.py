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
from cot.core.run_manager import RunManager
from cot.core.vehicle_spawner import VehicleSpawner


def main() -> None:
    client = make_client()
    world = client.get_world()
    bus = MetricBus()
    rm = RunManager()

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

    state = rm.start_run(world, vehicle, run_id="smoke")
    print(
        f"run_id={state.run_id} map_name={state.map_name} "
        f"vehicle_blueprint={state.vehicle_blueprint}"
    )
    logger = RunLogger(
        bus,
        run_id=state.run_id,
        run_metadata={
            "map_name": state.map_name,
            "weather": state.weather,
            "vehicle_blueprint": state.vehicle_blueprint,
        },
    )
    collector = EventCollector(world, vehicle, bus, run_id=state.run_id)

    def handler(msg: TelemetryMessage) -> None:
        print(f"{msg.topic} frame={msg.frame} payload={msg.payload}")

    bus.subscribe("metric.event.", handler)

    print("Drive into something to trigger collision; cross lane marking to trigger lane invasion.")

    try:
        for _ in range(600):
            world.wait_for_tick(1.0)
    finally:
        rm.stop_run()
        if hasattr(collector, "close") and callable(collector.close):
            collector.close()
        logger.close()
        bus.close(drain=True)
        print("event collector smoke complete")


if __name__ == "__main__":
    main()
