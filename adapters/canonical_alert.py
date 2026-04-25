"""Core dataclasses shared across NOC Whisperer agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


_VALID_DOMAINS: set[str] = {"infrastructure", "service_mesh", "application"}
_VALID_SEVERITIES: set[str] = {"critical", "major", "minor", "warning"}
_VALID_STATUSES: set[str] = {"open", "resolved"}


@dataclass
class CanonicalAlert:
    """Normalized alert payload used across all agents."""

    alert_id: str
    """UUID generated at normalization time."""
    timestamp: datetime
    """UTC timestamp normalized from source format."""
    domain: str
    """Alert domain: infrastructure, service_mesh, or application."""
    severity: str
    """Alert severity: critical, major, minor, or warning."""
    device: str
    """Normalized device identifier."""
    metric: str
    """Measured metric name."""
    message: str
    """Human-readable alert message."""
    source_system: str
    """Origin system: jaeger, prometheus, node_exporter, or synthetic."""
    value: float
    """Raw metric value."""
    threshold: float
    """Threshold breached by the raw metric."""
    confidence: float
    """Normalizer confidence score from 0.0 to 1.0."""
    raw_payload: Dict[str, Any]
    """Original payload retained for auditing."""

    def __post_init__(self) -> None:
        """Validate canonical alert domain and severity values."""
        if self.domain not in _VALID_DOMAINS:
            raise ValueError(f"Invalid domain '{self.domain}'. Expected one of {_VALID_DOMAINS}.")
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}'. Expected one of {_VALID_SEVERITIES}."
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this alert to a JSON-safe dictionary."""
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat(),
            "domain": self.domain,
            "severity": self.severity,
            "device": self.device,
            "metric": self.metric,
            "message": self.message,
            "source_system": self.source_system,
            "value": self.value,
            "threshold": self.threshold,
            "confidence": self.confidence,
            "raw_payload": self.raw_payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CanonicalAlert:
        """Create a canonical alert instance from a dictionary."""
        return cls(
            alert_id=str(data["alert_id"]),
            timestamp=datetime.fromisoformat(str(data["timestamp"])),
            domain=str(data["domain"]),
            severity=str(data["severity"]),
            device=str(data["device"]),
            metric=str(data["metric"]),
            message=str(data["message"]),
            source_system=str(data["source_system"]),
            value=float(data["value"]),
            threshold=float(data["threshold"]),
            confidence=float(data["confidence"]),
            raw_payload=dict(data["raw_payload"]),
        )


@dataclass
class TriageDecision:
    """Routing decision that links an alert to an incident action."""

    alert: CanonicalAlert
    """Canonical alert being routed."""
    action: str
    """Routing action: append or new."""
    incident_id: Optional[str]
    """Target incident id when appending; otherwise None."""

    def __post_init__(self) -> None:
        """Validate triage action values."""
        if self.action not in {"append", "new"}:
            raise ValueError("action must be either 'append' or 'new'.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this triage decision to a dictionary."""
        return {
            "alert": self.alert.to_dict(),
            "action": self.action,
            "incident_id": self.incident_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TriageDecision:
        """Create a triage decision from a dictionary."""
        return cls(
            alert=CanonicalAlert.from_dict(dict(data["alert"])),
            action=str(data["action"]),
            incident_id=None if data.get("incident_id") is None else str(data["incident_id"]),
        )


@dataclass
class Incident:
    """Unified incident view produced by correlation and reconciliation."""

    incident_id: str
    """Incident UUID."""
    created_at: datetime
    """Incident creation timestamp."""
    updated_at: datetime
    """Most recent incident update timestamp."""
    status: str
    """Incident status: open or resolved."""
    root_cause_device: str
    """Likely root-cause device from correlation."""
    incident_title: str
    """Single-line dashboard title."""
    affected_services: List[str]
    """Services impacted by this incident."""
    confidence: float
    """Correlation confidence score from 0.0 to 1.0."""
    recommended_action: str
    """Most important recommended operator action."""
    alerts: List[CanonicalAlert]
    """Full alert history for this incident."""
    preliminary_advisory_sent: bool = False
    """Whether preliminary advisory has been sent."""
    confirmed_advisory_sent: bool = False
    """Whether confirmed advisory has been sent."""

    def __post_init__(self) -> None:
        """Validate incident status values."""
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"Invalid status '{self.status}'. Expected one of {_VALID_STATUSES}.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this incident to a dictionary."""
        return {
            "incident_id": self.incident_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "root_cause_device": self.root_cause_device,
            "incident_title": self.incident_title,
            "affected_services": self.affected_services,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action,
            "alerts": [alert.to_dict() for alert in self.alerts],
            "preliminary_advisory_sent": self.preliminary_advisory_sent,
            "confirmed_advisory_sent": self.confirmed_advisory_sent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Incident:
        """Create an incident from a dictionary."""
        return cls(
            incident_id=str(data["incident_id"]),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
            status=str(data["status"]),
            root_cause_device=str(data["root_cause_device"]),
            incident_title=str(data["incident_title"]),
            affected_services=[str(service) for service in data["affected_services"]],
            confidence=float(data["confidence"]),
            recommended_action=str(data["recommended_action"]),
            alerts=[CanonicalAlert.from_dict(dict(alert)) for alert in data["alerts"]],
            preliminary_advisory_sent=bool(data.get("preliminary_advisory_sent", False)),
            confirmed_advisory_sent=bool(data.get("confirmed_advisory_sent", False)),
        )
