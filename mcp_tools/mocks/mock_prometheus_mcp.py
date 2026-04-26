"""Mock Prometheus MCP used for deterministic tests."""

from __future__ import annotations

from typing import List, Optional

from adapters.canonical_alert import CanonicalAlert


class MockPrometheusMCP:
    """Mock implementation of Prometheus MCP interface."""

    def __init__(self, scenario_alerts: Optional[List[CanonicalAlert]] = None) -> None:
        """Initialize mock with optional pre-seeded canonical alerts."""
        self.scenario_alerts = scenario_alerts or []

    def get_threshold_breaches(self) -> List[CanonicalAlert]:
        """Return seeded scenario alerts for threshold breaches."""
        return self.scenario_alerts

    def query(self, promql: str) -> dict:
        """Return a stable mock success payload for any PromQL query."""
        _ = promql
        return {"status": "success", "data": {"result": []}}

    def get_alerts_since(self, seconds: int = 30) -> List[CanonicalAlert]:
        """Return seeded scenario alerts for the recent window."""
        _ = seconds
        return self.scenario_alerts

    def health_check(self) -> bool:
        """Return True to indicate mock is always healthy."""
        return True
