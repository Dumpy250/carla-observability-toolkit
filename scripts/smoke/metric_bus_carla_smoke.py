from __future__ import annotations

import pathlib
import sys
import time

import carla

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.bus.metric_bus import MetricBus, TelemetryMessage


def main() -> None:
    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    bus = MetricBus()
    flaky_counter = {"count": 0}
    flaky_every_n = 10

    def printer(message: TelemetryMessage) -> None:
        print(
            f"frame={message.frame} sim_time_s={message.sim_time_s:.3f} payload={message.payload}"
        )

    def flaky(message: TelemetryMessage) -> None:
        flaky_counter["count"] += 1
        if flaky_counter["count"] % flaky_every_n == 0:
            raise RuntimeError(
                f"intentional flaky failure at count={flaky_counter['count']} frame={message.frame}"
            )

    bus.subscribe("metric.heartbeat", printer)
    bus.subscribe("metric.heartbeat", flaky)

    start = time.monotonic()
    ticks = 0
    max_ticks = 200
    max_seconds = 5.0

    try:
        while ticks < max_ticks and (time.monotonic() - start) < max_seconds:
            world.wait_for_tick(1.0)
            snapshot = world.get_snapshot()
            bus.publish(
                TelemetryMessage(
                    topic="metric.heartbeat",
                    run_id="smoke",
                    frame=snapshot.frame,
                    sim_time_s=snapshot.timestamp.elapsed_seconds,
                    payload={"status": "ok"},
                )
            )
            ticks += 1
    finally:
        bus.close(drain=True)
        print(f"MetricBus smoke run complete: ticks={ticks}, flaky_calls={flaky_counter['count']}")


if __name__ == "__main__":
    main()
