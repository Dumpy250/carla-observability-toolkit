from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    return next(
        (
            parent
            for parent in Path(__file__).resolve().parents
            if (parent / "README.md").exists() and (parent / "src").is_dir()
        ),
        Path(__file__).resolve().parents[1],
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.core.run_validator import validate_run_directory


def find_latest_run_dir(runs_dir: Path) -> Path | None:
    run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
    if not run_dirs:
        return None
    return max(run_dirs, key=lambda path: path.stat().st_mtime)


def resolve_run_dir(run_input: str | None) -> Path:
    if run_input:
        candidate = Path(run_input).expanduser()
        if candidate.is_absolute() and candidate.is_dir():
            return candidate.resolve()

        cwd_candidate = (Path.cwd() / candidate).resolve()
        if cwd_candidate.is_dir():
            return cwd_candidate

        runs_candidate = (REPO_ROOT / "runs" / candidate).resolve()
        if runs_candidate.is_dir():
            return runs_candidate

        raise FileNotFoundError(
            "Run directory not found. Checked: "
            f"{candidate}, {cwd_candidate}, and {runs_candidate}"
        )

    runs_dir = REPO_ROOT / "runs"
    if not runs_dir.exists() or not runs_dir.is_dir():
        raise FileNotFoundError(f"Runs directory not found: {runs_dir}")
    latest = find_latest_run_dir(runs_dir)
    if latest is None:
        raise FileNotFoundError(f"No run directories found in: {runs_dir}")
    return latest.resolve()


def _print_report(report: dict[str, Any]) -> None:
    print(f"Run: {report['summary'].get('run_dir')}")
    print(f"Overall: {'PASS' if report['passed'] else 'FAIL'}")
    print()
    print("Checks:")
    for check in report.get("checks", []):
        status = "PASS" if check.get("passed") else "FAIL"
        print(f"  [{status}] {check.get('name')}")
        details = check.get("details")
        if details:
            print(f"    {details}")
        for error in check.get("errors", []):
            print(f"    ERROR: {error}")
        for warning in check.get("warnings", []):
            print(f"    WARNING: {warning}")
    print()
    print("Summary:")
    for key, value in report.get("summary", {}).items():
        print(f"  {key}: {value}")

    if report.get("warnings"):
        print()
        print(f"Warnings ({len(report['warnings'])}):")
        for warning in report["warnings"]:
            print(f"  - {warning}")

    if report.get("errors"):
        print()
        print(f"Errors ({len(report['errors'])}):")
        for error in report["errors"]:
            print(f"  - {error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CARLA run data integrity for one run directory."
    )
    parser.add_argument(
        "run_dir",
        nargs="?",
        default=None,
        help="Optional run directory path or run directory name under runs/.",
    )
    args = parser.parse_args()

    try:
        run_dir = resolve_run_dir(args.run_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    report = validate_run_directory(run_dir)
    _print_report(report)
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

