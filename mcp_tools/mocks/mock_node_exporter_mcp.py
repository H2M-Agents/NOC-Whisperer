"""Mock Node Exporter MCP for deterministic tests."""

from __future__ import annotations

from typing import List, Optional

from adapters.canonical_alert import CanonicalAlert


class MockNodeExporterMCP:
    """Mock interface-compatible Node Exporter MCP."""

    def __init__(self, scenario_alerts: Optional[List[CanonicalAlert]] = None) -> None:
        """Initialize with optional pre-seeded alerts."""
        self.scenario_alerts = scenario_alerts or []

    def get_host_alerts(self) -> List[CanonicalAlert]:
        """Return seeded host alerts."""
        return self.scenario_alerts

    def health_check(self) -> bool:
        """Always healthy in mock mode."""
        return True
