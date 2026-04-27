from __future__ import annotations

import pathlib
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from math import sqrt
from threading import Event, Lock, Thread
from time import monotonic
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

SPEED_WARNING_THRESHOLD_KMH = 80.0
MAX_ACTIVE_ALERTS = 3
DEFAULT_ALERT_DURATION_S = 1.8


@dataclass
class DashboardAlert:
    key: str
    text: str
    color: tuple[int, int, int]
    expires_at: float


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
    high_speed_warning: bool = False
    events: list[str] = field(default_factory=list)
    alerts: list[DashboardAlert] = field(default_factory=list)
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
                self.high_speed_warning = False
                self.alerts = []

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
            self.high_speed_warning = self.speed_kmh >= SPEED_WARNING_THRESHOLD_KMH
            if self.high_speed_warning:
                self._upsert_alert_locked(
                    key="high_speed",
                    text="HIGH SPEED",
                    color=(255, 176, 64),
                    duration_s=0.5,
                )
            else:
                self._remove_alert_locked("high_speed")

    def push_event(self, message: TelemetryMessage) -> None:
        payload = message.payload if isinstance(message.payload, dict) else {}
        event_type = payload.get("type")
        if not isinstance(event_type, str) or not event_type:
            event_type = message.topic.split(".")[-1]
        frame_value = payload.get("frame")
        if frame_value is None:
            frame_value = message.frame
        event_line = f"{event_type} @ {frame_value if frame_value is not None else '?'}"

        with self._lock:
            self.events.insert(0, event_line)
            if len(self.events) > 3:
                self.events = self.events[:3]
            if event_type == "collision":
                self._upsert_alert_locked(
                    key="collision",
                    text="COLLISION DETECTED",
                    color=(235, 98, 98),
                    duration_s=DEFAULT_ALERT_DURATION_S,
                )
            elif event_type == "lane_invasion":
                self._upsert_alert_locked(
                    key="lane_invasion",
                    text="LANE INVASION",
                    color=(230, 193, 107),
                    duration_s=1.5,
                )

    def _upsert_alert_locked(
        self,
        key: str,
        text: str,
        color: tuple[int, int, int],
        duration_s: float,
    ) -> None:
        now = monotonic()
        expires_at = now + max(0.1, duration_s)
        self.alerts = [alert for alert in self.alerts if alert.expires_at > now]
        for alert in self.alerts:
            if alert.key == key:
                alert.text = text
                alert.color = color
                alert.expires_at = expires_at
                self.alerts.sort(key=lambda existing: existing.expires_at, reverse=True)
                return
        self.alerts.insert(0, DashboardAlert(key=key, text=text, color=color, expires_at=expires_at))
        self.alerts = self.alerts[:MAX_ACTIVE_ALERTS]

    def _remove_alert_locked(self, key: str) -> None:
        self.alerts = [alert for alert in self.alerts if alert.key != key]

    def snapshot(
        self,
    ) -> tuple[str, str, str, str, str, str, float, float, float, bool, list[str], list[DashboardAlert]]:
        with self._lock:
            now = monotonic()
            self.alerts = [alert for alert in self.alerts if alert.expires_at > now]
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
                self.high_speed_warning,
                list(self.events),
                [DashboardAlert(alert.key, alert.text, alert.color, alert.expires_at) for alert in self.alerts],
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


def _truncate_middle(value: str, keep: int = 8) -> str:
    if len(value) <= keep * 2 + 3:
        return value
    return f"{value[:keep]}...{value[-keep:]}"


def _draw_panel(screen: pygame.Surface, rect: pygame.Rect, border_color: tuple[int, int, int]) -> None:
    pygame.draw.rect(screen, (27, 33, 44), rect, border_radius=8)
    pygame.draw.rect(screen, border_color, rect, width=1, border_radius=8)


def _draw_kv_rows(
    screen: pygame.Surface,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    rect: pygame.Rect,
    rows: list[tuple[str, str]],
    label_color: tuple[int, int, int] = (150, 164, 186),
    value_color: tuple[int, int, int] = (228, 233, 241),
    row_height: int = 22,
) -> None:
    label_x = rect.left
    value_x = rect.left + 172
    y = rect.top
    for label, value in rows:
        label_surface = label_font.render(label, True, label_color)
        value_surface = value_font.render(value, True, value_color)
        screen.blit(label_surface, (label_x, y))
        screen.blit(value_surface, (value_x, y))
        y += row_height


def _draw_alerts(
    screen: pygame.Surface,
    alert_font: pygame.font.Font,
    alerts: list[DashboardAlert],
) -> None:
    if not alerts:
        return
    now = monotonic()
    banner_y = 46
    banner_height = 20
    max_visible = min(len(alerts), 2)
    for index in range(max_visible):
        alert = alerts[index]
        remaining = max(0.0, alert.expires_at - now)
        alpha_ratio = min(1.0, remaining / DEFAULT_ALERT_DURATION_S)
        alpha = int(60 + 150 * alpha_ratio)
        text_surface = alert_font.render(alert.text, True, alert.color)
        banner_width = min(screen.get_width() - 24, text_surface.get_width() + 20)
        banner_x = (screen.get_width() - banner_width) // 2
        y = banner_y + index * (banner_height + 4)
        banner_surface = pygame.Surface((banner_width, banner_height), pygame.SRCALPHA)
        border_surface = pygame.Surface((banner_width, banner_height), pygame.SRCALPHA)
        banner_surface.fill((24, 30, 40, alpha))
        border_surface.fill((0, 0, 0, 0))
        pygame.draw.rect(border_surface, (*alert.color, min(220, alpha + 40)), border_surface.get_rect(), width=1, border_radius=5)
        screen.blit(banner_surface, (banner_x, y))
        screen.blit(border_surface, (banner_x, y))
        text_x = banner_x + max(10, (banner_width - text_surface.get_width()) // 2)
        screen.blit(text_surface, (text_x, y + 2))


def _render(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    section_font: pygame.font.Font,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    metric_font: pygame.font.Font,
    speed_metric_font: pygame.font.Font,
    dashboard: DashboardState,
) -> None:
    screen.fill((19, 24, 32))
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
        high_speed_warning,
        events,
        alerts,
    ) = dashboard.snapshot()

    status_color = (86, 214, 128) if status == "RUNNING" else (235, 98, 98) if status == "STOPPED" else (229, 233, 240)
    short_run_id = _truncate_middle(run_id) if run_id != "-" else run_id
    title_surface = title_font.render("CARLA Observability Toolkit", True, (228, 233, 241))
    subtitle_surface = label_font.render("Client Telemetry Dashboard", True, (150, 164, 186))
    screen.blit(title_surface, (14, 10))
    screen.blit(subtitle_surface, (14, 34))

    panel_width = screen.get_width() - 24
    run_panel = pygame.Rect(12, 70, panel_width, 156)
    metrics_panel = pygame.Rect(12, 244, panel_width, 94)
    events_panel = pygame.Rect(12, 356, panel_width, 98)
    _draw_panel(screen, run_panel, (49, 61, 79))
    _draw_panel(screen, metrics_panel, (49, 61, 79))
    _draw_panel(screen, events_panel, (49, 61, 79))

    section_color = (174, 188, 211)
    run_title = section_font.render("RUN INFO", True, section_color)
    metrics_title = section_font.render("VEHICLE METRICS", True, section_color)
    events_title = section_font.render("EVENTS", True, section_color)
    screen.blit(run_title, (run_panel.left + 12, run_panel.top + 10))
    screen.blit(metrics_title, (metrics_panel.left + 12, metrics_panel.top + 10))
    screen.blit(events_title, (events_panel.left + 12, events_panel.top + 10))

    status_label = label_font.render("Run Status", True, (150, 164, 186))
    status_value = section_font.render(status, True, status_color)
    screen.blit(status_label, (run_panel.left + 12, run_panel.top + 38))
    screen.blit(status_value, (run_panel.left + 172, run_panel.top + 36))
    _draw_kv_rows(
        screen,
        label_font,
        value_font,
        pygame.Rect(run_panel.left + 12, run_panel.top + 64, run_panel.width - 24, 84),
        [
            ("Run ID", short_run_id),
            ("Experiment", experiment_id),
            ("Config", config_name),
            ("Scenario", scenario_label),
            ("Seed", seed),
        ],
        row_height=19,
    )

    metric_y = metrics_panel.top + 38
    speed_label = label_font.render("Speed", True, (150, 164, 186))
    accel_label = label_font.render("Acceleration (|a|)", True, (150, 164, 186))
    steer_label = label_font.render("Steering", True, (150, 164, 186))
    speed_value_color = (255, 182, 74) if high_speed_warning else (236, 242, 252)
    speed_value = speed_metric_font.render(f"{speed_kmh:.1f} km/h", True, speed_value_color)
    accel_value = metric_font.render(f"{accel_mag:.2f} m/s^2", True, (228, 233, 241))
    steer_value = metric_font.render(f"{steering:.3f}", True, (228, 233, 241))

    speed_x = metrics_panel.left + 12
    accel_x = metrics_panel.left + metrics_panel.width // 3 + 8
    steer_x = metrics_panel.left + (2 * metrics_panel.width) // 3 + 8
    screen.blit(speed_label, (speed_x, metric_y))
    screen.blit(accel_label, (accel_x, metric_y))
    screen.blit(steer_label, (steer_x, metric_y))
    screen.blit(speed_value, (speed_x, metric_y + 14))
    screen.blit(accel_value, (accel_x, metric_y + 16))
    screen.blit(steer_value, (steer_x, metric_y + 16))

    event_start_x = events_panel.left + 12
    event_start_y = events_panel.top + 34
    event_lines = events[:3] if events else ["(none)"]

    for index, event_line in enumerate(event_lines):
        event_surface = value_font.render(event_line, True, (211, 219, 233))
        screen.blit(event_surface, (event_start_x, event_start_y + index * 20))
    _draw_alerts(screen, value_font, alerts)
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
    screen = pygame.display.set_mode((620, 470))
    title_font = pygame.font.Font(None, 28)
    section_font = pygame.font.Font(None, 24)
    label_font = pygame.font.Font(None, 20)
    value_font = pygame.font.Font(None, 21)
    metric_font = pygame.font.Font(None, 26)
    speed_metric_font = pygame.font.Font(None, 30)
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
            _render(
                screen,
                title_font,
                section_font,
                label_font,
                value_font,
                metric_font,
                speed_metric_font,
                dashboard,
            )
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
