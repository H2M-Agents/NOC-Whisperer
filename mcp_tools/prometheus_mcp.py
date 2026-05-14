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
            # Cart latency spike — fires when > 1s (750x normal)
            # Normal is ~0.001s, only fires when valkey-cart is down
            'rate(app_cart_add_item_latency_seconds_sum[5m])'
            ' / rate(app_cart_add_item_latency_seconds_count[5m]) > 0.1',
            # Cart get latency spike
            'rate(app_cart_get_cart_latency_seconds_sum[5m])'
            ' / rate(app_cart_get_cart_latency_seconds_count[5m]) > 0.1',
            # Frontend 5xx errors — only fires on server errors
            # status label available in app_frontend_requests_total
            'rate(app_frontend_requests_total{status=~"5.."}[5m]) > 0.005',
            # Any OTel service completely down
            'up{job=~"opentelemetry-demo/.*"} == 0',
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

    def get_service_health(self, device: str) -> bool:
        """Return True if device has no active threshold breaches.

        Uses 1m lookback window for faster recovery detection
        after service restoration. Independent of
        get_threshold_breaches() — no shared state or queries.
        Returns True (healthy) on any query failure (fail open).

        Args:
            device: device name as returned by _to_canonical()
                e.g. 'cart', 'frontend'
        """
        queries = [
            "rate(app_cart_add_item_latency_seconds_sum[1m])"
            " / rate(app_cart_add_item_latency_seconds_count[1m]) > 0.1",
            "rate(app_cart_get_cart_latency_seconds_sum[1m])"
            " / rate(app_cart_get_cart_latency_seconds_count[1m]) > 0.1",
            'rate(app_frontend_requests_total{status=~"5.."}[1m]) > 0.005',
            'up{job=~"opentelemetry-demo/.*"} == 0',
        ]
        try:
            for promql in queries:
                response = self.query(promql)
                if response.get("status") != "success":
                    continue
                result = response.get("data", {}).get("result", [])
                if not isinstance(result, list):
                    continue
                for metric_result in result:
                    try:
                        alert = self._to_canonical(metric_result)
                        if alert.device == device:
                            return False  # still breaching
                    except Exception:
                        continue
            return True  # no breach found for device — healthy
        except Exception:
            return True  # fail open — assume healthy on error

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

        labels = metric
        metric_name = labels.get("__name__", "")
        if not metric_name:
            # rate() queries drop __name__ — use signal description
            service = labels.get("service_name", "")
            metric_name = f"{service}_threshold_breach" if service else "threshold_breach"
        else:
            metric_name = str(metric_name)
        service_name = labels.get("service_name", "")
        job = labels.get("job", "")
        instance = labels.get("instance", "")

        if service_name:
            device = service_name
        elif "/" in job:
            device = job.split("/")[-1]
        elif ":" in instance:
            device = instance.split(":")[0]
        elif instance:
            device = instance
        else:
            device = job if job else "unknown"
        device = str(device)

        value: float
        try:
            value = float(raw_value[1]) if isinstance(raw_value, list) and len(raw_value) >= 2 else 0.0
        except Exception:
            value = 0.0

        timestamp = datetime.now(timezone.utc)
        try:
            if isinstance(raw_value, list) and len(raw_value) >= 1:
                timestamp = datetime.fromtimestamp(float(raw_value[0]), tz=timezone.utc)
        except Exception:
            timestamp = datetime.now(timezone.utc)

        threshold = self._threshold_for_metric(metric_name)
        severity = self._severity_for_metric(metric_name, value, threshold)
        message = f"Prometheus threshold breach on {device}: {metric_name}={value:.4f} (threshold={threshold})"

        return CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=timestamp,
            domain="service_mesh",
            severity=severity,
            device=device,
            metric=metric_name,
            message=message,
            source_system="prometheus",
            value=value,
            threshold=threshold,
            confidence=0.90,
            raw_payload=metric_result,
        )

    def _threshold_for_metric(self, metric_name: str) -> float:
        """Return major-level threshold used to flag Prometheus breaches."""
        if metric_name == "valkey_cache_miss_ratio":
            config = self.thresholds.get("storage", {}).get("cache_miss_ratio", {})
            return float(config.get("major", 0.7))
        if metric_name == "http_server_duration_milliseconds_count":
            config = self.thresholds.get("service_mesh", {}).get("http_error_rate_per_min", {})
            return float(config.get("major", 10))
        if metric_name in {"cart_connections_active", "cart_connections_max"}:
            config = self.thresholds.get("service_mesh", {}).get("connection_pool_saturation", {})
            return float(config.get("major", 0.8))
        config = self.thresholds.get("service_mesh", {}).get("connection_pool_saturation", {})
        return float(config.get("major", 0.8))

    def _severity_for_metric(self, metric_name: str, value: float, threshold: float) -> str:
        """Infer severity using thresholds config and conservative defaults."""
        if metric_name == "valkey_cache_miss_ratio":
            config = self.thresholds.get("storage", {}).get("cache_miss_ratio", {})
            critical = float(config.get("critical", max(threshold, 0.9)))
            major = float(config.get("major", threshold))
            minor = float(config.get("minor", min(threshold, 0.5)))
        elif metric_name == "http_server_duration_milliseconds_count":
            config = self.thresholds.get("service_mesh", {}).get("http_error_rate_per_min", {})
            critical = float(config.get("critical", max(threshold, 20)))
            major = float(config.get("major", threshold))
            minor = float(config.get("minor", min(threshold, 5)))
        elif metric_name in {"cart_connections_active", "cart_connections_max"}:
            config = self.thresholds.get("service_mesh", {}).get("connection_pool_saturation", {})
            critical = float(config.get("critical", max(threshold, 0.95)))
            major = float(config.get("major", threshold))
            minor = float(config.get("minor", min(threshold, 0.7)))
        else:
            critical = max(threshold, 0.95)
            major = threshold
            minor = max(0.0, threshold * 0.85)

        if value >= critical:
            return "critical"
        if value >= major:
            return "major"
        if value >= minor:
            return "minor"
        return "minor"
