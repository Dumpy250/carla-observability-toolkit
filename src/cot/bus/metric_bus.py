from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class TelemetryMessage:
    topic: str
    run_id: Optional[str]
    frame: Optional[int]
    sim_time_s: Optional[float]
    payload: dict
    wall_time_utc_s: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Subscription:
    subscription_id: int
    topic_prefix: str
    handler: Callable[[TelemetryMessage], None]


class MetricBus:
    """In-process telemetry pub/sub bus with prefix topic matching."""

    _STOP = object()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscriptions: Dict[int, Subscription] = {}
        self._next_subscription_id = 1
        self._queue: "queue.Queue[object]" = queue.Queue()
        self._closed = False
        self._drain_on_close = True
        self._worker = threading.Thread(target=self._dispatch_loop, name="MetricBusWorker", daemon=True)
        self._worker.start()

    def subscribe(self, topic_prefix: str, handler: Callable[[TelemetryMessage], None]) -> Subscription:
        if not topic_prefix:
            raise ValueError("topic_prefix must be non-empty")
        with self._lock:
            if self._closed:
                raise RuntimeError("MetricBus is closed")
            subscription = Subscription(
                subscription_id=self._next_subscription_id,
                topic_prefix=topic_prefix,
                handler=handler,
            )
            self._subscriptions[subscription.subscription_id] = subscription
            self._next_subscription_id += 1
            return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        with self._lock:
            self._subscriptions.pop(subscription.subscription_id, None)

    def publish(self, message: TelemetryMessage) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("MetricBus is closed")
        self._queue.put(message)

    def close(self, drain: bool = True) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._drain_on_close = drain
        self._queue.put(self._STOP)
        self._worker.join()

    def _dispatch_loop(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is self._STOP:
                    return
                with self._lock:
                    if self._closed and not self._drain_on_close:
                        return
                message = item
                subscriptions = self._matching_subscriptions(message.topic)
                for subscription in subscriptions:
                    try:
                        subscription.handler(message)
                    except Exception:
                        logging.exception(
                            "MetricBus subscriber failed (prefix=%s, topic=%s)",
                            subscription.topic_prefix,
                            message.topic,
                        )
            finally:
                self._queue.task_done()

    def _matching_subscriptions(self, topic: str) -> list[Subscription]:
        with self._lock:
            return [
                subscription
                for subscription in self._subscriptions.values()
                if topic.startswith(subscription.topic_prefix)
            ]
