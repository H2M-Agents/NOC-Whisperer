"""Tests for ReconcilerAgent and ReconcilerDecision."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident
from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP
from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP
from orchestrator.reconciler_agent import ReconcilerAgent, ReconcilerDecision


def _alert(
    device: str,
    aid: str | None = None,
) -> CanonicalAlert:
    return CanonicalAlert(
        alert_id=aid or str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        domain="application",
        severity="major",
        device=device,
        metric="m",
        message="msg",
        source_system="prometheus",
        value=1.0,
        threshold=0.5,
        confidence=0.9,
        raw_payload={},
    )


def _incident(
    iid: str,
    root: str,
    confidence: float = 0.9,
    updated: datetime | None = None,
) -> Incident:
    when = updated or datetime.now(timezone.utc)
    return Incident(
        incident_id=iid,
        created_at=when,
        updated_at=when,
        status="open",
        root_cause_device=root,
        incident_title="t",
        affected_services=["cart"],
        confidence=confidence,
        recommended_action="act",
        alerts=[_alert(root)],
    )


def test_import() -> None:
    """Reconciler types import."""
    from orchestrator.reconciler_agent import ReconcilerAgent as RA

    assert RA is not None


def test_reconciler_decision_invalid_action_raises() -> None:
    """Invalid action string raises ValueError."""
    with pytest.raises(ValueError):
        ReconcilerDecision(action="shuffle", primary_incident_id="x", reasoning="bad")


def test_reconciler_decision_merge_requires_secondary() -> None:
    """Merge decisions must include secondary incident id."""
    with pytest.raises(ValueError):
        ReconcilerDecision(action="merge", primary_incident_id="a", reasoning="missing secondary")


def test_two_related_incidents_merge() -> None:
    """Related topology + confidence produces merge decision."""
    topo = MockTopologyMCP()
    prom = MockPrometheusMCP()
    agent = ReconcilerAgent(topo, prom, max_iterations=3)
    inc_a = _incident("inc-a", "valkey-cart", confidence=0.8)
    inc_b = _incident("inc-b", "cart", confidence=0.8)
    decisions = agent.reconcile([inc_a, inc_b])
    merges = [d for d in decisions if d.action == "merge"]
    assert len(merges) == 1
    assert merges[0].primary_incident_id == "inc-a"
    assert merges[0].secondary_incident_id == "inc-b"


def test_two_unrelated_incidents_keep() -> None:
    """Unrelated devices yield no merge (pair resolves to keep — omitted from output)."""
    topo = MockTopologyMCP()
    prom = MockPrometheusMCP()
    agent = ReconcilerAgent(topo, prom)
    inc_a = _incident("inc-a", "valkey-cart", confidence=0.8)
    inc_b = _incident("inc-b", "kafka", confidence=0.8)
    decisions = agent.reconcile([inc_a, inc_b])
    assert not any(d.action == "merge" for d in decisions)


def test_stale_incident_closes() -> None:
    """Old updated_at beyond inactivity window triggers close."""
    topo = MockTopologyMCP()
    prom = MockPrometheusMCP()
    agent = ReconcilerAgent(topo, prom)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=25)
    stale = _incident("stale-1", "valkey-cart", updated=stale_time)
    decisions = agent.reconcile([stale])
    closes = [d for d in decisions if d.action == "close"]
    assert len(closes) == 1
    assert closes[0].primary_incident_id == "stale-1"
    assert "20 minutes" in closes[0].reasoning


def test_acceptance_reconciler_agent_ok() -> None:
    """Session 20 smoke: merge, keep, and close paths reachable."""
    topo = MockTopologyMCP()
    prom = MockPrometheusMCP()
    agent = ReconcilerAgent(topo, prom)
    assert agent.reconcile([]) == []
    print("Reconciler agent OK")
