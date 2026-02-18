import carla

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 2000
DEFAULT_TIMEOUT_S = 10.0 # This is dependent on your server setup. With 2 seconds my client refused to connect.

def make_client(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout_s: float = DEFAULT_TIMEOUT_S) -> carla.Client:
    client = carla.Client(host, port)
    client.set_timeout(timeout_s)
    return client
