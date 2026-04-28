"""CARLA integration package."""

from cot.carla.client import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_TIMEOUT_S, make_client
from cot.carla.vehicle_spawner import VehicleSpawner

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT_S",
    "VehicleSpawner",
    "make_client",
]
