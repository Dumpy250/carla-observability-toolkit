import pathlib
import sys
import threading
import time
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.core.metric_bus import MetricBus, TelemetryMessage


class TestMetricBusSmoke(unittest.TestCase):
    def test_subscriber_exception_isolated_and_worker_continues(self) -> None:
        bus = MetricBus()
        handled = []
        event = threading.Event()
        lock = threading.Lock()

        def bad_handler(message: TelemetryMessage) -> None:
            raise RuntimeError(f"boom {message.topic}")

        def good_handler(message: TelemetryMessage) -> None:
            with lock:
                handled.append(message.payload["value"])
                if len(handled) >= 2:
                    event.set()

        bus.subscribe("telemetry/vehicle", bad_handler)
        bus.subscribe("telemetry/vehicle", good_handler)
        bus.publish(TelemetryMessage(topic="telemetry/vehicle/speed", run_id="run-1", frame=1, sim_time_s=0.1, payload={"value": 1}))
        bus.publish(TelemetryMessage(topic="telemetry/vehicle/speed", run_id="run-1", frame=2, sim_time_s=0.2, payload={"value": 2}))
        self.assertTrue(event.wait(timeout=2.0), "Expected healthy subscriber to receive both messages")

        with lock:
            self.assertEqual([1, 2], handled)
        bus.close(drain=True)
        self.assertFalse(bus._worker.is_alive())

    def test_close_drain_true_processes_queued_messages(self) -> None:
        bus = MetricBus()
        count = 0
        lock = threading.Lock()
        total = 30

        def handler(message: TelemetryMessage) -> None:
            nonlocal count
            with lock:
                count += 1

        bus.subscribe("telemetry/", handler)
        for i in range(total):
            bus.publish(TelemetryMessage(topic="telemetry/item", run_id="run-1", frame=i, sim_time_s=float(i), payload={"value": i}))
        bus.close(drain=True)

        with lock:
            self.assertEqual(total, count)
        self.assertFalse(bus._worker.is_alive())

        with self.assertRaises(RuntimeError):
            bus.subscribe("telemetry/", handler)
        with self.assertRaises(RuntimeError):
            bus.publish(
                TelemetryMessage(
                    topic="telemetry/vehicle/speed",
                    run_id="run-1",
                    frame=999,
                    sim_time_s=999.0,
                    payload={"value": 999},
                )
            )

    def test_close_drain_false_stops_without_draining(self) -> None:
        bus = MetricBus()
        count = 0
        lock = threading.Lock()
        total = 40

        def handler(message: TelemetryMessage) -> None:
            nonlocal count
            time.sleep(0.05)
            with lock:
                count += 1

        bus.subscribe("telemetry/", handler)
        for i in range(total):
            bus.publish(TelemetryMessage(topic="telemetry/item", run_id="run-1", frame=i, sim_time_s=float(i), payload={"value": i}))

        start = time.monotonic()
        bus.close(drain=False)
        elapsed = time.monotonic() - start

        self.assertLess(elapsed, 0.8, "close(drain=False) should return quickly and not drain the queue")
        with lock:
            self.assertLess(count, total)
        self.assertFalse(bus._worker.is_alive())


if __name__ == "__main__":
    unittest.main()
