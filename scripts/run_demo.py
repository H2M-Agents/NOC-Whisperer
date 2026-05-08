"""Session 26 agentic demo using MasterOrchestrator loops."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from agents.correlation_agent import CorrelationAgent
from agents.normalizer_agent import NormalizerAgent
from agents.triage_agent import TriageAgent
from communications.communications_agent import CommunicationsAgent
from dashboard.noc_dashboard import NOCDashboard
from generator.fault_scenarios import VALKEY_CART_CASCADE_SCENARIO
from generator.synthetic_generator import ScenarioDrivenGenerator
from mcp_tools.topology_mcp import TopologyMCP
from orchestrator.batch_reconciler import BatchReconciler
from orchestrator.incident_store import IncidentStore
from orchestrator.master_orchestrator import MasterOrchestrator
from orchestrator.reconciler_agent import ReconcilerAgent
from orchestrator.streaming_pipeline import StreamingPipeline


class SyntheticAlertTool:
    """One-shot synthetic alert source that returns alerts only once."""

    def __init__(self, alerts: list[object]) -> None:
        self._alerts = list(alerts)
        self._fired = False

    def get_alerts(self) -> list[object]:
        if not self._fired:
            self._fired = True
            return self._alerts
        return []


class _DemoPrometheus:
    """Minimal Prometheus stub for ReconcilerAgent in demo mode."""

    def query(self, _promql: str) -> dict:
        return {"status": "success"}


async def run_demo() -> None:
    """Run streaming and batch loops with dashboard thread."""
    from concurrent.futures import ThreadPoolExecutor
    import signal

    loop = asyncio.get_event_loop()

    load_dotenv()

    generator = ScenarioDrivenGenerator()
    incident = generator.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    alerts = incident if isinstance(incident, list) else incident.get("alerts", [])
    print(
        f"Generated {len(alerts)} alerts for scenario: "
        f"{VALKEY_CART_CASCADE_SCENARIO.name}"
    )

    topology = TopologyMCP("topology/otel_demo_graph.json")
    store = IncidentStore(":memory:")
    normalizer = NormalizerAgent(model_path=None)
    triage = TriageAgent(topology_mcp=topology, incident_store=store)
    correlator = CorrelationAgent(
        topology_mcp=topology,
        incident_store=store,
        mode="development",
    )
    communications = CommunicationsAgent(model_path=None)
    dashboard = NOCDashboard()
    reconciler = ReconcilerAgent(topology_mcp=topology, prometheus_mcp=_DemoPrometheus())

    synthetic_tool = SyntheticAlertTool(alerts)

    pipeline = StreamingPipeline(
        mcp_tools=[synthetic_tool],
        normalizer=normalizer,
        triage=triage,
        correlation=correlator,
        communications=communications,
        incident_store=store,
        dashboard=dashboard,
    )

    batch = BatchReconciler(
        reconciler_agent=reconciler,
        incident_store=store,
        interval_seconds=15,
    )

    orchestrator = MasterOrchestrator(
        streaming_pipeline=pipeline,
        batch_reconciler=batch,
    )

    print("Starting NOC Whisperer agentic demo...")
    print("Streaming loop + ReAct batch loop running in parallel")
    print("Press Ctrl+C to stop demo and see summary")
    print(f"{'=' * 60}")

    with ThreadPoolExecutor(max_workers=1) as executor:
        # Start dashboard in background thread
        loop.run_in_executor(executor, dashboard.run)

        try:
            # Run orchestrator indefinitely
            await orchestrator.run()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            # Stop dashboard cleanly
            dashboard.stop()

    # Print summary after demo ends
    open_incidents = store.get_open_incidents()
    primary = (
        store.get_incident(primary_incident_id)
        if 'primary_incident_id' in dir()
        else None
    )
    top = primary if primary is not None else (
        open_incidents[0] if open_incidents else None
    )

    print(f"\n{'=' * 60}")
    print("DEMO SUMMARY")
    print(f"{'=' * 60}")
    print(f"Alerts processed:    {len(alerts)}")
    print(f"Incidents created:   {len(open_incidents)}")
    if top is not None:
        advisory_status = (
            "Confirmed" if top.confirmed_advisory_sent
            else "Preliminary" if top.preliminary_advisory_sent
            else "No"
        )
        print(f"Root cause:          {top.root_cause_device}")
        print(f"Confidence:          {top.confidence:.2f}")
        print(f"Affected services:   {', '.join(top.affected_services)}")
        print(f"Advisory fired:      {advisory_status}")
    print(f"{'=' * 60}")


def main() -> None:
    """Entry point for demo execution."""
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
