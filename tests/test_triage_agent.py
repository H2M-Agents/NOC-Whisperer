"""Tests for rule-based triage routing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident, TriageDecision
from agents.triage_agent import TriageAgent
from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP


class MockIncidentStore:
    """In-memory store exposing open incidents for tests."""

    def __init__(self, incidents: list[Incident]) -> None:
        """Initialize with a fixed list of open incidents."""
        self._open = list(incidents)

    def get_open_incidents(self) -> list[Incident]:
        """Return open incidents."""
        return list(self._open)


def _dt(offset_seconds: float = 0.0) -> datetime:
    base = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=offset_seconds)


def _make_alert(device: str, ts: datetime) -> CanonicalAlert:
    return CanonicalAlert(
        alert_id="alert-test-1",
        timestamp=ts,
        domain="application",
        severity="major",
        device=device,
        metric="cpu_usage_percent",
        message="test alert",
        source_system="synthetic",
        value=1.0,
        threshold=0.9,
        confidence=0.95,
        raw_payload={},
    )


def _make_incident(
    incident_id: str,
    root_cause_device: str,
    updated_at: datetime,
) -> Incident:
    return Incident(
        incident_id=incident_id,
        created_at=updated_at - timedelta(minutes=5),
        updated_at=updated_at,
        status="open",
        root_cause_device=root_cause_device,
        incident_title="Test incident",
        affected_services=["cart"],
        confidence=0.8,
        recommended_action="investigate",
        alerts=[],
    )


def test_import() -> None:
    """Smoke import for triage agent."""
    assert TriageAgent is not None


def test_route_append_when_temporal_and_topological_match() -> None:
    """Related alert should append to matching open incident."""
    topo = MockTopologyMCP()
    updated = _dt(0)
    inc = _make_incident("inc-1", "cart", updated)
    store = MockIncidentStore([inc])
    agent = TriageAgent(topo, store)
    # MockTopologyMCP: are_related("valkey-cart", "cart") is True
    alert = _make_alert("valkey-cart", updated)
    decision = agent.route(alert)
    assert decision.action == "append"
    assert decision.incident_id == "inc-1"
    assert decision.alert.alert_id == alert.alert_id


def test_route_new_when_topologically_unrelated() -> None:
    """Unrelated device should open a new incident path."""
    topo = MockTopologyMCP()
    updated = _dt(0)
    inc = _make_incident("inc-1", "cart", updated)
    store = MockIncidentStore([inc])
    agent = TriageAgent(topo, store)
    alert = _make_alert("kafka", updated)
    decision = agent.route(alert)
    assert decision.action == "new"
    assert decision.incident_id is None


def test_route_new_when_no_open_incidents() -> None:
    """Empty store yields new incident."""
    topo = MockTopologyMCP()
    agent = TriageAgent(topo, MockIncidentStore([]))
    alert = _make_alert("valkey-cart", _dt(0))
    decision = agent.route(alert)
    assert decision.action == "new"
    assert decision.incident_id is None


def test_route_new_when_temporal_window_exceeded() -> None:
    """Outside time window should not append even if topology matches."""
    topo = MockTopologyMCP()
    updated = _dt(0)
    inc = _make_incident("inc-1", "cart", updated)
    store = MockIncidentStore([inc])
    agent = TriageAgent(topo, store)
    alert = _make_alert("valkey-cart", updated + timedelta(seconds=301))
    decision = agent.route(alert)
    assert decision.action == "new"


def test_is_temporally_proximate_boundary() -> None:
    """Exactly at window edge counts as proximate."""
    topo = MockTopologyMCP()
    updated = _dt(0)
    inc = _make_incident("inc-1", "cart", updated)
    agent = TriageAgent(topo, MockIncidentStore([inc]))
    alert = _make_alert("valkey-cart", updated + timedelta(seconds=300))
    assert agent._is_temporally_proximate(alert, inc) is True


def test_triage_decision_roundtrip() -> None:
    """TriageDecision serialization round-trip."""
    alert = _make_alert("cart", _dt(0))
    original = TriageDecision(alert=alert, action="new", incident_id=None)
    restored = TriageDecision.from_dict(original.to_dict())
    assert restored.action == original.action
    assert restored.incident_id == original.incident_id
    assert restored.alert.alert_id == original.alert.alert_id


def test_triage_decision_invalid_action_raises() -> None:
    """Invalid action must raise ValueError."""
    alert = _make_alert("cart", _dt(0))
    with pytest.raises(ValueError):
        TriageDecision(alert=alert, action="merge", incident_id=None)


def test_acceptance_scenario_append_and_new() -> None:
    """Session-style acceptance: append related, new unrelated."""
    topo = MockTopologyMCP()
    base = _dt(0)
    inc = _make_incident("open-1", "cart", base)
    store = MockIncidentStore([inc])
    agent = TriageAgent(topo, store)

    append_alert = _make_alert("valkey-cart", base)
    d_append = agent.route(append_alert)
    assert d_append.action == "append"
    assert d_append.incident_id == "open-1"

    new_alert = _make_alert("kafka", base)
    d_new = agent.route(new_alert)
    assert d_new.action == "new"
    assert d_new.incident_id is None
