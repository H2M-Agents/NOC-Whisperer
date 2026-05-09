"""Jaeger MCP tool for application error span retrieval."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from adapters.canonical_alert import CanonicalAlert


class JaegerMCP:
    """MCP wrapper for querying Jaeger traces and mapping to canonical alerts."""

    def __init__(self, base_url: str) -> None:
        """Store Jaeger base URL."""
        self.base_url = base_url.rstrip("/")

    def get_error_spans(self, since_seconds: int = 30) -> List[CanonicalAlert]:
        """Fetch error spans from Jaeger and convert to canonical alerts."""
        try:
            response = requests.get(
                f"{self.base_url}/jaeger/ui/api/traces",
                params={
                    "service": "all",
                    "tags": '{"error":"true"}',
                    "lookback": f"{since_seconds}s",
                    "limit": 100,
                },
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
            traces = payload.get("data", []) if isinstance(payload, dict) else []
        except Exception:
            return []

        alerts: List[CanonicalAlert] = []
        for trace in traces:
            process_map = trace.get("processes", {}) if isinstance(trace, dict) else {}
            for span in trace.get("spans", []) if isinstance(trace, dict) else []:
                if not isinstance(span, dict):
                    continue
                try:
                    alerts.append(self._span_to_canonical(span, process_map))
                except Exception:
                    continue
        return alerts

    def health_check(self) -> bool:
        """Return True when Jaeger services endpoint is reachable."""
        try:
            response = requests.get(f"{self.base_url}/jaeger/ui/api/services", timeout=5)
            response.raise_for_status()
            payload = response.json()
            return isinstance(payload, dict) and "data" in payload
        except Exception:
            return False

    def _span_to_canonical(self, span: dict, process_map: Dict[str, Any] | None = None) -> CanonicalAlert:
        """Convert a Jaeger span dict to CanonicalAlert."""
        tags = span.get("tags", [])
        tag_map = {
            str(tag.get("key", "")): tag.get("value")
            for tag in tags
            if isinstance(tag, dict)
        }

        process_id = span.get("processID")
        process_obj = (process_map or {}).get(process_id, {}) if process_id else {}
        device = str(
            process_obj.get("serviceName")
            or span.get("operationName")
            or "unknown-service"
        )

        metric = str(
            tag_map.get("error.type")
            or tag_map.get("error.kind")
            or span.get("operationName")
            or "jaeger_error_span"
        )

        message = str(
            tag_map.get("error.message")
            or tag_map.get("message")
            or f"Jaeger error span in {device}"
        )

        value = float(span.get("duration", 0))
        start_time = span.get("startTime")
        if isinstance(start_time, (int, float)):
            timestamp = datetime.fromtimestamp(float(start_time) / 1_000_000.0, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        return CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=timestamp,
            domain="application",
            severity="major",
            device=device,
            metric=metric,
            message=message,
            source_system="jaeger",
            value=value,
            threshold=0.0,
            confidence=0.90,
            raw_payload=span,
        )
