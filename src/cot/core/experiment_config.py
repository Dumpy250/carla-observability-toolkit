from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WeatherConfig:
    cloudiness: float | None = None
    precipitation: float | None = None
    precipitation_deposits: float | None = None
    wind_intensity: float | None = None
    fog_density: float | None = None
    wetness: float | None = None
    sun_altitude_angle: float | None = None

    def to_dict(self) -> dict[str, float]:
        values: dict[str, float] = {}
        for dataclass_field in fields(self):
            key = dataclass_field.name
            value = getattr(self, key)
            if value is not None:
                values[key] = value
        return values


@dataclass(slots=True)
class ExperimentConfig:
    experiment_id: str
    config_name: str | None = None
    seed: int | None = None
    duration_s: int | None = None
    tags: dict[str, str] = field(default_factory=dict)
    weather: WeatherConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "config_name": self.config_name,
            "seed": self.seed,
            "duration_s": self.duration_s,
            "tags": dict(self.tags),
            "weather": self.weather.to_dict() if self.weather is not None else None,
        }
        return payload


_WEATHER_FIELDS = {
    "cloudiness",
    "precipitation",
    "precipitation_deposits",
    "wind_intensity",
    "fog_density",
    "wetness",
    "sun_altitude_angle",
}

_EXPERIMENT_FIELDS = {
    "experiment_id",
    "config_name",
    "seed",
    "duration_s",
    "tags",
    "weather",
}


def _ensure_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _parse_optional_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"{field_name} must be a number")


def _parse_optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    raise ValueError(f"{field_name} must be an integer")


def _parse_optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"{field_name} must be a string")


def _parse_weather(raw_weather: Any) -> WeatherConfig:
    weather_obj = _ensure_object(raw_weather, "weather")
    unexpected = sorted(set(weather_obj) - _WEATHER_FIELDS)
    if unexpected:
        raise ValueError(f"weather contains unsupported fields: {unexpected}")

    return WeatherConfig(
        cloudiness=_parse_optional_float(weather_obj.get("cloudiness"), "weather.cloudiness"),
        precipitation=_parse_optional_float(
            weather_obj.get("precipitation"), "weather.precipitation"
        ),
        precipitation_deposits=_parse_optional_float(
            weather_obj.get("precipitation_deposits"), "weather.precipitation_deposits"
        ),
        wind_intensity=_parse_optional_float(
            weather_obj.get("wind_intensity"), "weather.wind_intensity"
        ),
        fog_density=_parse_optional_float(weather_obj.get("fog_density"), "weather.fog_density"),
        wetness=_parse_optional_float(weather_obj.get("wetness"), "weather.wetness"),
        sun_altitude_angle=_parse_optional_float(
            weather_obj.get("sun_altitude_angle"), "weather.sun_altitude_angle"
        ),
    )


def _parse_tags(raw_tags: Any) -> dict[str, str]:
    tags_obj = _ensure_object(raw_tags, "tags")
    tags: dict[str, str] = {}
    for key, value in tags_obj.items():
        if not isinstance(key, str):
            raise ValueError("tags keys must be strings")
        if not isinstance(value, str):
            raise ValueError(f"tags['{key}'] must be a string")
        tags[key] = value
    return tags


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    if config_path.suffix.lower() != ".json":
        raise ValueError(f"Only JSON experiment config files are supported: {config_path}")

    with config_path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    payload_obj = _ensure_object(payload, "experiment config")
    unexpected = sorted(set(payload_obj) - _EXPERIMENT_FIELDS)
    if unexpected:
        raise ValueError(f"experiment config contains unsupported fields: {unexpected}")

    experiment_id = payload_obj.get("experiment_id")
    if not isinstance(experiment_id, str) or experiment_id.strip() == "":
        raise ValueError("experiment_id is required and must be a non-empty string")

    tags = _parse_tags(payload_obj["tags"]) if "tags" in payload_obj else {}
    weather = _parse_weather(payload_obj["weather"]) if "weather" in payload_obj else None

    return ExperimentConfig(
        experiment_id=experiment_id,
        config_name=_parse_optional_str(payload_obj.get("config_name"), "config_name"),
        seed=_parse_optional_int(payload_obj.get("seed"), "seed"),
        duration_s=_parse_optional_int(payload_obj.get("duration_s"), "duration_s"),
        tags=tags,
        weather=weather,
    )
