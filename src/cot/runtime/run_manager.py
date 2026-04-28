from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from dataclasses import field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


@dataclass
class RunState:
    run_id: str
    status: str
    started_at_utc: Optional[str]
    ended_at_utc: Optional[str]
    map_name: Optional[str]
    weather: Optional[dict]
    vehicle_blueprint: Optional[str]
    experiment_id: Optional[str] = None
    config_name: Optional[str] = None
    seed: Optional[int] = None
    duration_s: Optional[int] = None
    tags: dict[str, str] = field(default_factory=dict)
    abort_reason: Optional[str] = None


class RunManager:
    """Tracks the lifecycle state for a CARLA simulation run."""

    def __init__(self) -> None:
        self._state = RunState(
            run_id="",
            status="idle",
            started_at_utc=None,
            ended_at_utc=None,
            map_name=None,
            weather=None,
            vehicle_blueprint=None,
            experiment_id=None,
            config_name=None,
            seed=None,
            duration_s=None,
            tags={},
            abort_reason=None,
        )

    def start_run(
            self,
            world,
            vehicle,
            run_id: Optional[str] = None,
            experiment_config: Optional[object] = None,
    ) -> RunState:
        resolved_run_id = run_id or str(uuid4())
        started_at_utc = datetime.now(timezone.utc).isoformat()
        config_tags = self._config_tags(experiment_config)

        self._state = RunState(
            run_id=resolved_run_id,
            status="running",
            started_at_utc=started_at_utc,
            ended_at_utc=None,
            map_name=self._map_name_if_available(world),
            weather=self._serialize_weather(world),
            vehicle_blueprint=getattr(vehicle, "type_id", None),
            experiment_id=self._optional_str_attr(experiment_config, "experiment_id"),
            config_name=self._optional_str_attr(experiment_config, "config_name"),
            seed=self._optional_int_attr(experiment_config, "seed"),
            duration_s=self._optional_int_attr(experiment_config, "duration_s"),
            tags=config_tags,
            abort_reason=None,
        )
        return self._state

    def stop_run(self) -> RunState:
        if self._state.status != "running":
            return self._state

        self._state.status = "stopped"
        if self._state.ended_at_utc is None:
            self._state.ended_at_utc = datetime.now(timezone.utc).isoformat()
        return self._state

    def abort_run(self, reason: str = "keyboard_abort") -> RunState:
        if self._state.status != "running":
            return self._state

        self._state.status = "aborted"
        if self._state.ended_at_utc is None:
            self._state.ended_at_utc = datetime.now(timezone.utc).isoformat()
        self._state.abort_reason = reason
        return self._state

    def tag(self, key: str, value: str) -> RunState:
        self._state.tags[key] = value
        return self._state

    def get_state(self) -> RunState:
        snapshot = replace(self._state)
        snapshot.tags = dict(self._state.tags)
        return snapshot

    def is_running(self) -> bool:
        return self._state.status == "running"

    def _config_tags(self, experiment_config: Optional[object]) -> dict[str, str]:
        if experiment_config is None:
            return {}

        raw_tags = getattr(experiment_config, "tags", None)
        if not isinstance(raw_tags, dict):
            return {}

        tags: dict[str, str] = {}
        for key, value in raw_tags.items():
            if isinstance(key, str) and isinstance(value, str):
                tags[key] = value
        return tags

    def _optional_str_attr(
            self, experiment_config: Optional[object], attribute_name: str
    ) -> Optional[str]:
        if experiment_config is None:
            return None
        value = getattr(experiment_config, attribute_name, None)
        return value if isinstance(value, str) else None

    def _optional_int_attr(
            self, experiment_config: Optional[object], attribute_name: str
    ) -> Optional[int]:
        if experiment_config is None:
            return None
        value = getattr(experiment_config, attribute_name, None)
        return value if isinstance(value, int) else None

    def _map_name_if_available(self, world) -> Optional[str]:
        if world is None:
            return None
        try:
            world_map = world.get_map()
        except Exception:
            return None
        return getattr(world_map, "name", None)

    def _serialize_weather(self, world) -> Optional[dict]:
        if world is None:
            return None
        try:
            weather = world.get_weather()
        except Exception:
            return None

        weather_dict: dict = {}
        for name in dir(weather):
            if name.startswith("_"):
                continue
            value = getattr(weather, name)
            if isinstance(value, (bool, int, float)):
                weather_dict[name] = value
        return weather_dict
