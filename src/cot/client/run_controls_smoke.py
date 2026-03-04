from __future__ import annotations

import pathlib
import sys
from dataclasses import asdict

import pygame

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.carla_client import make_client
from cot.core.logger import RunLogger
from cot.core.metric_bus import MetricBus
from cot.core.run_manager import RunManager


def _pick_vehicle(world):
    vehicles = world.get_actors().filter("vehicle.*")
    if not vehicles:
        return None

    for vehicle in vehicles:
        if vehicle.attributes.get("role_name") == "hero":
            return vehicle
    return vehicles[0]


def _parse_key_value(user_input: str) -> tuple[str, str] | None:
    if "=" not in user_input:
        return None
    key, value = user_input.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return key, value


def main() -> None:
    pygame.init()
    pygame.display.set_caption("CARLA Run Controls")
    pygame.display.set_mode((420, 140))

    client = make_client()
    world = client.get_world()
    vehicle = _pick_vehicle(world)
    if vehicle is None:
        raise RuntimeError("No vehicle actors found in the CARLA world.")

    runs_root = PROJECT_ROOT / "runs"
    run_manager = RunManager()
    metric_bus: MetricBus | None = None
    logger: RunLogger | None = None

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
                    if run_manager.is_running():
                        continue
                    state = run_manager.start_run(world, vehicle)
                    metric_bus = MetricBus()
                    logger = RunLogger(metric_bus, run_id=state.run_id, output_root=runs_root)
                    logger.update_metadata(asdict(state))
                    print(f"RUN started id={state.run_id}")
                elif event.key == pygame.K_F6:
                    if not run_manager.is_running():
                        continue
                    state = run_manager.stop_run()
                    if logger is not None:
                        logger.update_metadata(asdict(state))
                        logger.close()
                        logger = None
                    if metric_bus is not None:
                        metric_bus.close(drain=True)
                        metric_bus = None
                    print(f"RUN stopped id={state.run_id}")
                elif event.key == pygame.K_F7:
                    if not run_manager.is_running():
                        continue
                    state = run_manager.abort_run(reason="keyboard_abort")
                    if logger is not None:
                        logger.update_metadata(asdict(state))
                        logger.close()
                        logger = None
                    if metric_bus is not None:
                        metric_bus.close(drain=True)
                        metric_bus = None
                    print(f"RUN aborted id={state.run_id} reason={state.abort_reason}")
                elif event.key == pygame.K_F8:
                    user_input = input("Enter tag key=value: ")
                    parsed = _parse_key_value(user_input)
                    if parsed is None:
                        continue
                    key, value = parsed
                    state = run_manager.tag(key, value)
                    if logger is not None:
                        logger.update_metadata(asdict(state))
                    print(f"TAG {key}={value}")
            pygame.time.wait(10)
    finally:
        if run_manager.is_running():
            state = run_manager.stop_run()
            if logger is not None:
                logger.update_metadata(asdict(state))

        if logger is not None:
            logger.close()
        if metric_bus is not None:
            metric_bus.close(drain=True)
        pygame.quit()


if __name__ == "__main__":
    main()
