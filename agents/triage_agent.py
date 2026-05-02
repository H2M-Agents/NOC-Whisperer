"""Rule-based triage agent — routes alerts to new or existing incidents."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from adapters.canonical_alert import CanonicalAlert, Incident, TriageDecision


@runtime_checkable
class _TopologyMCPPort(Protocol):
    """Minimal topology surface required for triage."""

    def are_related(self, device_a: str, device_b: str) -> bool:
        """Return True if two devices are related in the service graph."""
        ...


@runtime_checkable
class _IncidentStorePort(Protocol):
    """Minimal incident store surface required for triage."""

    def get_open_incidents(self) -> List[Incident]:
        """Return all incidents that are currently open."""
        ...


class TriageAgent:
    """Rule-based router that assigns alerts to new or existing incidents."""

    def __init__(self, topology_mcp: _TopologyMCPPort, incident_store: _IncidentStorePort) -> None:
        """Wire topology access and shared incident state."""
        self.topology = topology_mcp
        self.store = incident_store
        self.time_window_seconds = 300

    def route(self, alert: CanonicalAlert) -> TriageDecision:
        """Return append vs new based on temporal and topological proximity."""
        for incident in self.store.get_open_incidents():
            if self._is_temporally_proximate(alert, incident) and self._is_topologically_proximate(
                alert, incident
            ):
                return TriageDecision(alert=alert, action="append", incident_id=incident.incident_id)
        return TriageDecision(alert=alert, action="new", incident_id=None)

    def _is_temporally_proximate(self, alert: CanonicalAlert, incident: Incident) -> bool:
        """True when the alert falls within the configured window of incident activity."""
        delta_seconds = abs((alert.timestamp - incident.updated_at).total_seconds())
        return delta_seconds <= float(self.time_window_seconds)

    def _is_topologically_proximate(self, alert: CanonicalAlert, incident: Incident) -> bool:
        """True when topology considers the alert device related to the incident root cause."""
        return self.topology.are_related(alert.device, incident.root_cause_device)
