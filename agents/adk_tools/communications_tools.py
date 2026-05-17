from __future__ import annotations

from typing import Any

from adapters.canonical_alert import Incident
from communications.communications_agent import CommunicationsAgent

_communications: CommunicationsAgent | None = None
_dashboard: Any = None


def init_communications() -> None:
    """Initialize the CommunicationsAgent."""
    global _communications
    _communications = CommunicationsAgent()


def init_dashboard(dashboard: Any) -> None:
    """Initialize dashboard reference for advisory updates."""
    global _dashboard
    _dashboard = dashboard


def generate_advisory(incident_id: str, advisory_type: str) -> str:
    """STEP 5 or STEP 6: Generate NOC advisory text.

    advisory_type must be one of: preliminary, confirmed, resolution.
    Call with 'confirmed' when confidence > 0.85 AND alert_count >= 2.
    Call with 'preliminary' when confidence > 0.50 AND alert_count >= 2.
    Call with 'resolution' when incident is being closed after healing.
    Returns advisory text string.
    """
    if _communications is None:
        return ""
    from orchestrator.incident_store import IncidentStore

    # get incident from store
    store = _get_store()
    if store is None:
        return ""
    incident = store.get_incident(incident_id)
    if incident is None:
        return ""
    advisory = _communications.generate(incident, advisory_type=advisory_type)
    if _dashboard is not None and advisory:
        _dashboard.update_advisory(advisory)
    return advisory


_store: Any = None


def _get_store() -> Any:
    return _store


def init_store(store: Any) -> None:
    """Initialize store reference for communications tools."""
    global _store
    _store = store
