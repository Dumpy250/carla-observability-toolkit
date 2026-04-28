from __future__ import annotations

from pathlib import Path


def find_repo_root(start_file: str | Path) -> Path:
    script_path = Path(start_file).resolve()
    return next(
        (
            parent
            for parent in script_path.parents
            if (parent / "README.md").exists() and (parent / "src").is_dir()
        ),
        script_path.parents[1],
    )


def resolve_run_directory(
    run_input: str,
    runs_dir: Path,
    *,
    resolve_absolute: bool,
    absolute_not_found_message: str | None,
    include_candidate_in_checked_message: bool,
) -> Path:
    candidate = Path(run_input).expanduser()
    if candidate.is_absolute():
        if candidate.is_dir():
            return candidate.resolve() if resolve_absolute else candidate
        if absolute_not_found_message is not None:
            raise FileNotFoundError(absolute_not_found_message.format(candidate=candidate))

    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.is_dir():
        return cwd_candidate

    runs_candidate = (runs_dir / candidate).resolve()
    if runs_candidate.is_dir():
        return runs_candidate

    if include_candidate_in_checked_message:
        raise FileNotFoundError(
            "Run directory not found. Checked: "
            f"{candidate}, {cwd_candidate}, and {runs_candidate}"
        )

    raise FileNotFoundError(
        "Run directory not found. Checked: "
        f"{cwd_candidate} and {runs_candidate}"
    )
