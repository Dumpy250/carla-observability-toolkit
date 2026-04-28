from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.runtime.run_data_loader import RunDataLoader

def test_run_data_loader_loads_minimal_fake_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()

    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "run-001",
                "started_at_utc": "2026-01-01T00:00:00+00:00",
                "status": "stopped",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.csv").write_text(
        "\n".join(
            [
                "frame,sim_time_s,speed_mps,acceleration_x,acceleration_y,acceleration_z,steering,throttle,brake,position_x,position_y,position_z,heading",
                "1,0.0,10.0,0.1,0.0,0.0,0.01,0.3,0.0,100.0,200.0,1.0,90.0",
                "2,0.1,12.0,0.2,0.1,0.0,0.02,0.4,0.0,101.0,200.5,1.0,91.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "run-001",
                    "frame": 1,
                    "type": "run_started",
                    "sim_time_s": 0.0,
                },
                {
                    "run_id": "run-001",
                    "frame": 2,
                    "type": "collision",
                    "sim_time_s": 0.1,
                },
            ]
        ),
        encoding="utf-8",
    )

    run_data = RunDataLoader().load_run(run_dir)

    assert run_data.metadata.get("run_id") == "run-001"
    assert len(run_data.metrics) == 2
    assert len(run_data.events) == 2
