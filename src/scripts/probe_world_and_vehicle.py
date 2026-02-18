from cot.carla_client import make_client
import math


def vec_mag(v) -> float:
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def get_or_spawn_vehicle(world):
    """Return an existing vehicle if present; otherwise spawn one safely and wait for stabilization."""
    vehicles = world.get_actors().filter("vehicle.*")
    if len(vehicles) > 0:
        return vehicles[0], False  # (vehicle, spawned?)

    bp_lib = world.get_blueprint_library()

    preferred = bp_lib.filter("vehicle.tesla.model3")
    bp = preferred[0] if preferred else bp_lib.filter("vehicle.*")[0]

    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        raise RuntimeError("No spawn points available on this map.")

    for sp in spawn_points[:30]:
        v = world.try_spawn_actor(bp, sp)
        if v is None:
            continue

        # Let the simulator advance so the actor has a stable transform/physics state
        for _ in range(3):
            world.wait_for_tick()

        # Re-fetch to ensure we have the fully-registered actor
        v2 = world.get_actor(v.id)
        return (v2 if v2 is not None else v), True

    raise RuntimeError("Failed to spawn a vehicle (first 30 spawn points blocked).")


def main():
    client = make_client(timeout_s=10.0)
    world = client.get_world()

    snap = world.get_snapshot()
    print("frame:", snap.frame)
    print("elapsed_seconds:", snap.timestamp.elapsed_seconds)
    print("delta_seconds:", snap.timestamp.delta_seconds)

    settings = world.get_settings()
    print("sync:", settings.synchronous_mode)
    print("fixed_dt:", settings.fixed_delta_seconds)
    print("no_rendering:", settings.no_rendering_mode)

    vehicles = world.get_actors().filter("vehicle.*")
    print("vehicles(before):", len(vehicles))

    v, spawned = get_or_spawn_vehicle(world)
    print("vehicle.selected:", v.id, v.type_id, "| spawned:" , spawned)
    print("vehicle.is_alive:", v.is_alive, "is_active:", v.is_active, "state:", v.actor_state)
    print("vehicle.bounding_box.extent:", v.bounding_box.extent.x, v.bounding_box.extent.y, v.bounding_box.extent.z)

    # Vehicle/Actor metrics
    t = v.get_transform()
    vel = v.get_velocity()
    acc = v.get_acceleration()
    ang = v.get_angular_velocity()
    ctrl = v.get_control()

    print("loc:", t.location.x, t.location.y, t.location.z)
    print("rot:", t.rotation.pitch, t.rotation.yaw, t.rotation.roll)
    print("speed(m/s):", vec_mag(vel))
    print("acc(m/s^2):", vec_mag(acc))
    print("ang(rad/s):", vec_mag(ang))
    print("control:", ctrl.throttle, ctrl.steer, ctrl.brake)
    print("vel_vec(m/s):", vel.x, vel.y, vel.z)
    print("acc_vec(m/s^2):", acc.x, acc.y, acc.z)
    print("ang_vec(rad/s):", ang.x, ang.y, ang.z)

    # Traffic light related
    is_at = v.is_at_traffic_light()
    print("is_at_traffic_light:", is_at)
    if is_at:
        state = v.get_traffic_light_state()
        name = getattr(state, "name", None)
        print("traffic_light_state:", name if name else state)

if __name__ == "__main__":
    main()