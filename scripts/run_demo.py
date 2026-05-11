"""Session 26 agentic demo using MasterOrchestrator loops."""

from __future__ import annotations

import asyncio
import os
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
    LIVE_MODE = os.environ.get("NOC_LIVE_MODE", "false").lower() == "true"

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
        mode="production",
    )
    communications = CommunicationsAgent(model_path=None)
    dashboard = NOCDashboard()
    reconciler = ReconcilerAgent(topology_mcp=topology, prometheus_mcp=_DemoPrometheus())

    if LIVE_MODE:
        from mcp_tools.prometheus_mcp import PrometheusMCP
        from mcp_tools.jaeger_mcp import JaegerMCP
        from mcp_tools.node_exporter_mcp import NodeExporterMCP
        import yaml

        with open("config/mcp_endpoints.yaml") as f:
            mcp_config = yaml.safe_load(f)
        mcp_tools_list = [
            PrometheusMCP(mcp_config["prometheus"]["base_url"]),
            JaegerMCP(mcp_config["jaeger"]["base_url"]),
            NodeExporterMCP(
                mcp_config["node_exporter"]["prometheus_base_url"]
            ),
        ]
        print("LIVE MODE: Using real MCP tools")
        print(f"  Prometheus: {mcp_config['prometheus']['base_url']}")
        print(f"  Jaeger:     {mcp_config['jaeger']['base_url']}")
        print("  Stop valkey-cart to trigger demo scenario:")
        print("  docker stop valkey-cart  (on ada-vm-1)")
    else:
        synthetic_tool = SyntheticAlertTool(alerts)
        mcp_tools_list = [synthetic_tool]
        print("SYNTHETIC MODE: Using generated alerts")

    pipeline = StreamingPipeline(
        mcp_tools=mcp_tools_list,
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
