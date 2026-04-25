"""Pytest unit tests for adapters.canonical_alert."""

from datetime import datetime

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident, TriageDecision


def _build_valid_alert() -> CanonicalAlert:
    """Create a valid CanonicalAlert for reuse in tests."""
    return CanonicalAlert(
        alert_id="alert-1",
        timestamp=datetime.now(),
        domain="infrastructure",
        severity="critical",
        device="redis",
        metric="cpu_usage_percent",
        message="CPU high",
        source_system="prometheus",
        value=95.0,
        threshold=90.0,
        confidence=0.93,
        raw_payload={"sample": "data"},
    )


def test_import() -> None:
    """Assert core classes are importable."""
    assert CanonicalAlert is not None
    assert TriageDecision is not None
    assert Incident is not None


def test_canonical_alert_valid_creation() -> None:
    """Create a valid CanonicalAlert and assert all fields."""
    timestamp = datetime.now()
    alert = CanonicalAlert(
        alert_id="alert-valid",
        timestamp=timestamp,
        domain="infrastructure",
        severity="major",
        device="cartservice",
        metric="memory_available_mb",
        message="Memory low",
        source_system="node_exporter",
        value=450.0,
        threshold=500.0,
        confidence=0.88,
        raw_payload={"host": "node-1"},
    )

    assert alert.alert_id == "alert-valid"
    assert alert.timestamp == timestamp
    assert alert.domain == "infrastructure"
    assert alert.severity == "major"
    assert alert.device == "cartservice"
    assert alert.metric == "memory_available_mb"
    assert alert.message == "Memory low"
    assert alert.source_system == "node_exporter"
    assert alert.value == 450.0
    assert alert.threshold == 500.0
    assert alert.confidence == 0.88
    assert alert.raw_payload == {"host": "node-1"}


def test_canonical_alert_invalid_domain() -> None:
    """Creating CanonicalAlert with invalid domain raises ValueError."""
    with pytest.raises(ValueError):
        CanonicalAlert(
            alert_id="alert-invalid-domain",
            timestamp=datetime.now(),
            domain="invalid_domain",
            severity="critical",
            device="redis",
            metric="cpu_usage_percent",
            message="CPU high",
            source_system="prometheus",
            value=95.0,
            threshold=90.0,
            confidence=0.90,
            raw_payload={},
        )


def test_canonical_alert_invalid_severity() -> None:
    """Creating CanonicalAlert with invalid severity raises ValueError."""
    with pytest.raises(ValueError):
        CanonicalAlert(
            alert_id="alert-invalid-severity",
            timestamp=datetime.now(),
            domain="infrastructure",
            severity="extreme",
            device="redis",
            metric="cpu_usage_percent",
            message="CPU high",
            source_system="prometheus",
            value=95.0,
            threshold=90.0,
            confidence=0.90,
            raw_payload={},
        )


def test_canonical_alert_roundtrip() -> None:
    """CanonicalAlert to_dict/from_dict preserves key fields."""
    alert = _build_valid_alert()
    reconstructed = CanonicalAlert.from_dict(alert.to_dict())

    assert reconstructed.alert_id == alert.alert_id
    assert reconstructed.domain == alert.domain
    assert reconstructed.severity == alert.severity
    assert reconstructed.device == alert.device


def test_triage_decision_valid() -> None:
    """Valid triage decisions should construct without errors."""
    alert = _build_valid_alert()

    append_decision = TriageDecision(alert=alert, action="append", incident_id="inc-1")
    new_decision = TriageDecision(alert=alert, action="new", incident_id=None)

    assert append_decision.action == "append"
    assert append_decision.incident_id == "inc-1"
    assert new_decision.action == "new"
    assert new_decision.incident_id is None


def test_triage_decision_invalid_action() -> None:
    """Unknown triage action must raise ValueError."""
    with pytest.raises(ValueError):
        TriageDecision(alert=_build_valid_alert(), action="unknown", incident_id="inc-2")


def test_incident_valid_creation() -> None:
    """Create valid open incident and check advisory defaults."""
    incident = Incident(
        incident_id="inc-valid",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status="open",
        root_cause_device="redis",
        incident_title="Redis outage",
        affected_services=["cartservice", "checkoutservice"],
        confidence=0.91,
        recommended_action="Restart redis container",
        alerts=[_build_valid_alert()],
    )

    assert incident.preliminary_advisory_sent is False
    assert incident.confirmed_advisory_sent is False


def test_incident_invalid_status() -> None:
    """Invalid incident status must raise ValueError."""
    with pytest.raises(ValueError):
        Incident(
            incident_id="inc-invalid-status",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="pending",
            root_cause_device="redis",
            incident_title="Redis outage",
            affected_services=["cartservice"],
            confidence=0.70,
            recommended_action="Investigate",
            alerts=[],
        )


def test_incident_roundtrip() -> None:
    """Incident to_dict/from_dict preserves required fields."""
    incident = Incident(
        incident_id="inc-roundtrip",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status="open",
        root_cause_device="redis",
        incident_title="Redis latency cascade",
        affected_services=["cartservice", "frontend"],
        confidence=0.86,
        recommended_action="Rollback latest redis config",
        alerts=[_build_valid_alert()],
    )

    reconstructed = Incident.from_dict(incident.to_dict())
    assert reconstructed.incident_id == incident.incident_id
    assert reconstructed.affected_services == incident.affected_services
