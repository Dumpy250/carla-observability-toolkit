from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any

from cot.core.run_data_loader import RunDataLoader, RunMetricRow, _parse_float, _parse_int


EXPECTED_METRICS_HEADERS = [field.name for field in fields(RunMetricRow)]
REQUIRED_FILES = ("metadata.json", "metrics.csv", "events.json")
REQUIRED_METADATA_FIELDS = ("run_id", "started_at_utc", "status")
TERMINAL_RUN_STATUSES = {"stopped", "aborted"}
CSV_FIRST_DATA_ROW_INDEX = 2
METRICS_WALL_DURATION_MAX_LEAD_S = 5.0
WALL_DURATION_DRIFT_ABS_THRESHOLD_S = 15.0
WALL_DURATION_DRIFT_RATIO_THRESHOLD = 0.5


@dataclass(slots=True)
class _CheckResult:
    name: str
    passed: bool
    details: str
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or value.strip() == "":
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _record_check(
    checks: list[_CheckResult],
    errors: list[str],
    warnings: list[str],
    name: str,
    details: str,
    check_errors: list[str] | None = None,
    check_warnings: list[str] | None = None,
) -> None:
    local_errors = check_errors or []
    local_warnings = check_warnings or []
    checks.append(
        _CheckResult(
            name=name,
            passed=not local_errors,
            details=details,
            errors=local_errors,
            warnings=local_warnings,
        )
    )
    errors.extend(local_errors)
    warnings.extend(local_warnings)


def validate_run_directory(run_path: str | Path) -> dict[str, Any]:
    """
    Validate one run directory and return a structured integrity report.

    Returned object keys:
    - passed: bool
    - checks: list[dict]
    - errors: list[str]
    - warnings: list[str]
    - summary: dict[str, Any]
    """
    run_dir = Path(run_path).expanduser().resolve()
    checks: list[_CheckResult] = []
    errors: list[str] = []
    warnings: list[str] = []

    if not run_dir.exists() or not run_dir.is_dir():
        not_found_error = f"Run directory does not exist: {run_dir}"
        _record_check(
            checks=checks,
            errors=errors,
            warnings=warnings,
            name="run_directory_exists",
            details="Run directory must exist.",
            check_errors=[not_found_error],
        )
        return {
            "passed": False,
            "checks": [check.to_dict() for check in checks],
            "errors": errors,
            "warnings": warnings,
            "summary": {"run_dir": str(run_dir)},
        }

    required_file_errors: list[str] = []
    for filename in REQUIRED_FILES:
        if not (run_dir / filename).is_file():
            required_file_errors.append(f"Missing required file: {filename}")
    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="required_files_exist",
        details="Run directory contains metadata.json, metrics.csv, and events.json.",
        check_errors=required_file_errors,
    )

    metadata_path = run_dir / "metadata.json"
    metrics_path = run_dir / "metrics.csv"
    events_path = run_dir / "events.json"

    metadata_obj: dict[str, Any] | None = None
    metadata_parse_errors: list[str] = []
    metadata_warnings: list[str] = []
    if not metadata_path.is_file():
        metadata_parse_errors.append("metadata.json is missing.")
    else:
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                metadata_parse_errors.append("metadata.json must contain a JSON object.")
            else:
                metadata_obj = loaded
                missing_fields = [
                    key for key in REQUIRED_METADATA_FIELDS if key not in metadata_obj
                ]
                if missing_fields:
                    metadata_parse_errors.append(
                        f"metadata.json missing required fields: {', '.join(missing_fields)}"
                    )
                if "run_id" in metadata_obj and not isinstance(metadata_obj["run_id"], str):
                    metadata_parse_errors.append("metadata.run_id must be a string.")
                if "status" in metadata_obj and not isinstance(metadata_obj["status"], str):
                    metadata_parse_errors.append("metadata.status must be a string.")
                if "abort_reason" in metadata_obj and metadata_obj["abort_reason"] is not None:
                    if not isinstance(metadata_obj["abort_reason"], str):
                        metadata_parse_errors.append(
                            "metadata.abort_reason must be a string or null."
                        )
                if "tags" in metadata_obj and not isinstance(metadata_obj["tags"], dict):
                    metadata_parse_errors.append("metadata.tags must be an object.")
                if "map_name" in metadata_obj and not isinstance(metadata_obj["map_name"], str):
                    metadata_parse_errors.append("metadata.map_name must be a string.")
                if "vehicle_blueprint" in metadata_obj and not isinstance(
                    metadata_obj["vehicle_blueprint"], str
                ):
                    metadata_parse_errors.append("metadata.vehicle_blueprint must be a string.")

                started_at = _parse_iso_utc(metadata_obj.get("started_at_utc"))
                ended_at = _parse_iso_utc(metadata_obj.get("ended_at_utc"))
                if metadata_obj.get("started_at_utc") is not None and started_at is None:
                    metadata_parse_errors.append("metadata.started_at_utc is not valid ISO datetime.")
                if metadata_obj.get("ended_at_utc") is not None and ended_at is None:
                    metadata_parse_errors.append("metadata.ended_at_utc is not valid ISO datetime.")
                status = metadata_obj.get("status")
                if (
                    isinstance(status, str)
                    and status.lower() in TERMINAL_RUN_STATUSES
                    and _is_blank(metadata_obj.get("ended_at_utc"))
                ):
                    metadata_parse_errors.append(
                        "metadata.ended_at_utc is required when status is stopped/aborted."
                    )
                if started_at is not None and ended_at is not None and ended_at < started_at:
                    metadata_parse_errors.append(
                        "metadata.ended_at_utc is earlier than metadata.started_at_utc."
                    )
        except json.JSONDecodeError as exc:
            metadata_parse_errors.append(f"metadata.json is not parseable JSON: {exc}")
        except OSError as exc:
            metadata_parse_errors.append(f"Failed to read metadata.json: {exc}")
    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="metadata_integrity",
        details="metadata.json is parseable and has required fields.",
        check_errors=metadata_parse_errors,
        check_warnings=metadata_warnings,
    )

    metrics_row_count = 0
    metric_frames: list[int] = []
    metric_times: list[float] = []
    metrics_header: list[str] | None = None
    metrics_errors: list[str] = []
    metrics_warnings: list[str] = []
    if not metrics_path.is_file():
        metrics_errors.append("metrics.csv is missing.")
    else:
        try:
            with metrics_path.open("r", newline="", encoding="utf-8") as file_obj:
                reader = csv.reader(file_obj)
                rows = list(reader)
            if not rows:
                metrics_errors.append("metrics.csv is empty.")
            else:
                metrics_header = rows[0]
                if metrics_header != EXPECTED_METRICS_HEADERS:
                    metrics_errors.append(
                        "metrics.csv header mismatch. "
                        f"Expected: {EXPECTED_METRICS_HEADERS}. Found: {metrics_header}"
                    )

                for row_index, row in enumerate(rows[1:], start=CSV_FIRST_DATA_ROW_INDEX):
                    if not row or all(cell.strip() == "" for cell in row):
                        metrics_errors.append(
                            f"metrics.csv row {row_index} is blank/malformed."
                        )
                        continue
                    if row == metrics_header:
                        metrics_errors.append(
                            f"metrics.csv row {row_index} duplicates the header row."
                        )
                        continue
                    if len(row) != len(metrics_header):
                        metrics_errors.append(
                            f"metrics.csv row {row_index} has {len(row)} columns; "
                            f"expected {len(metrics_header)}."
                        )
        except (OSError, csv.Error) as exc:
            metrics_errors.append(f"metrics.csv read/parse failure: {exc}")

        if metrics_header:
            try:
                with metrics_path.open("r", newline="", encoding="utf-8") as file_obj:
                    dict_reader = csv.DictReader(file_obj)
                    for row_index, row in enumerate(
                        dict_reader, start=CSV_FIRST_DATA_ROW_INDEX
                    ):
                        if row is None:
                            metrics_errors.append(f"metrics.csv row {row_index} is missing.")
                            continue

                        metrics_row_count += 1
                        raw_frame = row.get("frame")
                        parsed_frame = _parse_int(raw_frame)
                        if _is_blank(raw_frame):
                            metrics_errors.append(f"metrics.csv row {row_index} has blank frame.")
                        elif parsed_frame is None:
                            metrics_errors.append(
                                f"metrics.csv row {row_index} has invalid frame value: {raw_frame!r}"
                            )
                        else:
                            metric_frames.append(parsed_frame)

                        raw_time = row.get("sim_time_s")
                        parsed_time = _parse_float(raw_time)
                        if _is_blank(raw_time):
                            metrics_errors.append(
                                f"metrics.csv row {row_index} has blank sim_time_s."
                            )
                        elif parsed_time is None:
                            metrics_errors.append(
                                f"metrics.csv row {row_index} has invalid sim_time_s: {raw_time!r}"
                            )
                        else:
                            metric_times.append(parsed_time)

                        for column in EXPECTED_METRICS_HEADERS:
                            if column in ("frame", "sim_time_s"):
                                continue
                            raw_value = row.get(column)
                            if _is_blank(raw_value):
                                continue
                            if _parse_float(raw_value) is None:
                                metrics_errors.append(
                                    f"metrics.csv row {row_index} has invalid numeric "
                                    f"value in '{column}': {raw_value!r}"
                                )
            except (OSError, csv.Error) as exc:
                metrics_errors.append(f"metrics.csv data scan failed: {exc}")

        previous_frame: int | None = None
        previous_time: float | None = None
        for idx, frame in enumerate(metric_frames):
            if previous_frame is not None and frame < previous_frame:
                metrics_errors.append(
                    f"metrics.csv frame decreases at metric index {idx + 1}: "
                    f"{frame} < {previous_frame}"
                )
                break
            previous_frame = frame
        for idx, sim_time in enumerate(metric_times):
            if previous_time is not None and sim_time < previous_time:
                metrics_errors.append(
                    f"metrics.csv sim_time_s decreases at metric index {idx + 1}: "
                    f"{sim_time} < {previous_time}"
                )
                break
            previous_time = sim_time

    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="metrics_integrity",
        details=(
            "metrics.csv is parseable, has expected headers, valid numeric/time fields, "
            "and nondecreasing frame/sim_time_s."
        ),
        check_errors=metrics_errors,
        check_warnings=metrics_warnings,
    )

    event_count = 0
    events_errors: list[str] = []
    events_warnings: list[str] = []
    if not events_path.is_file():
        events_errors.append("events.json is missing.")
    else:
        try:
            events_loaded = json.loads(events_path.read_text(encoding="utf-8"))
            if not isinstance(events_loaded, list):
                events_errors.append("events.json must contain a JSON array.")
            else:
                frame_min = min(metric_frames) if metric_frames else None
                frame_max = max(metric_frames) if metric_frames else None
                time_min = min(metric_times) if metric_times else None
                time_max = max(metric_times) if metric_times else None
                metadata_run_id = (
                    metadata_obj.get("run_id")
                    if isinstance(metadata_obj, dict)
                    and isinstance(metadata_obj.get("run_id"), str)
                    else None
                )
                previous_event_frame: int | None = None

                for index, event in enumerate(events_loaded):
                    event_count += 1
                    prefix = f"events.json item {index}"
                    if not isinstance(event, dict):
                        events_errors.append(f"{prefix} must be a JSON object.")
                        continue

                    event_type = event.get("type")
                    if not isinstance(event_type, str) or event_type.strip() == "":
                        events_errors.append(f"{prefix} has missing/invalid 'type'.")

                    event_run_id = event.get("run_id")
                    if not isinstance(event_run_id, str) or event_run_id.strip() == "":
                        events_errors.append(f"{prefix} has missing/invalid 'run_id'.")
                    elif metadata_run_id is not None and event_run_id != metadata_run_id:
                        events_errors.append(
                            f"{prefix} run_id {event_run_id!r} does not match "
                            f"metadata run_id {metadata_run_id!r}."
                        )

                    raw_frame = event.get("frame")
                    parsed_frame = _parse_int(raw_frame)
                    if _is_blank(raw_frame):
                        events_errors.append(f"{prefix} has missing 'frame'.")
                    elif parsed_frame is None:
                        events_errors.append(f"{prefix} has invalid frame value: {raw_frame!r}")
                    else:
                        if previous_event_frame is not None and parsed_frame < previous_event_frame:
                            # Event files can occasionally arrive slightly out of sequence.
                            events_warnings.append(
                                f"{prefix} frame decreases: {parsed_frame} < {previous_event_frame}."
                            )
                        previous_event_frame = parsed_frame
                        if frame_min is not None and frame_max is not None:
                            if parsed_frame < frame_min or parsed_frame > frame_max:
                                message = (
                                    f"{prefix} frame {parsed_frame} is outside metrics frame range "
                                    f"[{frame_min}, {frame_max}]."
                                )
                                if event_type == "run_started":
                                    events_warnings.append(message)
                                else:
                                    events_errors.append(message)

                    raw_time = event.get("sim_time_s")
                    if raw_time is not None:
                        parsed_time = _parse_float(raw_time)
                        if parsed_time is None:
                            events_errors.append(
                                f"{prefix} has invalid sim_time_s value: {raw_time!r}"
                            )
                        elif time_min is not None and time_max is not None:
                            if parsed_time < time_min or parsed_time > time_max:
                                message = (
                                    f"{prefix} sim_time_s {parsed_time} is outside "
                                    f"metrics time range [{time_min}, {time_max}]."
                                )
                                if event_type == "run_started":
                                    events_warnings.append(message)
                                else:
                                    events_errors.append(message)
        except json.JSONDecodeError as exc:
            events_errors.append(f"events.json is not parseable JSON: {exc}")
        except OSError as exc:
            events_errors.append(f"Failed to read events.json: {exc}")

    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="events_integrity",
        details=(
            "events.json is parseable and event records are structurally valid; "
            "event frame/time values fall in the run's valid range."
        ),
        check_errors=events_errors,
        check_warnings=events_warnings,
    )

    loader_errors: list[str] = []
    loaded_data = None
    try:
        loaded_data = RunDataLoader().load_run(run_dir)
    except Exception as exc:
        loader_errors.append(f"RunDataLoader failed to load run artifacts: {exc}")
    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="loader_roundtrip",
        details="RunDataLoader can parse metadata, metrics, and events for this run.",
        check_errors=loader_errors,
    )

    loader_count_errors: list[str] = []
    if loaded_data is not None:
        if metrics_row_count != len(loaded_data.metrics):
            loader_count_errors.append(
                "Raw metrics row count does not match RunDataLoader metrics count: "
                f"{metrics_row_count} != {len(loaded_data.metrics)}"
            )
        if event_count != len(loaded_data.events):
            loader_count_errors.append(
                "Raw event count does not match RunDataLoader event count: "
                f"{event_count} != {len(loaded_data.events)}"
            )
    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="loader_raw_count_consistency",
        details="Raw artifact row counts match counts loaded through RunDataLoader.",
        check_errors=loader_count_errors,
    )

    consistency_errors: list[str] = []
    consistency_warnings: list[str] = []
    if metadata_obj is not None:
        started_at = _parse_iso_utc(metadata_obj.get("started_at_utc"))
        ended_at = _parse_iso_utc(metadata_obj.get("ended_at_utc"))
        metrics_duration = None
        if metric_times:
            metrics_duration = max(metric_times) - min(metric_times)
            if metrics_duration < 0:
                consistency_errors.append("Metrics duration is negative.")
        if started_at is not None and ended_at is not None:
            wall_duration = (ended_at - started_at).total_seconds()
            if wall_duration < 0:
                consistency_errors.append("Metadata wall-clock duration is negative.")
            if metrics_duration is not None:
                if metrics_duration > wall_duration + METRICS_WALL_DURATION_MAX_LEAD_S:
                    consistency_errors.append(
                        "Metrics duration exceeds metadata wall duration by more than "
                        "5 seconds."
                    )
                elif abs(metrics_duration - wall_duration) > max(
                    WALL_DURATION_DRIFT_ABS_THRESHOLD_S,
                    wall_duration * WALL_DURATION_DRIFT_RATIO_THRESHOLD,
                ):
                    consistency_warnings.append(
                        "Metrics duration differs significantly from metadata wall duration."
                    )

    _record_check(
        checks=checks,
        errors=errors,
        warnings=warnings,
        name="duration_and_timeline_consistency",
        details="Run duration and recorded timestamps are logically consistent.",
        check_errors=consistency_errors,
        check_warnings=consistency_warnings,
    )

    summary: dict[str, Any] = {
        "run_dir": str(run_dir),
        "metric_row_count": metrics_row_count,
        "event_count": event_count,
        "metadata_run_id": metadata_obj.get("run_id") if isinstance(metadata_obj, dict) else None,
    }
    if metric_frames:
        summary["metric_frame_min"] = min(metric_frames)
        summary["metric_frame_max"] = max(metric_frames)
    if metric_times:
        summary["metric_sim_time_min"] = min(metric_times)
        summary["metric_sim_time_max"] = max(metric_times)
        summary["metric_duration_s"] = max(metric_times) - min(metric_times)
    if loaded_data is not None:
        summary["loader_metric_rows"] = len(loaded_data.metrics)
        summary["loader_event_rows"] = len(loaded_data.events)

    return {
        "passed": not errors,
        "checks": [check.to_dict() for check in checks],
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }
