from __future__ import annotations

from threading import Event, Thread

from cot.bus.metric_bus import MetricBus
from cot.collectors.event_collector import EventCollector
from cot.collectors.vehicle_metrics_collector import VehicleMetricsCollector

COLLECTOR_WAIT_FOR_TICK_TIMEOUT_S = 0.25
COLLECTOR_JOIN_TIMEOUT_S = 2.0


class CollectorSession:
    def __init__(
        self,
        metric_bus: MetricBus,
        world,
        vehicle,
        run_id: str,
        tick_timeout_s: float = COLLECTOR_WAIT_FOR_TICK_TIMEOUT_S,
        join_timeout_s: float = COLLECTOR_JOIN_TIMEOUT_S,
    ) -> None:
        self._metric_bus = metric_bus
        self._world = world
        self._vehicle = vehicle
        self._run_id = run_id
        self._tick_timeout_s = tick_timeout_s
        self._join_timeout_s = join_timeout_s

        self._stop_event = Event()
        self._collector_thread: Thread | None = None
        self._vehicle_collector: VehicleMetricsCollector | None = None
        self._event_collector: EventCollector | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._vehicle_collector = VehicleMetricsCollector(self._metric_bus, self._world, run_id=self._run_id)
        self._event_collector = EventCollector(self._world, self._vehicle, self._metric_bus, run_id=self._run_id)
        self._collector_thread = Thread(target=self._tick_loop, daemon=True)
        self._collector_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._collector_thread is not None:
            self._collector_thread.join(timeout=self._join_timeout_s)
            self._collector_thread = None

        self._vehicle_collector = None
        if self._event_collector is not None and hasattr(self._event_collector, "close"):
            self._event_collector.close()
        self._event_collector = None

    def _tick_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                snapshot = self._world.wait_for_tick(self._tick_timeout_s)
            except Exception:
                continue
            if snapshot is None or self._vehicle_collector is None:
                continue
            try:
                self._vehicle_collector.tick(snapshot)
            except Exception:
                continue
