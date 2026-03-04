from __future__ import annotations

from typing import Optional

import carla


class VehicleSpawner:
    """Helper for finding or spawning a deterministic vehicle actor."""

    def __init__(self, world: carla.World) -> None:
        self.world = world

    def find_first_vehicle(self) -> Optional[carla.Vehicle]:
        """Return the first vehicle actor in the world, if one exists."""
        actors = self.world.get_actors().filter("vehicle.*")
        return actors[0] if actors else None

    def ensure_vehicle(self) -> Optional[carla.Vehicle]:
        """Return an existing vehicle or spawn one deterministically.

        Returns `None` when no compatible blueprint exists, no spawn points are
        available, or actor spawning fails.
        """
        existing = self.find_first_vehicle()
        if existing is not None:
            return existing

        blueprint_library = self.world.get_blueprint_library()
        vehicle_blueprints = blueprint_library.filter("vehicle.*")
        if not vehicle_blueprints:
            return None

        blueprint = next(
            (bp for bp in vehicle_blueprints if bp.id == "vehicle.tesla.model3"),
            vehicle_blueprints[0],
        )

        spawn_points = self.world.get_map().get_spawn_points()
        if not spawn_points:
            return None

        spawned_actor = self.world.try_spawn_actor(blueprint, spawn_points[0])
        if spawned_actor is None:
            return None

        self.world.wait_for_tick(1.0)
        return spawned_actor if isinstance(spawned_actor, carla.Vehicle) else None
