from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from adapters.canonical_alert import CanonicalAlert
from agents.triage_agent import TriageAgent

_triage: TriageAgent | None = None


def init_triage(topology_path: str = "topology/otel_demo_graph.json") -> None:
    """Initialize the TriageAgent."""
    global _triage
    from mcp_tools.topology_mcp import TopologyMCP

    topology = TopologyMCP(topology_path)
    _triage = TriageAgent(topology_mcp=topology)


def route_alert(
    alert_id: str,
    device: str,
    domain: str,
    severity: str,
    metric: str,
    value: float,
    confidence: float,
    source_system: str,
    message: str = "",
) -> dict[str, Any]:
    """STEP 3: Route a normalized alert to new or existing incident.

    Call once for EACH normalized alert from normalize_alert().
    Returns dict with: action (new/append), incident_id.
    """
    if _triage is None:
        return {}
    alert = CanonicalAlert(
        alert_id=alert_id,
        timestamp=datetime.now(timezone.utc),
        domain=domain,
        severity=severity,
        device=device,
        metric=metric,
        message=message,
        source_system=source_system,
        value=value,
        threshold=0.0,
        confidence=confidence,
        raw_payload={},
    )
    decision = _triage.route(alert)
    return decision.to_dict()
