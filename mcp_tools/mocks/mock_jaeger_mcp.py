"""Mock Jaeger MCP for deterministic tests."""

from __future__ import annotations

from typing import List, Optional

from adapters.canonical_alert import CanonicalAlert


class MockJaegerMCP:
    """Mock interface-compatible Jaeger MCP."""

    def __init__(self, scenario_alerts: Optional[List[CanonicalAlert]] = None) -> None:
        """Initialize with optional pre-seeded scenario alerts."""
        self.scenario_alerts = scenario_alerts or []

    def get_error_spans(self, since_seconds: int = 30) -> List[CanonicalAlert]:
        """Return seeded error alerts."""
        _ = since_seconds
        return self.scenario_alerts

    def health_check(self) -> bool:
        """Always healthy in mock mode."""
        return True
