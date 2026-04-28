from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.runtime.path_utils import find_repo_root, resolve_run_directory
from cot.runtime.run_data_loader import RunDataLoader
from cot.runtime.run_statistics import compute_run_summary

REPO_ROOT = find_repo_root(__file__)


def _resolve_run_dir(run_input: str, repo_root: Path) -> Path:
    return resolve_run_directory(
        run_input=run_input,
        runs_dir=repo_root / "runs",
        resolve_absolute=False,
        absolute_not_found_message="Run directory not found: {candidate}",
        include_candidate_in_checked_message=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate summary_report.json for one persisted CARLA run directory."
        )
    )
    parser.add_argument(
        "run_dir",
        help="Run directory path, or run directory name relative to runs/",
    )
    args = parser.parse_args()

    try:
        run_dir = _resolve_run_dir(args.run_dir, REPO_ROOT)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    loader = RunDataLoader()
    try:
        run_data = loader.load_run(run_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: metadata missing for run '{run_dir}': {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: failed to load run artifacts from '{run_dir}': {exc}", file=sys.stderr)
        return 1

    if not isinstance(run_data.metadata, dict):
        print(
            f"ERROR: metadata missing or invalid in run '{run_dir}'",
            file=sys.stderr,
        )
        return 1

    try:
        summary = compute_run_summary(run_data)
    except Exception as exc:
        print(f"ERROR: summary generation failure for '{run_dir}': {exc}", file=sys.stderr)
        return 1

    report = {
        "report_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir_name": run_data.run_dir.name,
        "metadata": run_data.metadata,
        "summary": asdict(summary),
    }

    output_path = run_dir / "summary_report.json"
    try:
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: JSON write failure for '{output_path}': {exc}", file=sys.stderr)
        return 1

    print(f"Summary report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
