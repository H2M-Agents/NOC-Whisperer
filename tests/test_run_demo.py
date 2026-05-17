"""Session 26 tests for run_demo script wiring and imports."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock


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


def test_streaming_pipeline_wiring() -> None:
    """StreamingPipeline exposes all agent and dashboard dependencies."""
    from orchestrator.incident_store import IncidentStore
    from orchestrator.streaming_pipeline import StreamingPipeline

    store = IncidentStore(":memory:")
    try:
        normalizer = MagicMock()
        triage = MagicMock()
        correlation = MagicMock()
        communications = MagicMock()
        dashboard = MagicMock()
        pipeline = StreamingPipeline(
            mcp_tools=[],
            normalizer=normalizer,
            triage=triage,
            correlation=correlation,
            communications=communications,
            incident_store=store,
            dashboard=dashboard,
        )
        assert pipeline.normalizer is normalizer
        assert pipeline.triage is triage
        assert pipeline.correlation is correlation
        assert pipeline.communications is communications
        assert pipeline.dashboard is dashboard
        assert pipeline.store is store
    finally:
        store.close()


def test_batch_reconciler_wiring() -> None:
    """BatchReconciler wires reconciler, store, interval; optional deps default None."""
    from orchestrator.batch_reconciler import BatchReconciler
    from orchestrator.incident_store import IncidentStore

    store = IncidentStore(":memory:")
    try:
        reconciler = MagicMock()
        batch = BatchReconciler(reconciler_agent=reconciler, incident_store=store, interval_seconds=15)
        assert batch.reconciler is reconciler
        assert batch.store is store
        assert batch.interval == 15
        assert batch.communications is None
        assert batch.dashboard is None
    finally:
        store.close()


def test_batch_reconciler_accepts_communications_and_dashboard() -> None:
    """BatchReconciler accepts communications and dashboard for resolution advisories."""
    from orchestrator.batch_reconciler import BatchReconciler
    from orchestrator.incident_store import IncidentStore

    store = IncidentStore(":memory:")
    try:
        communications = MagicMock()
        dashboard = MagicMock()
        batch = BatchReconciler(
            reconciler_agent=MagicMock(),
            incident_store=store,
            communications=communications,
            dashboard=dashboard,
        )
        assert batch.communications is communications
        assert batch.dashboard is dashboard
    finally:
        store.close()


def test_master_orchestrator_wiring() -> None:
    """MasterOrchestrator runs streaming and batch loops via run()."""
    from orchestrator.master_orchestrator import MasterOrchestrator

    orchestrator = MasterOrchestrator(
        streaming_pipeline=MagicMock(),
        batch_reconciler=MagicMock(),
    )
    assert orchestrator.streaming is not None
    assert orchestrator.batch is not None
    assert inspect.iscoroutinefunction(MasterOrchestrator.run)


def test_live_mode_flag_defaults_false() -> None:
    """run_demo checks NOC_LIVE_MODE and defaults to false when unset."""
    from scripts import run_demo

    source = Path(run_demo.__file__).read_text(encoding="utf-8")
    assert "NOC_LIVE_MODE" in source
    assert '.get("NOC_LIVE_MODE", "false")' in source or "NOC_LIVE_MODE\", \"false\"" in source


def test_run_demo_uses_batch_reconciler() -> None:
    """run_demo passes communications and dashboard into BatchReconciler."""
    from scripts import run_demo

    source = Path(run_demo.__file__).read_text(encoding="utf-8")
    assert "BatchReconciler" in source
    assert "communications=communications" in source
    assert "dashboard=dashboard" in source


def test_run_demo_uses_signal_based_close() -> None:
    """Signal-based close uses get_service_health on Prometheus MCP / ReconcilerAgent."""
    from scripts import run_demo

    run_demo_source = Path(run_demo.__file__).read_text(encoding="utf-8")
    reconciler_source = (
        Path(__file__).resolve().parents[1] / "orchestrator" / "reconciler_agent.py"
    ).read_text(encoding="utf-8")
    prometheus_source = (
        Path(__file__).resolve().parents[1] / "mcp_tools" / "prometheus_mcp.py"
    ).read_text(encoding="utf-8")

    assert "ReconcilerAgent" in run_demo_source
    assert "prometheus_mcp=" in run_demo_source
    assert "get_service_health" in reconciler_source
    assert "def get_service_health" in prometheus_source
