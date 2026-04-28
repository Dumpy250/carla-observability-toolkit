from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.runtime.run_data_loader import LoadedRunData
from cot.runtime.run_data_loader import RunEvent
from cot.runtime.run_data_loader import RunMetricRow
from cot.runtime.run_statistics import compute_run_summary

def test_compute_run_summary_with_synthetic_data() -> None:
    run_data = LoadedRunData(
        run_dir=Path("/tmp/fake_run"),
        metadata={
            "run_id": "run-summary-1",
            "started_at_utc": "2026-01-01T00:00:00+00:00",
            "status": "stopped",
        },
        metrics=[
            RunMetricRow(
                frame=1,
                sim_time_s=0.0,
                speed_mps=10.0,
                acceleration_x=0.0,
                acceleration_y=0.0,
                acceleration_z=0.0,
                steering=0.0,
                throttle=0.2,
                brake=0.0,
                position_x=0.0,
                position_y=0.0,
                position_z=0.0,
                heading=0.0,
            ),
            RunMetricRow(
                frame=2,
                sim_time_s=1.0,
                speed_mps=20.0,
                acceleration_x=0.0,
                acceleration_y=0.0,
                acceleration_z=0.0,
                steering=0.1,
                throttle=0.3,
                brake=0.0,
                position_x=1.0,
                position_y=0.0,
                position_z=0.0,
                heading=5.0,
            ),
            RunMetricRow(
                frame=3,
                sim_time_s=2.0,
                speed_mps=30.0,
                acceleration_x=0.0,
                acceleration_y=0.0,
                acceleration_z=0.0,
                steering=0.2,
                throttle=0.4,
                brake=0.0,
                position_x=2.0,
                position_y=0.0,
                position_z=0.0,
                heading=10.0,
            ),
        ],
        events=[
            RunEvent(
                run_id="run-summary-1",
                frame=2,
                event_type="collision",
                sim_time_s=1.5,
                payload={"type": "collision"},
            ),
            RunEvent(
                run_id="run-summary-1",
                frame=3,
                event_type="lane_invasion",
                sim_time_s=1.8,
                payload={"type": "lane_invasion"},
            ),
        ],
    )

    summary = compute_run_summary(run_data)

    assert summary.max_speed_mps == 30.0
    assert summary.avg_speed_mps == 20.0
    assert summary.total_collisions == 1
    assert summary.event_count == 2
    assert summary.metric_row_count == 3
