from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RunMetricRow:
    """Typed representation of one row from metrics.csv."""

    frame: int | None
    sim_time_s: float | None
    speed_mps: float | None
    acceleration_x: float | None
    acceleration_y: float | None
    acceleration_z: float | None
    steering: float | None
    throttle: float | None
    brake: float | None
    position_x: float | None
    position_y: float | None
    position_z: float | None
    heading: float | None


@dataclass(slots=True)
class RunEvent:
    """Typed run event with normalized frame/time fields and raw payload."""

    run_id: str | None
    frame: int | None
    event_type: str | None
    sim_time_s: float | None
    payload: dict[str, Any]


@dataclass(slots=True)
class LoadedRunData:
    """Loaded run artifact bundle for one run directory."""

    run_dir: Path
    metadata: dict[str, Any]
    metrics: list[RunMetricRow]
    events: list[RunEvent]


def _none_if_blank(value: Any) -> Any:
    """Return None for blank-ish values, otherwise return the original value."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _parse_int(value: Any) -> int | None:
    """Parse an integer safely; blank or invalid values become None."""
    normalized = _none_if_blank(value)
    if normalized is None:
        return None
    if isinstance(normalized, bool):
        return int(normalized)
    if isinstance(normalized, int):
        return normalized
    if isinstance(normalized, float):
        if normalized.is_integer():
            return int(normalized)
        return None
    if isinstance(normalized, str):
        text = normalized.strip()
        try:
            return int(text)
        except ValueError:
            try:
                float_value = float(text)
            except ValueError:
                return None
            if float_value.is_integer():
                return int(float_value)
            return None
    return None


def _parse_float(value: Any) -> float | None:
    """Parse a float safely; blank or invalid values become None."""
    normalized = _none_if_blank(value)
    if normalized is None:
        return None
    if isinstance(normalized, bool):
        return float(normalized)
    if isinstance(normalized, (int, float)):
        return float(normalized)
    if isinstance(normalized, str):
        text = normalized.strip()
        try:
            return float(text)
        except ValueError:
            return None
    return None


class RunDataLoader:
    """Load persisted run artifacts into typed in-memory structures."""

    def __init__(self, runs_root: str | Path | None = None) -> None:
        self.runs_root = Path(runs_root) if runs_root is not None else None

    def load_run(self, run_dir: str | Path) -> LoadedRunData:
        """
        Load one run directory.

        metadata.json is required. metrics.csv and events.json are optional.
        """
        candidate = Path(run_dir)
        resolved_run_dir = candidate if candidate.is_absolute() else (
            self.runs_root / candidate if self.runs_root is not None else candidate
        )

        metadata = self._load_metadata(resolved_run_dir / "metadata.json")
        metrics = self._load_metrics(resolved_run_dir / "metrics.csv")
        events = self._load_events(resolved_run_dir / "events.json")

        return LoadedRunData(
            run_dir=resolved_run_dir,
            metadata=metadata,
            metrics=metrics,
            events=events,
        )

    def _load_metadata(self, path: Path) -> dict[str, Any]:
        """Load metadata.json and return it as a dictionary."""
        if not path.exists():
            raise FileNotFoundError(f"Required metadata file not found: {path}")

        with path.open("r", encoding="utf-8") as file_obj:
            loaded = json.load(file_obj)

        if not isinstance(loaded, dict):
            raise ValueError(f"metadata.json must contain a JSON object: {path}")
        return loaded

    def _load_metrics(self, path: Path) -> list[RunMetricRow]:
        """Load metrics.csv into typed metric rows."""
        if not path.exists():
            return []

        rows: list[RunMetricRow] = []
        with path.open("r", newline="", encoding="utf-8") as file_obj:
            reader = csv.DictReader(file_obj)
            for row in reader:
                rows.append(
                    RunMetricRow(
                        frame=_parse_int(row.get("frame")),
                        sim_time_s=_parse_float(row.get("sim_time_s")),
                        speed_mps=_parse_float(row.get("speed_mps")),
                        acceleration_x=_parse_float(row.get("acceleration_x")),
                        acceleration_y=_parse_float(row.get("acceleration_y")),
                        acceleration_z=_parse_float(row.get("acceleration_z")),
                        steering=_parse_float(row.get("steering")),
                        throttle=_parse_float(row.get("throttle")),
                        brake=_parse_float(row.get("brake")),
                        position_x=_parse_float(row.get("position_x")),
                        position_y=_parse_float(row.get("position_y")),
                        position_z=_parse_float(row.get("position_z")),
                        heading=_parse_float(row.get("heading")),
                    )
                )
        return rows

    def _load_events(self, path: Path) -> list[RunEvent]:
        """Load events.json as a list of typed RunEvent objects."""
        if not path.exists():
            return []

        with path.open("r", encoding="utf-8") as file_obj:
            loaded = json.load(file_obj)

        if not isinstance(loaded, list):
            raise ValueError(f"events.json must contain a JSON array: {path}")

        events: list[RunEvent] = []
        for index, raw_event in enumerate(loaded):
            if not isinstance(raw_event, dict):
                raise ValueError(
                    f"events.json item at index {index} must be a JSON object: {path}"
                )
            events.append(
                RunEvent(
                    run_id=raw_event.get("run_id")
                    if isinstance(raw_event.get("run_id"), str)
                    else None,
                    frame=_parse_int(raw_event.get("frame")),
                    event_type=raw_event.get("type")
                    if isinstance(raw_event.get("type"), str)
                    else None,
                    sim_time_s=_parse_float(raw_event.get("sim_time_s")),
                    payload=dict(raw_event),
                )
            )
        return events

