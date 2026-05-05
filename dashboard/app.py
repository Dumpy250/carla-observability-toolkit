from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, jsonify, render_template, send_from_directory

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
RUNS_DIR = REPO_ROOT / "runs"
FRONTEND_DIST_DIR = REPO_ROOT / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.runtime.run_data_loader import RunDataLoader
from cot.runtime.run_statistics import compute_run_summary

app = Flask(__name__, template_folder="templates", static_folder="static")
loader = RunDataLoader()


def _read_run_metadata(run_dir: Path) -> dict[str, Any]:
    """Read metadata.json from a run directory, returning empty dict on failure."""
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        with metadata_path.open("r", encoding="utf-8") as file_obj:
            loaded = json.load(file_obj)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _list_run_dirs() -> list[Path]:
    """List run directories under runs/, sorted newest first."""
    if not RUNS_DIR.exists() or not RUNS_DIR.is_dir():
        return []

    run_dirs = [path for path in RUNS_DIR.iterdir() if path.is_dir()]
    run_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return run_dirs


def _frontend_missing_response() -> Response:
    """Return setup instructions when the React production build is missing."""
    return Response(
        "React dashboard build not found.\n\n"
        "Run the following commands to build the frontend:\n"
        "cd frontend\n"
        "npm run build\n",
        mimetype="text/plain",
        status=503,
    )


@app.get("/api/runs")
def get_runs() -> Any:
    """Return available run directories with light metadata."""
    response: list[dict[str, Any]] = []
    for run_dir in _list_run_dirs():
        metadata = _read_run_metadata(run_dir)
        response.append(
            {
                "run_dir_name": run_dir.name,
                "run_id": metadata.get("run_id"),
                "status": metadata.get("status"),
            }
        )
    return jsonify(response)


@app.get("/api/runs/<string:run_dir_name>")
def get_run_details(run_dir_name: str) -> Any:
    """Return full run details and computed summary for one run directory."""
    if run_dir_name in {"", ".", ".."} or Path(run_dir_name).name != run_dir_name:
        return jsonify({"error": "Invalid run directory name"}), 400

    run_dir = RUNS_DIR / run_dir_name
    if not run_dir.exists() or not run_dir.is_dir():
        return jsonify({"error": f"Run not found: {run_dir_name}"}), 404

    try:
        run_data = loader.load_run(run_dir)
        summary = compute_run_summary(run_data)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return jsonify({"error": f"Failed to load run: {exc}"}), 500

    return jsonify(
        {
            "metadata": run_data.metadata,
            "summary": asdict(summary),
            "metrics": [asdict(row) for row in run_data.metrics],
            "events": [asdict(event) for event in run_data.events],
        }
    )


@app.get("/legacy")
def legacy_dashboard() -> str:
    """Legacy Flask dashboard (deprecated, replaced by React)"""
    return render_template("index.html")


@app.get("/")
@app.get("/<path:path>")
def serve_dashboard(path: str = "") -> Response:
    """Serve React dashboard build and support client-side routing."""
    if path.startswith("api/"):
        abort(404)

    if not FRONTEND_INDEX_PATH.exists():
        return _frontend_missing_response()

    if path:
        requested_path = (FRONTEND_DIST_DIR / path).resolve()
        if FRONTEND_DIST_DIR.resolve() in requested_path.parents and requested_path.is_file():
            return send_from_directory(str(FRONTEND_DIST_DIR), path)

    return send_from_directory(str(FRONTEND_DIST_DIR), "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
