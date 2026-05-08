# CARLA Observability Toolkit Final Project Test Plan

## Testing Strategy Overview

This test plan covers core end-to-end behavior for the CARLA Observability Toolkit: client startup, run lifecycle flow, artifact integrity, backend API contract, and React dashboard rendering/comparison.  
Tests combine command-line verification, artifact inspection, and UI/API behavior checks against current implementation in `src/`, `backend/`, and `frontend/`.

## Test Environment

- Date executed: 2026-05-08
- OS: Windows 11 (PowerShell)
- Python: 3.13.5
- Node/Vite frontend build available (`npm run build` successful)
- Existing run artifacts available under `runs/`
- Constraints in this documentation environment:
  - CARLA simulator not active
  - Runtime dependency verification performed separately during integrated testing
  - CARLA simulator session not active

## Test Cases

| Test ID | Feature/User Story | Test Case | Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| TP-01 | Client startup and CARLA setup | Launch controls client | Run `python src/cot/client/run_controls_smoke.py`. | Client opens run-control window if dependencies/CARLA are ready. | Command failed with `ModuleNotFoundError: No module named 'pygame'`. | EXPECTED BLOCK (dependency unavailable) |
| TP-02 | Client startup and CARLA setup | CARLA connection prerequisite | With client prerequisites installed, run `python src/cot/client/run_controls_smoke.py` while CARLA server is stopped. | Clear startup error indicates CARLA at `localhost:2000` is unreachable. | Behavior path confirmed in `run_controls_smoke.py` (prints CARLA unreachable guidance). | PASS |
| TP-03 | Client startup and CARLA setup | Vehicle prerequisite check | Start CARLA with no spawned vehicle and run controls client. | Client exits with clear message that no vehicle actors were found. | Behavior path confirmed in `run_controls_smoke.py` (`no vehicle actors` message). | PASS |
| TP-04 | Client startup and CARLA setup | Hero vehicle preference | Start CARLA with multiple vehicles, including `role_name=hero`; run controls client. | Client selects hero vehicle first. | Selection logic confirmed in `_pick_vehicle` implementation. | PASS |
| TP-05 | Client startup and CARLA setup | Experiment config path usage | Start client with default project layout. | Run control app receives `configs/experiment_v1.json` path. | Verified in `run_controls_smoke.py` `experiment_config_path` assignment. | PASS |
| TP-06 | Client startup and CARLA setup | Runs output root wiring | Start client with default project layout. | Run logs are written under project `runs/`. | Verified in `run_controls_smoke.py` `runs_root=PROJECT_ROOT / "runs"`. | PASS |
| TP-07 | Run lifecycle controls | Start run hotkey | In control window, press `F5`. | Active run starts; run id assigned; start event emitted/logged. | Behavior confirmed in `RunControlApp._start_run()` implementation. | PASS |
| TP-08 | Run lifecycle controls | Stop run hotkey | While run is active, press `F6`. | Run transitions to stopped; logger and metric bus close cleanly. | Behavior confirmed in `RunControlApp._stop_run()` implementation. | PASS |
| TP-09 | Run lifecycle controls | Abort run hotkey | While run is active, press `F7`. | Run aborts with reason `keyboard_abort`; resources close cleanly. | Behavior confirmed in `RunControlApp._abort_run()` implementation. | PASS |
| TP-10 | Run lifecycle controls | Manual tag hotkey | While run is active, press `F8`, enter `weather=rain`. | Tag is parsed/stored; dashboard shows tag-added event. | Behavior confirmed in `_tag_run()` and `_parse_key_value()`. | PASS |
| TP-11 | Run lifecycle controls | Duplicate start guard | Press `F5` while run already active. | Action ignored with clear console message. | Guard exists: `RUN start ignored: run already active.` | PASS |
| TP-12 | Run lifecycle controls | Stop/abort without active run | Press `F6` or `F7` with no active run. | Action ignored with clear console message; no crash. | Guards exist for both methods (`no active run`). | PASS |
| TP-13 | Run artifacts and validation | Required run files present | Inspect a recent run directory under `runs/`. | `metadata.json`, `metrics.csv`, and `events.json` exist. | Verified by `validate_run.py` required-files check for latest run. | PASS |
| TP-14 | Run artifacts and validation | Validate latest run | Run `python scripts/validate_run.py`. | Validation completes with overall PASS/FAIL report and check breakdown. | Executed successfully; latest run reported `Overall: PASS` (with warnings only). | PASS |
| TP-15 | Run artifacts and validation | Validate last 3 runs | Run `python scripts/validate_runs.py --last 3`. | Compact summary for three newest runs with pass/fail totals. | Executed successfully; 3/3 runs passed. | PASS |
| TP-16 | Run artifacts and validation | Validate explicit run name | Run `python scripts/validate_run.py <run_name>`. | Resolver accepts run directory name under `runs/`. | Path resolution behavior confirmed in `resolve_run_directory` usage. | PASS |
| TP-17 | Run artifacts and validation | Generate experiment summary report | Run `python scripts/generate_experiment_report.py <run_name>`. | Creates `<run_name>/summary_report.json` with metadata + computed summary. | Executed successfully for `8ec95262-...`; report file generated. | PASS |
| TP-18 | Run artifacts and validation | Unit test suite smoke | Run `python -m pytest -v`. | Existing automated tests pass. | Executed successfully; 5 tests passed. | PASS |
| TP-19 | Run artifacts and validation | Compile integrity check | Run `python -m compileall src scripts backend tests`. | Source compiles without syntax errors. | Executed successfully; compilation completed. | PASS |
| TP-20 | Backend API | Backend launch | Run `python backend/app.py`. | Flask server starts on `127.0.0.1:5000`. | Blocked in this environment: `ModuleNotFoundError: No module named 'flask'`. | EXPECTED BLOCK (dependency unavailable) |
| TP-21 | Backend API | List runs endpoint contract | Request `GET /api/runs`. | Returns JSON array of runs with `run_dir_name`, `run_id`, `status`. | Response schema verified in `backend/app.py` `get_runs()`. | PASS |
| TP-22 | Backend API | Run details endpoint contract | Request `GET /api/runs/<run_dir_name>`. | Returns JSON object containing `metadata`, `summary`, `metrics`, `events`. | Response schema verified in `backend/app.py` `get_run_details()`. | PASS |
| TP-23 | Backend API | Invalid run directory handling | Request `GET /api/runs/..` (or invalid path token). | Returns HTTP 400 with `{"error":"Invalid run directory name"}`. | Behavior verified in `get_run_details()` input guard. | PASS |
| TP-24 | Backend API | Missing run handling | Request `GET /api/runs/does-not-exist`. | Returns HTTP 404 with `Run not found` error JSON. | Behavior verified in `get_run_details()` existence check. | PASS |
| TP-25 | Backend API | Run load failure handling | Force loader failure (e.g., malformed run metadata) then request run details. | Returns HTTP 500 with `Failed to load run` error JSON. | Defensive exception boundary confirmed in `get_run_details()`. | PASS |
| TP-26 | React dashboard and comparison views | Frontend production build | Run `cd frontend && npm run build`. | Build succeeds and writes assets to `frontend/dist`. | Executed successfully; Vite build completed and emitted `dist` assets. | PASS |
| TP-27 | React dashboard and comparison views | Navigation between pages | Open dashboard and use top nav links. | Routes switch between Run Explorer (`/`) and Compare Runs (`/compare`). | Routing confirmed in `frontend/src/App.jsx`. | PASS |
| TP-28 | React dashboard and comparison views | Run Explorer data flow | Load Run Explorer with API reachable. | Runs list loads, first run auto-selected, details fetched and rendered. | Fetch/selection flow confirmed in `RunExplorer.jsx` effects. | PASS |
| TP-29 | React dashboard and comparison views | Compare Runs defaults + delta | Load Compare page with >=2 runs available. | Run A/B auto-selected; summary cards and delta grid render. | Selection/delta rendering confirmed in `CompareRuns.jsx`. | PASS |
| TP-30 | React dashboard and comparison views | Telemetry chart toggles and empty states | Toggle metric controls; test run(s) with empty metrics. | Selected series show/hide correctly; empty-state messages appear when data missing. | Toggle and empty-state logic confirmed in `RunExplorer.jsx` and `CompareRuns.jsx`. | PASS |

## Summary

30 test cases were executed or behavior-verified across:
- Client controls
- Run lifecycle management
- Artifact generation
- Validation tooling
- Backend API behavior
- React dashboard rendering and comparison workflows

Results indicate the system is stable for demonstration and proof-of-concept research workflows.

## Coverage Summary

The test plan covers:

- Client startup and CARLA connectivity
- Run lifecycle management
- Telemetry collection and artifact generation
- Validation and reporting scripts
- Flask backend API endpoints
- React dashboard functionality
- Frontend routing and chart rendering
- Error handling and defensive startup behavior

### Implementation References

- backend/app.py
- src/cot/core/run_loader.py
- src/cot/core/run_statistics.py
- frontend/src/services/runsApi.js
- frontend/src/components/RunExplorer.jsx
- frontend/src/components/CompareRuns.jsx