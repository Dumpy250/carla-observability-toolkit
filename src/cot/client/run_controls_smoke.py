from __future__ import annotations

import pathlib
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from math import sqrt
from threading import Event, Lock, Thread
from typing import Optional

import pygame

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.carla_client import make_client
from cot.core.event_collector import EventCollector
from cot.core.logger import RunLogger
from cot.core.metric_bus import MetricBus
from cot.core.metric_bus import TelemetryMessage
from cot.core.experiment_config import load_experiment_config
from cot.core.run_manager import RunManager
from cot.core.vehicle_metrics_collector import VehicleMetricsCollector


@dataclass
class DashboardState:
    status: str = "STOPPED"
    run_id: str = "-"
    experiment_id: str = "-"
    config_name: str = "-"
    scenario_label: str = "-"
    seed: str = "-"
    speed_kmh: float = 0.0
    acceleration_magnitude: float = 0.0
    steering: float = 0.0
    events: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def set_run(self, status: str, run_id: Optional[str]) -> None:
        with self._lock:
            self.status = status.upper()
            self.run_id = run_id or "-"
            if self.status != "RUNNING":
                self.experiment_id = "-"
                self.config_name = "-"
                self.scenario_label = "-"
                self.seed = "-"
                self.speed_kmh = 0.0
                self.acceleration_magnitude = 0.0
                self.steering = 0.0

    def set_experiment_metadata(
        self,
        experiment_id: Optional[str],
        config_name: Optional[str],
        scenario_label: Optional[str],
        seed: Optional[int],
    ) -> None:
        with self._lock:
            self.experiment_id = experiment_id if experiment_id else "-"
            self.config_name = config_name if config_name else "-"
            self.scenario_label = scenario_label if scenario_label else "-"
            self.seed = str(seed) if seed is not None else "-"

    def update_vehicle(self, message: TelemetryMessage) -> None:
        payload = message.payload if isinstance(message.payload, dict) else {}
        speed_mps = _as_float(payload.get("speed_mps"))
        acceleration = payload.get("acceleration")
        if not isinstance(acceleration, dict):
            acceleration = {}
        ax = _as_float(acceleration.get("x"))
        ay = _as_float(acceleration.get("y"))
        az = _as_float(acceleration.get("z"))
        steering = _as_float(payload.get("steering"))

        with self._lock:
            self.speed_kmh = speed_mps * 3.6
            self.acceleration_magnitude = sqrt(ax * ax + ay * ay + az * az)
            self.steering = steering

    def push_event(self, message: TelemetryMessage) -> None:
        payload = message.payload if isinstance(message.payload, dict) else {}
        event_type = payload.get("type")
        if not isinstance(event_type, str) or not event_type:
            event_type = message.topic.split(".")[-1]
        frame_value = payload.get("frame")
        if frame_value is None:
            frame_value = message.frame
        event_line = f"{event_type} frame={frame_value if frame_value is not None else '?'}"

        with self._lock:
            self.events.insert(0, event_line)
            if len(self.events) > 3:
                self.events = self.events[:3]

    def snapshot(self) -> tuple[str, str, str, str, str, str, float, float, float, list[str]]:
        with self._lock:
            return (
                self.status,
                self.run_id,
                self.experiment_id,
                self.config_name,
                self.scenario_label,
                self.seed,
                self.speed_kmh,
                self.acceleration_magnitude,
                self.steering,
                list(self.events),
            )


def _as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pick_vehicle(world):
    vehicles = world.get_actors().filter("vehicle.*")
    if not vehicles:
        return None

    for vehicle in vehicles:
        if vehicle.attributes.get("role_name") == "hero":
            return vehicle
    return vehicles[0]


def _parse_key_value(user_input: str) -> tuple[str, str] | None:
    if "=" not in user_input:
        return None
    key, value = user_input.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return key, value


def _render(screen: pygame.Surface, font: pygame.font.Font, dashboard: DashboardState) -> None:
    screen.fill((0, 0, 0))
    (
        status,
        run_id,
        experiment_id,
        config_name,
        scenario_label,
        seed,
        speed_kmh,
        accel_mag,
        steering,
        events,
    ) = dashboard.snapshot()
    lines = [
        f"Run: {status}  id={run_id}",
        f"Experiment: {experiment_id}",
        f"Config: {config_name}",
        f"Scenario: {scenario_label}",
        f"Seed: {seed}",
        f"Speed: {speed_kmh:.1f} km/h",
        f"Accel |a|: {accel_mag:.2f} m/s^2",
        f"Steering: {steering:.3f}",
        "Events (latest 3):",
    ]
    lines.extend([f"  - {evt}" for evt in events] or ["  - (none)"])

    y = 12
    for line in lines:
        text = font.render(line, True, (220, 220, 220))
        screen.blit(text, (10, y))
        y += 24
    pygame.display.flip()


def _apply_config_weather(world, config) -> None:
    weather_config = getattr(config, "weather", None)
    if weather_config is None:
        return

    weather = world.get_weather()
    for key, value in weather_config.to_dict().items():
        if hasattr(weather, key):
            setattr(weather, key, value)
    world.set_weather(weather)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("CARLA Run Controls")
    screen = pygame.display.set_mode((560, 320))
    font = pygame.font.Font(None, 20)
    clock = pygame.time.Clock()

    client = make_client()
    world = client.get_world()
    vehicle = _pick_vehicle(world)
    if vehicle is None:
        raise RuntimeError("No vehicle actors found in the CARLA world.")

    runs_root = PROJECT_ROOT / "runs"
    experiment_config_path = PROJECT_ROOT / "configs" / "experiment_v1.json"
    run_manager = RunManager()
    metric_bus: MetricBus | None = None
    logger: RunLogger | None = None
    vehicle_collector: VehicleMetricsCollector | None = None
    event_collector: EventCollector | None = None
    collector_thread: Thread | None = None
    collector_stop = Event()
    dashboard = DashboardState()

    def stop_collectors() -> None:
        nonlocal vehicle_collector, event_collector, collector_thread
        collector_stop.set()
        if collector_thread is not None:
            collector_thread.join(timeout=2.0)
            collector_thread = None
        vehicle_collector = None
        if event_collector is not None and hasattr(event_collector, "close"):
            event_collector.close()
        event_collector = None

    def tick_vehicle_metrics() -> None:
        while not collector_stop.is_set():
            try:
                snapshot = world.wait_for_tick(0.25)
            except Exception:
                continue
            if snapshot is None or vehicle_collector is None:
                continue
            try:
                vehicle_collector.tick(snapshot)
            except Exception:
                continue

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type != pygame.KEYDOWN:
                    continue

                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F5:
                    if run_manager.is_running():
                        continue
                    try:
                        config = load_experiment_config(experiment_config_path)
                    except Exception as exc:
                        print(
                            f"RUN start failed: unable to load experiment config "
                            f"from {experiment_config_path}: {exc}"
                        )
                        continue

                    try:
                        _apply_config_weather(world, config)
                    except Exception as exc:
                        try:
                            run_manager.abort_run(
                                reason=f"weather_apply_failed:{type(exc).__name__}"
                            )
                        except Exception:
                            pass
                        print(f"RUN start failed: unable to apply weather from config: {exc}")
                        continue
                    state = run_manager.start_run(world, vehicle, experiment_config=config)

                    metric_bus = MetricBus()
                    metric_bus.subscribe("metric.vehicle.state", dashboard.update_vehicle)
                    metric_bus.subscribe("metric.event.", dashboard.push_event)
                    logger = RunLogger(metric_bus, run_id=state.run_id, output_root=runs_root)

                    frame = None
                    sim_time_s = None
                    try:
                        snapshot = world.get_snapshot()
                        if snapshot is not None:
                            frame = getattr(snapshot, "frame", None)
                            timestamp = getattr(snapshot, "timestamp", None)
                            if timestamp is not None:
                                sim_time_s = getattr(timestamp, "elapsed_seconds", None)
                    except Exception:
                        pass

                    payload = {
                        "run_id": state.run_id,
                        "type": "run_started",
                        "source": "user",
                        "trigger": "experiment_config",
                    }
                    if frame is not None:
                        payload["frame"] = frame
                    if sim_time_s is not None:
                        payload["sim_time_s"] = sim_time_s
                    metric_bus.publish(
                        TelemetryMessage(
                            topic="metric.event.run_started",
                            run_id=state.run_id,
                            frame=frame,
                            sim_time_s=sim_time_s,
                            payload=payload,
                        )
                    )

                    collector_stop.clear()
                    vehicle_collector = VehicleMetricsCollector(metric_bus, world, run_id=state.run_id)
                    event_collector = EventCollector(world, vehicle, metric_bus, run_id=state.run_id)
                    collector_thread = Thread(target=tick_vehicle_metrics, daemon=True)
                    collector_thread.start()
                    dashboard.set_run(state.status, state.run_id)

                    tags_payload = getattr(config, "tags", {})
                    if not isinstance(tags_payload, dict):
                        tags_payload = {}
                    dashboard.set_experiment_metadata(
                        getattr(config, "experiment_id", None),
                        getattr(config, "config_name", None),
                        tags_payload.get("scenario"),
                        getattr(config, "seed", None),
                    )

                    logger.update_metadata(asdict(state))
                    weather_payload = None
                    if getattr(config, "weather", None) is not None:
                        weather_value = getattr(config, "weather")
                        if hasattr(weather_value, "to_dict"):
                            weather_payload = weather_value.to_dict()
                        elif isinstance(weather_value, dict):
                            weather_payload = dict(weather_value)

                    logger.update_metadata(
                        {
                            "experiment": {
                                "experiment_id": getattr(config, "experiment_id", None),
                                "config_name": getattr(config, "config_name", None),
                                "seed": getattr(config, "seed", None),
                                "duration_s": getattr(config, "duration_s", None),
                                "tags": dict(tags_payload),
                                "weather": weather_payload,
                                "config_path": str(experiment_config_path),
                            }
                        }
                    )
                    print(f"RUN started id={state.run_id}")
                elif event.key == pygame.K_F6:
                    if not run_manager.is_running():
                        continue
                    state = run_manager.stop_run()
                    dashboard.set_run(state.status, state.run_id)
                    stop_collectors()
                    if logger is not None:
                        logger.update_metadata(asdict(state))
                        logger.close()
                        logger = None
                    if metric_bus is not None:
                        metric_bus.close(drain=True)
                        metric_bus = None
                    print(f"RUN stopped id={state.run_id}")
                elif event.key == pygame.K_F7:
                    if not run_manager.is_running():
                        continue
                    state = run_manager.abort_run(reason="keyboard_abort")
                    dashboard.set_run(state.status, state.run_id)
                    stop_collectors()
                    if logger is not None:
                        logger.update_metadata(asdict(state))
                        logger.close()
                        logger = None
                    if metric_bus is not None:
                        metric_bus.close(drain=True)
                        metric_bus = None
                    print(f"RUN aborted id={state.run_id} reason={state.abort_reason}")
                elif event.key == pygame.K_F8:
                    user_input = input("Enter tag key=value: ")
                    parsed = _parse_key_value(user_input)
                    if parsed is None:
                        continue
                    key, value = parsed
                    state = run_manager.tag(key, value)
                    if logger is not None:
                        logger.update_metadata(asdict(state))
                    print(f"TAG {key}={value}")
            _render(screen, font, dashboard)
            clock.tick(30)
    finally:
        if run_manager.is_running():
            state = run_manager.stop_run()
            dashboard.set_run(state.status, state.run_id)
            if logger is not None:
                logger.update_metadata(asdict(state))

        stop_collectors()
        if logger is not None:
            logger.close()
        if metric_bus is not None:
            metric_bus.close(drain=True)
        pygame.quit()


if __name__ == "__main__":
    main()
