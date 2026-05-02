"""Tests for the correlation agent and incident assembly."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident, TriageDecision
from agents.correlation_agent import CorrelationAgent, _parse_confidence_field, _split_affected_services
from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP


def _alert(alert_id: str, device: str, ts: datetime) -> CanonicalAlert:
    return CanonicalAlert(
        alert_id=alert_id,
        timestamp=ts,
        domain="application",
        severity="major",
        device=device,
        metric="m",
        message="msg",
        source_system="synthetic",
        value=1.0,
        threshold=0.5,
        confidence=0.9,
        raw_payload={},
    )


class MockEmptyStore:
    """Store with no open incidents."""

    def get_open_incidents(self) -> list[Incident]:
        return []


class MockStoreWithIncident:
    """Store returning one open incident for append flows."""

    def __init__(self, incident: Incident) -> None:
        self._incident = incident

    def get_open_incidents(self) -> list[Incident]:
        return [self._incident]


def test_import() -> None:
    """CorrelationAgent must import."""
    assert CorrelationAgent is not None


def test_parse_confidence_field() -> None:
    """Confidence parser reads leading float."""
    assert _parse_confidence_field("0.82 Reasoning text") == pytest.approx(0.82)
    assert _parse_confidence_field("no number") == 0.5


def test_split_affected_services() -> None:
    """Affected services split on commas."""
    assert _split_affected_services("cart, checkout") == ["cart", "checkout"]


def test_correlate_new_populates_incident_fields() -> None:
    """TriageDecision action=new yields Incident with required fields."""
    topo = MockTopologyMCP()
    agent = CorrelationAgent(topo, MockEmptyStore(), window_seconds=180, mode="development")
    now = datetime.now(timezone.utc)
    alert = _alert(str(uuid.uuid4()), "valkey-cart", now)
    decision = TriageDecision(alert=alert, action="new", incident_id=None)
    incident = agent.correlate(decision)
    assert incident.status == "open"
    assert incident.incident_title
    assert incident.root_cause_device
    assert incident.affected_services
    assert 0.0 <= incident.confidence <= 1.0
    assert incident.recommended_action
    assert len(incident.alerts) >= 1
    assert incident.alerts[-1].alert_id == alert.alert_id


def test_correlate_append_reuses_incident_id() -> None:
    """Append path preserves existing incident id and merges alerts."""
    topo = MockTopologyMCP()
    base_time = datetime.now(timezone.utc)
    prior_alert = _alert("a-old", "valkey-cart", base_time)
    open_incident = Incident(
        incident_id="inc-existing",
        created_at=base_time,
        updated_at=base_time,
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Existing",
        affected_services=["cart"],
        confidence=0.7,
        recommended_action="watch",
        alerts=[prior_alert],
    )
    store = MockStoreWithIncident(open_incident)
    agent = CorrelationAgent(topo, store, window_seconds=180, mode="development")
    new_alert = _alert("a-new", "cart", base_time + timedelta(seconds=10))
    decision = TriageDecision(alert=new_alert, action="append", incident_id="inc-existing")
    result = agent.correlate(decision)
    assert result.incident_id == "inc-existing"
    assert result.created_at == open_incident.created_at
    assert len(result.alerts) == 2
    assert result.alerts[-1].alert_id == new_alert.alert_id


def test_sliding_window_prunes_stale_alerts() -> None:
    """Alerts older than window drop from buffer before new clustering."""
    topo = MockTopologyMCP()
    agent = CorrelationAgent(topo, MockEmptyStore(), window_seconds=60, mode="development")
    t0 = datetime.now(timezone.utc)
    old = _alert("old", "kafka", t0 - timedelta(seconds=120))
    agent.alert_buffer.append(old)
    fresh_alert = _alert("fresh", "valkey-cart", t0)
    decision = TriageDecision(alert=fresh_alert, action="new", incident_id=None)
    incident = agent.correlate(decision)
    assert old not in agent.alert_buffer
    assert incident.alerts[-1].alert_id == fresh_alert.alert_id


def test_load_correlator_production_is_dspycorrelator() -> None:
    """Production mode selects DSPy correlator stub."""
    from dspy_programs.alerts_to_incident import DSPyCorrelator

    topo = MockTopologyMCP()
    agent = CorrelationAgent(topo, MockEmptyStore(), mode="production")
    assert isinstance(agent.correlator, DSPyCorrelator)


def test_roundtrip_incident_from_correlate() -> None:
    """Incident serializes round-trip after correlate."""
    topo = MockTopologyMCP()
    agent = CorrelationAgent(topo, MockEmptyStore(), mode="development")
    alert = _alert(str(uuid.uuid4()), "cart", datetime.now(timezone.utc))
    decision = TriageDecision(alert=alert, action="new", incident_id=None)
    inc = agent.correlate(decision)
    restored = Incident.from_dict(inc.to_dict())
    assert restored.incident_id == inc.incident_id
    assert len(restored.alerts) == len(inc.alerts)
