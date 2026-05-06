from __future__ import annotations

import pathlib
import sys

import pygame

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cot.carla.client import make_client
from cot.client.run_control_app import RunControlApp

DASHBOARD_WINDOW_SIZE = (620, 470)


def _pick_vehicle(world):
    vehicles = world.get_actors().filter("vehicle.*")
    if not vehicles:
        return None

    for vehicle in vehicles:
        if vehicle.attributes.get("role_name") == "hero":
            return vehicle
    return vehicles[0]


def main() -> None:
    pygame.init()
    pygame.display.set_caption("CARLA Run Controls")
    screen = pygame.display.set_mode(DASHBOARD_WINDOW_SIZE)
    title_font = pygame.font.Font(None, 28)
    section_font = pygame.font.Font(None, 24)
    label_font = pygame.font.Font(None, 20)
    value_font = pygame.font.Font(None, 21)
    metric_font = pygame.font.Font(None, 26)
    speed_metric_font = pygame.font.Font(None, 30)
    clock = pygame.time.Clock()

    try:
        client = make_client()
        world = client.get_world()
    except Exception:
        print("ERROR: Could not reach CARLA at localhost:2000.")
        print("Start the CARLA server first.")
        print("Then run manual_control.py (or spawn a vehicle), and rerun:")
        print("python src/cot/client/run_controls_smoke.py")
        pygame.quit()
        raise SystemExit(1)

    vehicle = _pick_vehicle(world)
    if vehicle is None:
        print("ERROR: Connected to CARLA, but no vehicle actors were found.")
        print("Start manual_control.py (or spawn a vehicle) first, then rerun:")
        print("python src/cot/client/run_controls_smoke.py")
        pygame.quit()
        raise SystemExit(1)

    app = RunControlApp(
        world=world,
        vehicle=vehicle,
        screen=screen,
        title_font=title_font,
        section_font=section_font,
        label_font=label_font,
        value_font=value_font,
        metric_font=metric_font,
        speed_metric_font=speed_metric_font,
        clock=clock,
        runs_root=PROJECT_ROOT / "runs",
        experiment_config_path=PROJECT_ROOT / "configs" / "experiment_v1.json",
    )
    app.run()


if __name__ == "__main__":
    main()
