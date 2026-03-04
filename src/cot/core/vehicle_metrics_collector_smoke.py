from __future__ import annotations

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.carla_client import make_client
from cot.core.metric_bus import MetricBus
from cot.core.vehicle_metrics_collector import VehicleMetricsCollector
from cot.core.vehicle_spawner import VehicleSpawner


def main() -> None:
    client = make_client()
    world = client.get_world()

    bus = MetricBus()
    collector = VehicleMetricsCollector(bus, world, run_id="smoke")

    counter = {"n": 0}

    def handler(msg) -> None:
        counter["n"] += 1
        if counter["n"] % 20 == 0:
            payload = msg.payload
            print(
                f"frame={msg.frame} "
                f"speed={payload['speed_mps']:.2f} "
                f"heading={payload['heading']:.1f}"
            )

    bus.subscribe("metric.vehicle.state", handler)

    spawner = VehicleSpawner(world)
    spawner.ensure_vehicle()

    ticks = 200
    for _ in range(ticks):
        snapshot = world.wait_for_tick(1.0)
        collector.tick(snapshot)

    bus.close(drain=True)
    print(f"collector smoke complete: ticks={ticks}, received={counter['n']}")


if __name__ == "__main__":
    main()
