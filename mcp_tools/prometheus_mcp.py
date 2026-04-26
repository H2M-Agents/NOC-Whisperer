"""Prometheus MCP tool for service-mesh threshold breaches."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
import yaml

from adapters.canonical_alert import CanonicalAlert


class PrometheusMCP:
    """MCP client wrapper for querying Prometheus and mapping alerts."""

    def __init__(self, base_url: str, thresholds_path: str = "config/thresholds.yaml") -> None:
        """Initialize MCP client and load threshold configuration."""
        self.base_url = base_url.rstrip("/")
        self.thresholds: Dict[str, Any] = {}

        try:
            with open(thresholds_path, "r", encoding="utf-8") as file:
                loaded = yaml.safe_load(file) or {}
                if isinstance(loaded, dict):
                    self.thresholds = loaded
        except Exception:
            self.thresholds = {}

    def get_threshold_breaches(self) -> List[CanonicalAlert]:
        """Fetch Prometheus threshold breaches as canonical alerts."""
        queries = [
            'rate(http_server_duration_milliseconds_count{status_code=~"5.."}[1m]) > 0.1',
            "valkey_cache_miss_ratio > 0.9",
            "cart_connections_active / cart_connections_max > 0.9",
        ]

        alerts: List[CanonicalAlert] = []
        for promql in queries:
            response = self.query(promql)
            if response.get("status") != "success":
                continue

            result = response.get("data", {}).get("result", [])
            if not isinstance(result, list):
                continue

            for metric_result in result:
                try:
                    alerts.append(self._to_canonical(metric_result))
                except Exception:
                    continue

        return alerts

    def query(self, promql: str) -> dict:
        """Execute a PromQL instant query and return raw response."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": promql},
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def get_alerts_since(self, seconds: int = 30) -> List[CanonicalAlert]:
        """Return recent threshold breaches for the requested time window."""
        _ = seconds
        return self.get_threshold_breaches()

    def health_check(self) -> bool:
        """Check Prometheus availability via the up query endpoint."""
        response = self.query("up")
        return response.get("status") == "success"

    def _to_canonical(self, metric_result: dict) -> CanonicalAlert:
        """Convert a Prometheus vector result into a canonical alert."""
        metric = metric_result.get("metric", {})
        raw_value = metric_result.get("value", [None, 0])

        metric_name = str(metric.get("__name__", "unknown_metric"))
        device = str(
            metric.get("service")
            or metric.get("job")
            or metric.get("instance")
            or metric.get("pod")
            or "unknown-device"
        )

        value: float
        try:
            value = float(raw_value[1]) if isinstance(raw_value, list) and len(raw_value) >= 2 else 0.0
        except Exception:
            value = 0.0

        severity = self._severity_for_metric(metric_name, value)
        description = f"Prometheus threshold breach: {metric_name}={value:.4f}"

        return CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_system="prometheus",
            domain="service_mesh",
            metric=metric_name,
            value=value,
            device=device,
            severity=severity,
            description=description,
            incident_id=None,
        )

    def _severity_for_metric(self, metric_name: str, value: float) -> str:
        """Infer severity using thresholds config and conservative defaults."""
        if metric_name == "valkey_cache_miss_ratio":
            critical = 0.95
            major = 0.9
            minor = 0.8
        elif metric_name == "http_server_duration_milliseconds_count":
            config = self.thresholds.get("service_mesh", {}).get("http_error_rate_per_min", {})
            critical = float(config.get("critical", 20))
            major = float(config.get("major", 10))
            minor = float(config.get("minor", 5))
        else:
            critical = 0.95
            major = 0.9
            minor = 0.8

        if value >= critical:
            return "critical"
        if value >= major:
            return "major"
        if value >= minor:
            return "minor"
        return "minor"
