from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from adapters.canonical_alert import CanonicalAlert, TriageDecision
from agents.correlation_agent import CorrelationAgent

_correlation: CorrelationAgent | None = None


def init_correlation(store: Any, topology_path: str = "topology/otel_demo_graph.json") -> None:
    """Initialize the CorrelationAgent."""
    global _correlation
    from mcp_tools.topology_mcp import TopologyMCP

    topology = TopologyMCP(topology_path)
    _correlation = CorrelationAgent(topology_mcp=topology, incident_store=store)


def correlate_alert(
    alert_id: str,
    device: str,
    domain: str,
    severity: str,
    metric: str,
    value: float,
    confidence: float,
    source_system: str,
    action: str,
    incident_id: str | None,
    message: str = "",
) -> dict[str, Any]:
    """STEP 4: Correlate alert into incident using DSPy.

    Call once for EACH routed alert from route_alert().
    Returns dict with: incident_id, root_cause_device,
    affected_services, confidence, alert_count.
    """
    if _correlation is None:
        return {}

    # Duplicate guard: if the LLM passes action="new" but an
    # open incident already exists for this device, redirect
    # to append. get_open_incidents() only returns OPEN
    # incidents so there is no risk of merging resolved
    # incidents. Age is irrelevant — one open incident per
    # device is always the correct invariant.
    if action == "new":
        for _inc in _correlation.store.get_open_incidents():
            if _inc.root_cause_device == device:
                action = "append"
                incident_id = _inc.incident_id
                break

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
    decision = TriageDecision(
        alert=alert,
        action=action,
        incident_id=incident_id,
    )
    incident = _correlation.correlate(decision)
    try:
        _correlation.store._upsert_sync(incident)
    except Exception:
        pass
    return {
        "incident_id": incident.incident_id,
        "root_cause_device": incident.root_cause_device,
        "affected_services": list(incident.affected_services),
        "confidence": incident.confidence,
        "alert_count": len(incident.alerts),
        "status": incident.status,
        "preliminary_advisory_sent": incident.preliminary_advisory_sent,
        "confirmed_advisory_sent": incident.confirmed_advisory_sent,
    }
