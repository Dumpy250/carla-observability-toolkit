from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pygame

from cot.bus.metric_bus import MetricBus
from cot.bus.metric_bus import TelemetryMessage
from cot.client.collector_session import CollectorSession
from cot.client.dashboard_renderer import render_dashboard
from cot.client.dashboard_state import DashboardState
from cot.config.experiment_config import load_experiment_config
from cot.runtime.logger import RunLogger
from cot.runtime.run_manager import RunManager

DASHBOARD_FPS = 30


class RunControlApp:
    def __init__(
        self,
        world,
        vehicle,
        screen: pygame.Surface,
        title_font: pygame.font.Font,
        section_font: pygame.font.Font,
        label_font: pygame.font.Font,
        value_font: pygame.font.Font,
        metric_font: pygame.font.Font,
        speed_metric_font: pygame.font.Font,
        clock: pygame.time.Clock,
        runs_root: Path,
        experiment_config_path: Path,
    ) -> None:
        self._world = world
        self._vehicle = vehicle
        self._screen = screen
        self._title_font = title_font
        self._section_font = section_font
        self._label_font = label_font
        self._value_font = value_font
        self._metric_font = metric_font
        self._speed_metric_font = speed_metric_font
        self._clock = clock
        self._runs_root = runs_root
        self._experiment_config_path = experiment_config_path

        self._run_manager = RunManager()
        self._dashboard = DashboardState()
        self._metric_bus: MetricBus | None = None
        self._logger: RunLogger | None = None
        self._collector_session: CollectorSession | None = None

    def run(self) -> None:
        print("COT controls ready. Focus the pygame window. F5=start, F6=stop, F7=abort, F8=tag, ESC=quit.")
        running = True
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break

                    if event.type != pygame.KEYDOWN:
                        continue

                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F5:
                        self._start_run()
                    elif event.key == pygame.K_F6:
                        self._stop_run()
                    elif event.key == pygame.K_F7:
                        self._abort_run()
                    elif event.key == pygame.K_F8:
                        self._tag_run()

                render_dashboard(
                    self._screen,
                    self._title_font,
                    self._section_font,
                    self._label_font,
                    self._value_font,
                    self._metric_font,
                    self._speed_metric_font,
                    self._dashboard,
                )
                self._clock.tick(DASHBOARD_FPS)
        finally:
            self._cleanup()

    def _start_run(self) -> None:
        if self._run_manager.is_running():
            print("RUN start ignored: run already active.")
            return
        try:
            config = load_experiment_config(self._experiment_config_path)
        except Exception as exc:
            print(
                f"RUN start failed: unable to load experiment config "
                f"from {self._experiment_config_path}: {exc}"
            )
            return

        try:
            _apply_config_weather(self._world, config)
        except Exception as exc:
            try:
                self._run_manager.abort_run(reason=f"weather_apply_failed:{type(exc).__name__}")
            except Exception:
                pass
            print(f"RUN start failed: unable to apply weather from config: {exc}")
            return

        state = self._run_manager.start_run(self._world, self._vehicle, experiment_config=config)

        self._metric_bus = MetricBus()
        self._metric_bus.subscribe("metric.vehicle.state", self._dashboard.update_vehicle)
        self._metric_bus.subscribe("metric.event.", self._dashboard.push_event)
        self._logger = RunLogger(self._metric_bus, run_id=state.run_id, output_root=self._runs_root)

        frame = None
        sim_time_s = None
        try:
            snapshot = self._world.get_snapshot()
            if snapshot is not None:
                frame = getattr(snapshot, "frame", None)
                timestamp = getattr(snapshot, "timestamp", None)
                if timestamp is not None:
                    sim_time_s = getattr(timestamp, "elapsed_seconds", None)
        except Exception:
            pass

        payload = {
            "run_id": state.run_id,
            "type": "run_started",
            "source": "user",
            "trigger": "experiment_config",
        }
        if frame is not None:
            payload["frame"] = frame
        if sim_time_s is not None:
            payload["sim_time_s"] = sim_time_s
        self._metric_bus.publish(
            TelemetryMessage(
                topic="metric.event.run_started",
                run_id=state.run_id,
                frame=frame,
                sim_time_s=sim_time_s,
                payload=payload,
            )
        )

        self._collector_session = CollectorSession(self._metric_bus, self._world, self._vehicle, run_id=state.run_id)
        self._collector_session.start()
        self._dashboard.set_run(state.status, state.run_id)

        tags_payload = getattr(config, "tags", {})
        if not isinstance(tags_payload, dict):
            tags_payload = {}
        self._dashboard.set_experiment_metadata(
            getattr(config, "experiment_id", None),
            getattr(config, "config_name", None),
            tags_payload.get("scenario"),
            getattr(config, "seed", None),
        )

        self._logger.update_metadata(asdict(state))
        weather_payload = None
        if getattr(config, "weather", None) is not None:
            weather_value = getattr(config, "weather")
            if hasattr(weather_value, "to_dict"):
                weather_payload = weather_value.to_dict()
            elif isinstance(weather_value, dict):
                weather_payload = dict(weather_value)

        self._logger.update_metadata(
            {
                "experiment": {
                    "experiment_id": getattr(config, "experiment_id", None),
                    "config_name": getattr(config, "config_name", None),
                    "seed": getattr(config, "seed", None),
                    "duration_s": getattr(config, "duration_s", None),
                    "tags": dict(tags_payload),
                    "weather": weather_payload,
                    "config_path": str(self._experiment_config_path),
                }
            }
        )
        print(f"RUN started id={state.run_id}")

    def _stop_run(self) -> None:
        if not self._run_manager.is_running():
            print("RUN stop ignored: no active run.")
            return
        state = self._run_manager.stop_run()
        self._dashboard.set_run(state.status, state.run_id)
        self._stop_collectors()
        if self._logger is not None:
            self._logger.update_metadata(asdict(state))
            self._logger.close()
            self._logger = None
        if self._metric_bus is not None:
            self._metric_bus.close(drain=True)
            self._metric_bus = None
        print(f"RUN stopped id={state.run_id}")

    def _abort_run(self) -> None:
        if not self._run_manager.is_running():
            print("RUN abort ignored: no active run.")
            return
        state = self._run_manager.abort_run(reason="keyboard_abort")
        self._dashboard.set_run(state.status, state.run_id)
        self._stop_collectors()
        if self._logger is not None:
            self._logger.update_metadata(asdict(state))
            self._logger.close()
            self._logger = None
        if self._metric_bus is not None:
            self._metric_bus.close(drain=True)
            self._metric_bus = None
        print(f"RUN aborted id={state.run_id} reason={state.abort_reason}")

    def _tag_run(self) -> None:
        if not self._run_manager.is_running():
            print("TAG ignored: no active run.")
            self._dashboard.push_manual_event("tag ignored", alert_text="TAG IGNORED")
            return
        user_input = input("Enter tag key=value: ")
        parsed = _parse_key_value(user_input)
        if parsed is None:
            print("TAG ignored: expected key=value.")
            self._dashboard.push_manual_event("tag ignored", alert_text="TAG IGNORED")
            return
        key, value = parsed
        state = self._run_manager.tag(key, value)
        if self._logger is not None:
            self._logger.update_metadata(asdict(state))
        self._dashboard.push_manual_event(f"tag {key}={value}", alert_text="TAG ADDED")
        print(f"TAG added {key}={value}")

    def _stop_collectors(self) -> None:
        if self._collector_session is not None:
            self._collector_session.stop()
            self._collector_session = None

    def _cleanup(self) -> None:
        if self._run_manager.is_running():
            state = self._run_manager.stop_run()
            self._dashboard.set_run(state.status, state.run_id)
            if self._logger is not None:
                self._logger.update_metadata(asdict(state))

        self._stop_collectors()
        if self._logger is not None:
            self._logger.close()
            self._logger = None
        if self._metric_bus is not None:
            self._metric_bus.close(drain=True)
            self._metric_bus = None
        pygame.quit()


def _parse_key_value(user_input: str) -> tuple[str, str] | None:
    user_input = user_input.strip()
    if not user_input:
        return None
    if "=" not in user_input:
        return "note", user_input
    key, value = user_input.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return key, value


def _apply_config_weather(world, config) -> None:
    weather_config = getattr(config, "weather", None)
    if weather_config is None:
        return

    weather = world.get_weather()
    for key, value in weather_config.to_dict().items():
        if hasattr(weather, key):
            setattr(weather, key, value)
    world.set_weather(weather)
