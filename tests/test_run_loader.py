from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.core.run_data_loader import RunDataLoader


def find_latest_run_dir(runs_dir: Path) -> Path | None:
    """Return the most recently modified run directory, if one exists."""
    run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
    if not run_dirs:
        return None
    return max(run_dirs, key=lambda path: path.stat().st_mtime)


def main() -> int:
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

    print("Run directory:", run_data.run_dir)
    print("Run ID:", run_data.metadata.get("run_id"))
    print("Run status:", run_data.metadata.get("status"))
    print("Metric rows:", len(run_data.metrics))
    print("Event rows:", len(run_data.events))

    if run_data.metrics:
        print("First metric row:", run_data.metrics[0])

    if run_data.events:
        print("First event:", run_data.events[0])

    print("RunDataLoader smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
