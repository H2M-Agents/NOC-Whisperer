"""Correlation agent — clusters alerts and synthesizes incidents via DSPy correlators."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Protocol, runtime_checkable

from adapters.canonical_alert import CanonicalAlert, Incident, TriageDecision

_DEFAULT_CONFIDENCE = 0.5


@runtime_checkable
class _TopologyMCPPort(Protocol):
    """Topology operations needed for correlation."""

    def get_topology_context(self, devices: List[str]) -> dict:
        """Return dependency context for the given devices."""
        ...


@runtime_checkable
class _IncidentStorePort(Protocol):
    """Incident store operations used when appending to an existing incident."""

    def get_open_incidents(self) -> List[Incident]:
        """Return incidents that are still open."""
        ...


def _parse_confidence_field(raw: str) -> float:
    """Extract leading numeric confidence from correlator output text."""
    match = re.match(r"^\s*([0-9]*\.?[0-9]+)", raw.strip())
    if match:
        return max(0.0, min(1.0, float(match.group(1))))
    return _DEFAULT_CONFIDENCE


def _split_affected_services(raw: str) -> List[str]:
    """Split comma-separated affected services into a clean list."""
    return [part.strip() for part in raw.split(",") if part.strip()]


class CorrelationAgent:
    """Build incidents from triage decisions using topology context and a correlator."""

    def __init__(
        self,
        topology_mcp: _TopologyMCPPort,
        incident_store: _IncidentStorePort,
        window_seconds: int = 180,
        mode: str = "development",
    ) -> None:
        """Attach topology + store, sliding window size, and correlator mode."""
        self.topology = topology_mcp
        self.store = incident_store
        self.window = window_seconds
        self.alert_buffer: List[CanonicalAlert] = []
        self.correlator = self._load_correlator(mode)

    def correlate(self, decision: TriageDecision) -> Incident:
        """Turn a triage decision into a correlated incident."""
        self._prune_buffer(decision.alert.timestamp)

        existing: Optional[Incident] = None
        if decision.action == "append" and decision.incident_id:
            existing = self._find_incident(decision.incident_id)

        cluster = self._assemble_cluster(decision, existing)

        if decision.action == "append" and existing is not None:
            incident_id = existing.incident_id
            created_at = existing.created_at
        else:
            incident_id = str(uuid.uuid4())
            created_at = decision.alert.timestamp

        self.alert_buffer.append(decision.alert)

        devices = [alert.device for alert in cluster]
        topology_context = self.topology.get_topology_context(devices)
        serial_cluster = [alert.to_dict() for alert in cluster]
        result = self.correlator.predict(serial_cluster, topology_context)

        confidence = _parse_confidence_field(str(result.get("confidence", "")))
        affected = _split_affected_services(str(result.get("affected_services", "")))

        return Incident(
            incident_id=incident_id,
            created_at=_ensure_utc(created_at),
            updated_at=_ensure_utc(decision.alert.timestamp),
            status="open",
            root_cause_device=str(result.get("root_cause_device", "unknown-device")),
            incident_title=str(result.get("incident_title", "Untitled incident")),
            affected_services=affected if affected else ["unknown"],
            confidence=confidence,
            recommended_action=str(result.get("recommended_action", "Investigate alerts")),
            alerts=cluster,
            preliminary_advisory_sent=(
                existing.preliminary_advisory_sent
                if decision.action == "append" and existing is not None
                else False
            ),
            confirmed_advisory_sent=(
                existing.confirmed_advisory_sent
                if decision.action == "append" and existing is not None
                else False
            ),
        )

    def _assemble_cluster(
        self, decision: TriageDecision, existing: Optional[Incident]
    ) -> List[CanonicalAlert]:
        """Return alerts for correlation (append vs sliding window)."""
        if decision.action == "append" and existing is not None:
            return list(existing.alerts) + [decision.alert]
        return list(self.alert_buffer) + [decision.alert]

    def _prune_buffer(self, reference_time: datetime) -> None:
        """Drop alerts outside the sliding time window."""
        cutoff = reference_time - timedelta(seconds=self.window)
        self.alert_buffer = [alert for alert in self.alert_buffer if alert.timestamp >= cutoff]

    def _find_incident(self, incident_id: str) -> Optional[Incident]:
        """Locate an open incident by id."""
        for incident in self.store.get_open_incidents():
            if incident.incident_id == incident_id:
                return incident
        return None

    def _load_correlator(self, mode: str) -> Any:
        """Resolve correlator implementation for development vs production."""
        from dspy_programs.alerts_to_incident import BaselineCorrelator, DSPyCorrelator

        if mode == "production":
            return DSPyCorrelator()
        return BaselineCorrelator()


def _ensure_utc(value: datetime) -> datetime:
    """Normalize datetimes to UTC-aware for consistent incident records."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
