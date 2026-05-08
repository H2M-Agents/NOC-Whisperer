"""Session 26 tests for run_demo script wiring and imports."""

from __future__ import annotations

from pathlib import Path


def test_import() -> None:
    """run_demo imports without error."""
    from scripts import run_demo

    assert run_demo is not None


def test_main_guard_exists() -> None:
    """Script includes a __main__ guard."""
    from scripts import run_demo

    content = Path(run_demo.__file__).read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in content


def test_required_imports_resolve() -> None:
    """Core agent and dependency imports resolve."""
    from agents.correlation_agent import CorrelationAgent
    from agents.normalizer_agent import NormalizerAgent
    from agents.triage_agent import TriageAgent
    from communications.communications_agent import CommunicationsAgent
    from dashboard.noc_dashboard import NOCDashboard
    from mcp_tools.topology_mcp import TopologyMCP
    from orchestrator.incident_store import IncidentStore

    assert CorrelationAgent is not None
    assert NormalizerAgent is not None
    assert TriageAgent is not None
    assert CommunicationsAgent is not None
    assert NOCDashboard is not None
    assert TopologyMCP is not None
    assert IncidentStore is not None


def test_scenario_exists() -> None:
    """Primary demo scenario is importable."""
    from generator.fault_scenarios import VALKEY_CART_CASCADE_SCENARIO

    assert VALKEY_CART_CASCADE_SCENARIO.name


def test_store_instantiation() -> None:
    """IncidentStore supports in-memory instantiation."""
    from orchestrator.incident_store import IncidentStore

    store = IncidentStore(":memory:")
    try:
        assert store.get_open_incidents() == []
    finally:
        store.close()


def test_synthetic_alert_tool_fires_once() -> None:
    """SyntheticAlertTool emits alerts only on first poll."""
    from scripts.run_demo import SyntheticAlertTool

    mock_alert = object()
    tool = SyntheticAlertTool([mock_alert])
    assert len(tool.get_alerts()) == 1
    assert len(tool.get_alerts()) == 0
