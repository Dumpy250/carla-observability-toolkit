from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.core.run_data_loader import RunDataLoader
from cot.core.run_statistics import compute_run_summary


def find_latest_run_dir(runs_dir: Path) -> Path | None:
    """Return the most recently modified run directory from runs/."""
    run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
    if not run_dirs:
        return None
    return max(run_dirs, key=lambda path: path.stat().st_mtime)


def main() -> int:
    """Load the newest run and print computed summary statistics."""
    runs_dir = REPO_ROOT / "runs"
    if not runs_dir.exists() or not runs_dir.is_dir():
        print(f"Runs directory does not exist: {runs_dir}")
        return 1

    latest_run = find_latest_run_dir(runs_dir)
    if latest_run is None:
        print(f"No run directories found in: {runs_dir}")
        return 1

    loader = RunDataLoader()
    try:
        run_data = loader.load_run(latest_run)
    except Exception as exc:
        print(f"Failed to load run data from {latest_run}: {exc}")
        return 1

    summary = compute_run_summary(run_data)

    print("Run directory:", run_data.run_dir)
    print("max_speed_mps:", summary.max_speed_mps)
    print("avg_speed_mps:", summary.avg_speed_mps)
    print("total_collisions:", summary.total_collisions)
    print("run_duration_s:", summary.run_duration_s)
    print("avg_acceleration_mps2:", summary.avg_acceleration_mps2)
    print("metric_row_count:", summary.metric_row_count)
    print("event_count:", summary.event_count)

    print("Run statistics smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())