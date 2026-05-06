from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from math import sqrt
from threading import Lock
from time import monotonic
from typing import Optional

from cot.bus.metric_bus import TelemetryMessage

SPEED_WARNING_THRESHOLD_KMH = 80.0
MAX_ACTIVE_ALERTS = 3
DEFAULT_ALERT_DURATION_S = 1.8
MIN_ALERT_DURATION_S = 0.1
HIGH_SPEED_ALERT_DURATION_S = 0.5
LANE_INVASION_ALERT_DURATION_S = 1.5
RECENT_EVENT_LIMIT = 3


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
                    duration_s=HIGH_SPEED_ALERT_DURATION_S,
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
            self._push_event_line_locked(event_line)
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
                    duration_s=LANE_INVASION_ALERT_DURATION_S,
                )

    def push_manual_event(self, text: str, alert_text: Optional[str] = None) -> None:
        with self._lock:
            self._push_event_line_locked(text)
            if alert_text:
                self._upsert_alert_locked(
                    key="manual_event",
                    text=alert_text,
                    color=(86, 214, 128),
                    duration_s=DEFAULT_ALERT_DURATION_S,
                )

    def _push_event_line_locked(self, event_line: str) -> None:
        self.events.insert(0, event_line)
        if len(self.events) > RECENT_EVENT_LIMIT:
            self.events = self.events[:RECENT_EVENT_LIMIT]

    def _upsert_alert_locked(
        self,
        key: str,
        text: str,
        color: tuple[int, int, int],
        duration_s: float,
    ) -> None:
        now = monotonic()
        expires_at = now + max(MIN_ALERT_DURATION_S, duration_s)
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
