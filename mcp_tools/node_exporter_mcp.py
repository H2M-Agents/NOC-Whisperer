"""Node Exporter MCP tool for infrastructure host alerts via Prometheus."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
import yaml

from adapters.canonical_alert import CanonicalAlert


class NodeExporterMCP:
    """MCP wrapper for node exporter metrics scraped by Prometheus."""

    def __init__(self, prometheus_base_url: str, thresholds_path: str = "config/thresholds.yaml") -> None:
        """Store Prometheus endpoint and load thresholds configuration."""
        self.prometheus_base_url = prometheus_base_url.rstrip("/")
        self.thresholds: Dict[str, Any] = {}
        try:
            with open(thresholds_path, "r", encoding="utf-8") as file:
                loaded = yaml.safe_load(file) or {}
                if isinstance(loaded, dict):
                    self.thresholds = loaded
        except Exception:
            self.thresholds = {}

    def get_host_alerts(self) -> List[CanonicalAlert]:
        """Query host-level metrics and convert threshold breaches to canonical alerts."""
        queries = [
            (
                "cpu_utilization_percent",
                '100-(avg(rate(node_cpu_seconds_total{mode="idle"}[2m]))*100) > 90',
            ),
            ("memory_available_mb", "node_memory_MemAvailable_bytes/1024/1024 < 524288000/1024/1024"),
            (
                "disk_used_percent",
                "(node_filesystem_size_bytes-node_filesystem_free_bytes)/node_filesystem_size_bytes*100 > 90",
            ),
        ]

        alerts: List[CanonicalAlert] = []
        for metric_name, promql in queries:
            response = self._query(promql)
            if response.get("status") != "success":
                continue
            result = response.get("data", {}).get("result", [])
            if not isinstance(result, list):
                continue
            for metric_result in result:
                try:
                    alerts.append(self._to_canonical(metric_result, metric_name))
                except Exception:
                    continue
        return alerts

    def health_check(self) -> bool:
        """Return True when Prometheus reports node exporter as up."""
        response = self._query('up{job="node"} == 1')
        if response.get("status") != "success":
            return False
        result = response.get("data", {}).get("result", [])
        return isinstance(result, list) and len(result) > 0

    def _query(self, promql: str) -> dict:
        """Execute an instant query against Prometheus and return payload dict."""
        try:
            response = requests.get(
                f"{self.prometheus_base_url}/api/v1/query",
                params={"query": promql},
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _to_canonical(self, metric_result: dict, metric_name: str) -> CanonicalAlert:
        """Convert a Prometheus result vector into a canonical infrastructure alert."""
        metric = metric_result.get("metric", {})
        raw_value = metric_result.get("value", [None, 0])

        device = str(
            metric.get("instance")
            or metric.get("nodename")
            or metric.get("job")
            or "unknown-host"
        )
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

        threshold, severity = self._threshold_and_severity(metric_name, value)
        message = f"Node Exporter threshold breach on {device}: {metric_name}={value:.2f} (threshold={threshold})"

        return CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=timestamp,
            domain="infrastructure",
            severity=severity,
            device=device,
            metric=metric_name,
            message=message,
            source_system="node_exporter",
            value=value,
            threshold=threshold,
            confidence=0.90,
            raw_payload=metric_result,
        )

    def _threshold_and_severity(self, metric_name: str, value: float) -> tuple[float, str]:
        """Get threshold and severity from config for the given metric value."""
        compute = self.thresholds.get("compute", {})
        storage = self.thresholds.get("storage", {})

        if metric_name == "cpu_utilization_percent":
            config = compute.get("cpu_utilization_percent", {})
            critical = float(config.get("critical", 90.0))
            major = float(config.get("major", 80.0))
            minor = float(config.get("minor", 70.0))
        elif metric_name == "memory_available_mb":
            config = compute.get("memory_available_mb", {})
            critical = float(config.get("critical", 500))
            major = float(config.get("major", 1000))
            minor = float(config.get("minor", 2000))
            if value <= critical:
                return critical, "critical"
            if value <= major:
                return major, "major"
            return minor, "minor"
        else:
            config = storage.get("disk_used_percent", {})
            critical = float(config.get("critical", 90.0))
            major = float(config.get("major", 80.0))
            minor = float(config.get("minor", 70.0))

        if value >= critical:
            return critical, "critical"
        if value >= major:
            return major, "major"
        return minor, "minor"
