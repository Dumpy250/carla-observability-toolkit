"""Telemetry collector package."""

from cot.collectors.event_collector import EventCollector
from cot.collectors.vehicle_metrics_collector import VehicleMetricsCollector

__all__ = ["EventCollector", "VehicleMetricsCollector"]
