from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.runtime.path_utils import find_repo_root, resolve_run_directory
from cot.runtime.run_validator import validate_run_directory

REPO_ROOT = find_repo_root(__file__)


def _sorted_run_dirs(runs_dir: Path) -> list[Path]:
    run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
    return sorted(run_dirs, key=lambda path: path.stat().st_mtime, reverse=True)


def _resolve_run_input(run_input: str, runs_dir: Path) -> Path:
    return resolve_run_directory(
        run_input=run_input,
        runs_dir=runs_dir,
        resolve_absolute=True,
        absolute_not_found_message="Run directory not found: {candidate}",
        include_candidate_in_checked_message=False,
    )


def _print_compact_fail_details(errors: list[str], warnings: list[str], verbose: bool) -> None:
    for error in errors:
        print(f"  - {error}")
    if verbose:
        for warning in warnings:
            print(f"  ~ {warning}")


def _select_run_dirs(args: argparse.Namespace, runs_dir: Path) -> list[Path]:
    if args.run_dirs:
        return [_resolve_run_input(run_input, runs_dir) for run_input in args.run_dirs]

    discovered = _sorted_run_dirs(runs_dir)
    if not discovered:
        return []

    if args.all:
        return discovered
    if args.last is not None:
        return discovered[: args.last]
    # Default and --latest both validate only the newest run.
    return [discovered[0]]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-validate one or more CARLA run directories."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--latest",
        action="store_true",
        help="Validate the most recent run (default behavior when no args are provided).",
    )
    mode_group.add_argument(
        "--last",
        type=int,
        metavar="N",
        help="Validate the N most recent runs.",
    )
    mode_group.add_argument(
        "--all",
        action="store_true",
        help="Validate all runs under runs/.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include warnings in compact output.",
    )
    parser.add_argument(
        "run_dirs",
        nargs="*",
        help="Specific run directory names (relative to runs/) or paths.",
    )
    args = parser.parse_args()

    if args.last is not None and args.last <= 0:
        print("ERROR: --last must be greater than 0.", file=sys.stderr)
        return 1

    runs_dir = REPO_ROOT / "runs"
    if not runs_dir.exists() or not runs_dir.is_dir():
        print(f"ERROR: runs directory does not exist: {runs_dir}", file=sys.stderr)
        return 1

    try:
        run_dirs = _select_run_dirs(args, runs_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not run_dirs:
        print(f"ERROR: no run directories found in: {runs_dir}", file=sys.stderr)
        return 1

    total = 0
    passed = 0
    failed = 0

    for run_dir in run_dirs:
        total += 1
        report: dict[str, Any] = validate_run_directory(run_dir)
        run_name = run_dir.name
        if report.get("passed"):
            passed += 1
            print(f"[PASS] {run_name}")
            if args.verbose:
                for warning in report.get("warnings", []):
                    print(f"  ~ {warning}")
        else:
            failed += 1
            print(f"[FAIL] {run_name}")
            _print_compact_fail_details(
                errors=report.get("errors", []),
                warnings=report.get("warnings", []),
                verbose=args.verbose,
            )

    print()
    print("Summary:")
    print(f"  total: {total}")
    print(f"  passed: {passed}")
    print(f"  failed: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

