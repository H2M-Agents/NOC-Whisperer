from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from adapters.canonical_alert import CanonicalAlert, TriageDecision
from agents.correlation_agent import CorrelationAgent

import logging as _log

_logger = _log.getLogger(__name__)

_INFRA_PAIRS: frozenset[frozenset[str]] = frozenset({
    frozenset({"cart", "valkey-cart"}),
})


def _devices_match(
    alert_device: str,
    stored_root_cause: str,
) -> bool:
    """True when alert device and stored
    root_cause_device are the same node or
    a known infrastructure alias pair.
    Intentionally narrow — does not use full
    topology are_related() to avoid merging
    cart alerts into frontend/ad noise incidents.
    """
    return (
        alert_device == stored_root_cause
        or frozenset({alert_device, stored_root_cause})
        in _INFRA_PAIRS
    )


_correlation: CorrelationAgent | None = None


def init_correlation(store: Any, topology_path: str = "topology/otel_demo_graph.json") -> None:
    """Initialize the CorrelationAgent."""
    global _correlation
    from mcp_tools.topology_mcp import TopologyMCP

    topology = TopologyMCP(topology_path)
    _correlation = CorrelationAgent(
        topology_mcp=topology,
        incident_store=store,
        mode="production",
    )


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

    # Always-run dedup guard.
    # Runs before TriageDecision regardless of
    # LLM action value.
    #
    # Priority:
    #   1. action=append + valid id in store
    #      → keep as-is (legitimate append)
    #   2. action=append + id missing/invalid
    #      → resolve by device match
    #   3. action=new + matching open incident
    #      → redirect to append
    #
    # _open cached once to avoid double DB read.
    _open = _correlation.store.get_open_incidents()

    _valid_id_in_store = (
        action == "append"
        and incident_id is not None
        and any(
            _inc.incident_id == incident_id
            for _inc in _open
        )
    )

    if not _valid_id_in_store:
        for _inc in _open:
            if _devices_match(
                device,
                _inc.root_cause_device,
            ):
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
    except Exception as _upsert_err:
        _logger.warning(
            "correlate_alert: upsert failed "
            "for incident %s: %s",
            incident.incident_id,
            _upsert_err,
        )
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
