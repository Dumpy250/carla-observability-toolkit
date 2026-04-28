from __future__ import annotations

import math
from dataclasses import dataclass

from cot.runtime.run_data_loader import LoadedRunData, RunMetricRow


@dataclass(slots=True)
class RunSummaryStats:
    """High-level summary statistics computed from one loaded run."""

    max_speed_mps: float | None
    avg_speed_mps: float | None
    total_collisions: int
    run_duration_s: float | None
    avg_acceleration_mps2: float | None
    metric_row_count: int
    event_count: int


def _average(values: list[float]) -> float | None:
    """Return arithmetic mean for a non-empty list, otherwise None."""
    if not values:
        return None
    return sum(values) / len(values)


def _acceleration_magnitude(row: RunMetricRow) -> float | None:
    """Return acceleration vector magnitude for a metric row when all axes exist."""
    ax = row.acceleration_x
    ay = row.acceleration_y
    az = row.acceleration_z
    if ax is None or ay is None or az is None:
        return None
    return math.sqrt((ax * ax) + (ay * ay) + (az * az))


def compute_run_summary(run_data: LoadedRunData) -> RunSummaryStats:
    """Compute aggregate summary statistics from loaded run data."""
    speeds = [row.speed_mps for row in run_data.metrics if row.speed_mps is not None]
    timestamps = [row.sim_time_s for row in run_data.metrics if row.sim_time_s is not None]

    acceleration_magnitudes: list[float] = []
    for row in run_data.metrics:
        magnitude = _acceleration_magnitude(row)
        if magnitude is not None:
            acceleration_magnitudes.append(magnitude)

    total_collisions = sum(1 for event in run_data.events if event.event_type == "collision")

    return RunSummaryStats(
        max_speed_mps=max(speeds) if speeds else None,
        avg_speed_mps=_average(speeds),
        total_collisions=total_collisions,
        run_duration_s=(max(timestamps) - min(timestamps)) if timestamps else None,
        avg_acceleration_mps2=_average(acceleration_magnitudes),
        metric_row_count=len(run_data.metrics),
        event_count=len(run_data.events),
    )
