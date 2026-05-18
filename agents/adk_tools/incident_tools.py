from __future__ import annotations

from typing import Any

_store: Any = None
_dashboard: Any = None


def init_incident_store(store: Any) -> None:
    """Initialize the incident store."""
    global _store
    _store = store


def init_dashboard(dashboard: Any) -> None:
    """Wire NOCDashboard so close_incident() can remove resolved incidents from the board."""
    global _dashboard
    _dashboard = dashboard


def check_open_incidents() -> list[dict[str, Any]]:
    """STEP 6a: Get all currently open incidents.

    Call this to check which incidents need health verification.
    Returns list of dicts with: incident_id, root_cause_device,
    confidence, alert_count, status.
    """
    if _store is None:
        return []
    incidents = _store.get_open_incidents()
    return [
        {
            "incident_id": i.incident_id,
            "root_cause_device": i.root_cause_device,
            "affected_services": list(i.affected_services),
            "confidence": i.confidence,
            "alert_count": len(i.alerts),
            "status": i.status,
            "preliminary_advisory_sent": i.preliminary_advisory_sent,
            "confirmed_advisory_sent": i.confirmed_advisory_sent,
        }
        for i in incidents
    ]


def close_incident(incident_id: str) -> dict[str, Any]:
    """STEP 6c: Mark incident as resolved in the store.

    Call only when check_service_health() returns True.
    Then immediately call generate_advisory(advisory_type='resolution').
    Returns dict with: incident_id, status.
    """
    if _store is None:
        return {}
    incident = _store.get_incident(incident_id)
    if incident is None:
        return {"error": f"Incident {incident_id} not found"}
    incident.status = "resolved"
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_store.upsert(incident))
    except RuntimeError:
        asyncio.run(_store.upsert(incident))
    if _dashboard is not None:
        _dashboard.update_incident_board(incident)
    return {"incident_id": incident_id, "status": "resolved"}
