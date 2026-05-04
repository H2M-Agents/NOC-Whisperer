"""Tests for StreamingPipeline async orchestration."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, List

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident
from agents.correlation_agent import CorrelationAgent
from agents.normalizer_agent import NormalizerAgent
from agents.triage_agent import TriageAgent
from communications.communications_agent import CommunicationsAgent
from mcp_tools.mocks.mock_jaeger_mcp import MockJaegerMCP
from mcp_tools.mocks.mock_node_exporter_mcp import MockNodeExporterMCP
from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP
from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP
from orchestrator.incident_store import IncidentStore
from orchestrator.streaming_pipeline import StreamingPipeline


def _valkey_alert(alert_id: str) -> CanonicalAlert:
    """Single synthetic prometheus-style alert for valkey-cart cascade demos."""
    return CanonicalAlert(
        alert_id=alert_id,
        timestamp=datetime.now(timezone.utc),
        domain="application",
        severity="major",
        device="valkey-cart",
        metric="cache_errors",
        message="elevated errors",
        source_system="prometheus",
        value=10.0,
        threshold=1.0,
        confidence=0.9,
        raw_payload={"device": "valkey-cart", "metric": "cache_errors", "value": 10.0},
    )


class RecordingDashboard:
    """Captures dashboard callbacks for assertions."""

    def __init__(self) -> None:
        """Initialize empty recording buffers."""
        self.streams: List[CanonicalAlert] = []
        self.boards: List[Incident] = []
        self.advisories: List[str] = []

    def update_alert_stream(self, canonical: CanonicalAlert) -> None:
        """Record canonical alert updates."""
        self.streams.append(canonical)

    def update_incident_board(self, incident: Incident) -> None:
        """Record incident board updates."""
        self.boards.append(incident)

    def update_advisory(self, advisory: str) -> None:
        """Record advisory panel updates."""
        self.advisories.append(advisory)


@pytest.fixture
def topology() -> MockTopologyMCP:
    """Shared topology mock."""
    return MockTopologyMCP()


@pytest.fixture
def memory_store() -> IncidentStore:
    """Ephemeral SQLite incident store."""
    return IncidentStore(":memory:")


def test_import() -> None:
    """StreamingPipeline is importable."""
    from orchestrator.streaming_pipeline import StreamingPipeline as SP

    assert SP is not None


@pytest.mark.asyncio
async def test_process_alert_invalid_payload_raises(memory_store: IncidentStore, topology: MockTopologyMCP) -> None:
    """Non-CanonicalAlert inputs are rejected."""
    pipe = StreamingPipeline(
        mcp_tools=[],
        normalizer=NormalizerAgent(model_path=None),
        triage=TriageAgent(topology, memory_store),
        correlation=CorrelationAgent(topology, memory_store, mode="development"),
        communications=CommunicationsAgent(model_path=None),
        incident_store=memory_store,
        dashboard=RecordingDashboard(),
    )
    with pytest.raises(TypeError):
        await pipe.process_alert({"device": "x"})


@pytest.mark.asyncio
async def test_check_advisory_preliminary_triggers(memory_store: IncidentStore, topology: MockTopologyMCP) -> None:
    """Confidence above 0.50 triggers preliminary advisory once."""
    dash = RecordingDashboard()
    pipe = StreamingPipeline(
        mcp_tools=[],
        normalizer=NormalizerAgent(model_path=None),
        triage=TriageAgent(topology, memory_store),
        correlation=CorrelationAgent(topology, memory_store, mode="development"),
        communications=CommunicationsAgent(model_path=None),
        incident_store=memory_store,
        dashboard=dash,
    )
    inc = Incident(
        incident_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Test",
        affected_services=["cart"],
        confidence=0.55,
        recommended_action="Investigate",
        alerts=[],
        preliminary_advisory_sent=False,
        confirmed_advisory_sent=False,
    )
    await pipe.check_advisory_triggers(inc)
    assert len(dash.advisories) == 1


@pytest.mark.asyncio
async def test_check_advisory_confirmed_after_preliminary_sent(
    memory_store: IncidentStore, topology: MockTopologyMCP
) -> None:
    """High confidence triggers confirmed advisory when preliminary already sent."""
    dash = RecordingDashboard()
    pipe = StreamingPipeline(
        mcp_tools=[],
        normalizer=NormalizerAgent(model_path=None),
        triage=TriageAgent(topology, memory_store),
        correlation=CorrelationAgent(topology, memory_store, mode="development"),
        communications=CommunicationsAgent(model_path=None),
        incident_store=memory_store,
        dashboard=dash,
    )
    inc = Incident(
        incident_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Test",
        affected_services=["cart"],
        confidence=0.90,
        recommended_action="Investigate",
        alerts=[],
        preliminary_advisory_sent=True,
        confirmed_advisory_sent=False,
    )
    await pipe.check_advisory_triggers(inc)
    assert len(dash.advisories) == 1


@pytest.mark.asyncio
async def test_acceptance_streaming_pipeline_mock_tools(
    memory_store: IncidentStore, topology: MockTopologyMCP
) -> None:
    """Session 19 acceptance: mock tools feed valkey alert; store and advisory update."""
    seeded = [_valkey_alert("acceptance-valkey-1")]
    tools: List[Any] = [
        MockJaegerMCP([]),
        MockPrometheusMCP(seeded),
        MockNodeExporterMCP([]),
        topology,
    ]
    dash = RecordingDashboard()
    pipe = StreamingPipeline(
        mcp_tools=tools,
        normalizer=NormalizerAgent(model_path=None),
        triage=TriageAgent(topology, memory_store),
        correlation=CorrelationAgent(topology, memory_store, mode="development"),
        communications=CommunicationsAgent(model_path=None),
        incident_store=memory_store,
        dashboard=dash,
    )
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(pipe.streaming_loop(), timeout=5.0)

    assert len(memory_store.get_open_incidents()) >= 1
    assert len(dash.advisories) >= 1


@pytest.mark.asyncio
async def test_streaming_deduplicates_alert_ids(memory_store: IncidentStore, topology: MockTopologyMCP) -> None:
    """Same alert_id is only processed once across polling iterations."""
    same_id = "dedupe-alert-1"
    seeded = [_valkey_alert(same_id)]
    tools: List[Any] = [
        MockJaegerMCP([]),
        MockPrometheusMCP(seeded),
        MockNodeExporterMCP([]),
        topology,
    ]
    dash = RecordingDashboard()
    pipe = StreamingPipeline(
        mcp_tools=tools,
        normalizer=NormalizerAgent(model_path=None),
        triage=TriageAgent(topology, memory_store),
        correlation=CorrelationAgent(topology, memory_store, mode="development"),
        communications=CommunicationsAgent(model_path=None),
        incident_store=memory_store,
        dashboard=dash,
    )
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(pipe.streaming_loop(), timeout=5.0)

    assert same_id in pipe.seen_alert_ids
    assert len(dash.streams) == 1
