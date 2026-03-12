from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .metric_bus import MetricBus, Subscription, TelemetryMessage


class RunLogger:
    """Persists telemetry from MetricBus into run-scoped files."""

    def __init__(
        self,
        metric_bus: MetricBus,
        run_id: str,
        output_root: Optional[str | Path] = None,
        run_metadata: Optional[dict] = None,
    ) -> None:
        self.metric_bus = metric_bus
        self.run_id = run_id
        repo_root = next(
            (
                parent
                for parent in Path(__file__).resolve().parents
                if (parent / "README.md").exists() and (parent / "src").is_dir()
            ),
            Path(__file__).resolve().parents[3],
        )
        runs_root = repo_root / "runs"
        self.output_root = Path(output_root) if output_root is not None else runs_root
        self.start_time_utc = datetime.now(timezone.utc)
        self.run_metadata = run_metadata

        timestamp = self.start_time_utc.strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = self.output_root / f"{run_id}_{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_csv_path = self.run_dir / "metrics.csv"
        self.events_json_path = self.run_dir / "events.json"
        self.metadata_json_path = self.run_dir / "metadata.json"

        self._events: list[dict[str, Any]] = []
        self._closed = False
        self._metadata: dict[str, Any] = {
            "run_id": self.run_id,
            "started_at_utc": self.start_time_utc.isoformat(),
            "ended_at_utc": None,
            "status": "running",
            "abort_reason": None,
            "tags": {},
            "map_name": None,
            "vehicle_blueprint": None,
        }
        if self.run_metadata:
            self._metadata.update(self.run_metadata)

        self._metrics_file = self.metrics_csv_path.open("w", newline="", encoding="utf-8")
        self._metrics_writer = csv.DictWriter(
            self._metrics_file,
            fieldnames=[
                "frame",
                "sim_time_s",
                "speed_mps",
                "acceleration_x",
                "acceleration_y",
                "acceleration_z",
                "steering",
                "throttle",
                "brake",
                "position_x",
                "position_y",
                "position_z",
                "heading",
            ],
        )
        self._metrics_writer.writeheader()
        self._metrics_file.flush()

        self._write_metadata()

        self._subscriptions: list[Subscription] = [
            self.metric_bus.subscribe("metric.vehicle.state", self._on_metric_vehicle_state),
            self.metric_bus.subscribe("metric.event.collision", self._on_metric_event),
            self.metric_bus.subscribe("metric.event.lane_invasion", self._on_metric_event),
            self.metric_bus.subscribe("metric.event.run_started", self._on_metric_event),
        ]

    def _fmt(self, v):
        if v is None:
            return None
        value = float(v)
        if abs(value) < 1e-4:
            return 0.0
        return round(value, 6)

    def _write_metadata(self) -> None:
        self.metadata_json_path.write_text(json.dumps(self._metadata, indent=2), encoding="utf-8")

    def update_metadata(self, extra: dict[str, Any]) -> None:
        self._metadata.update(extra)
        self._write_metadata()

    def _on_metric_vehicle_state(self, message: TelemetryMessage) -> None:
        payload = message.payload or {}
        acceleration = payload.get("acceleration") or {}
        position = payload.get("position") or {}

        self._metrics_writer.writerow(
            {
                "frame": message.frame,
                "sim_time_s": self._fmt(message.sim_time_s),
                "speed_mps": self._fmt(payload.get("speed_mps")),
                "acceleration_x": self._fmt(acceleration.get("x")),
                "acceleration_y": self._fmt(acceleration.get("y")),
                "acceleration_z": self._fmt(acceleration.get("z")),
                "steering": self._fmt(payload.get("steering")),
                "throttle": self._fmt(payload.get("throttle")),
                "brake": self._fmt(payload.get("brake")),
                "position_x": self._fmt(position.get("x")),
                "position_y": self._fmt(position.get("y")),
                "position_z": self._fmt(position.get("z")),
                "heading": self._fmt(payload.get("heading")),
            }
        )
        self._metrics_file.flush()

    def _on_metric_event(self, message: TelemetryMessage) -> None:
        payload = message.payload or {}
        self._events.append(dict(payload))

    def close(self) -> None:
        """Flush output files and release resources."""
        if self._closed:
            return
        self._closed = True

        if hasattr(self.metric_bus, "unsubscribe"):
            for subscription in self._subscriptions:
                self.metric_bus.unsubscribe(subscription)
        self._subscriptions = []

        self._metrics_file.flush()
        self._write_metadata()
        self.events_json_path.write_text(json.dumps(self._events, indent=2), encoding="utf-8")
        self._metrics_file.close()
