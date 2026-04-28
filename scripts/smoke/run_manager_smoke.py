from __future__ import annotations

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.runtime.run_manager import RunManager


class FakeMap:
    name = "FakeTown"


class FakeWeather:
    cloudiness = 50.0
    precipitation = 0.0
    wetness = 0.0


class FakeWorld:
    def get_map(self) -> FakeMap:
        return FakeMap()

    def get_weather(self) -> FakeWeather:
        return FakeWeather()


class FakeVehicle:
    type_id = "vehicle.tesla.model3"


def main() -> None:
    rm = RunManager()
    fake_world = FakeWorld()
    fake_vehicle = FakeVehicle()

    state = rm.start_run(fake_world, fake_vehicle)
    assert state.status == "running"
    assert state.run_id
    assert state.started_at_utc
    assert state.map_name == "FakeTown"
    assert "vehicle." in (state.vehicle_blueprint or "")
    assert state.weather is not None
    assert "cloudiness" in state.weather

    stopped_once = rm.stop_run()
    assert stopped_once.status == "stopped"
    assert stopped_once.ended_at_utc

    run_id_before = stopped_once.run_id
    ended_before = stopped_once.ended_at_utc
    stopped_twice = rm.stop_run()
    assert stopped_twice.status == "stopped"
    assert stopped_twice.run_id == run_id_before
    assert stopped_twice.ended_at_utc == ended_before

    print("RunManager smoke OK")


if __name__ == "__main__":
    main()
