from __future__ import annotations

from typing import Any

from mcp_tools.prometheus_mcp import PrometheusMCP

_prometheus: PrometheusMCP | None = None


def init_prometheus(base_url: str, thresholds_path: str = "config/thresholds.yaml") -> None:
    """Initialize the Prometheus MCP client."""
    global _prometheus
    _prometheus = PrometheusMCP(base_url, thresholds_path)


def get_active_alerts() -> list[dict[str, Any]]:
    """STEP 1: Get all active Prometheus threshold breaches.

    Always call this first in every monitoring cycle.
    Returns list of dicts with keys: device, metric, value,
    severity, source_system. Empty list means no active alerts.
    """
    if _prometheus is None:
        return []
    alerts = _prometheus.get_threshold_breaches()
    return [a.to_dict() for a in alerts]


def check_service_health(device: str) -> bool:
    """STEP 6b: Check if device is healthy in Prometheus.

    Call for each open incident's root_cause_device.
    Returns True if healthy (no breaches) — proceed to close.
    Returns False if still unhealthy — keep incident open.
    """
    if _prometheus is None:
        return True
    return _prometheus.get_service_health(device)
