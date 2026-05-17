"""NOC Whisperer demo using Google ADK Runner for orchestration."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from rich.console import Console

from agents.adk_tools.communications_tools import (
    init_communications,
    init_dashboard as init_comms_dashboard,
    init_store,
)
from agents.adk_tools.correlation_tools import init_correlation
from agents.adk_tools.incident_tools import init_incident_store
from agents.adk_tools.normalizer_tools import (
    init_dashboard as init_norm_dashboard,
    init_normalizer,
)
from agents.adk_tools.prometheus_tools import init_prometheus
from agents.adk_tools.triage_tools import init_triage
from dashboard.noc_dashboard import NOCDashboard
from orchestrator.adk_orchestrator import build_noc_orchestrator
from orchestrator.incident_store import IncidentStore

import google.adk.flows.llm_flows.functions as _adk_functions

_original_get_tool = _adk_functions._get_tool


def _patched_get_tool(function_call, tools_dict):
    """Sanitize hallucinated token suffixes from tool names.

    gpt-oss-20b sometimes appends <|channel|>commentary to tool names.
    """
    import re

    # Strip any non-alphanumeric/underscore suffix from tool name
    match = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*", function_call.name)
    clean_name = match.group(0) if match else function_call.name
    if clean_name != function_call.name:
        print(f"[ADK] Sanitized tool name: {function_call.name!r} -> {clean_name!r}")
        function_call.name = clean_name
    return _original_get_tool(function_call, tools_dict)


_adk_functions._get_tool = _patched_get_tool

import yaml


def _load_mcp_config() -> dict:
    try:
        with open("config/mcp_endpoints.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


_mcp_config = _load_mcp_config()
PROMETHEUS_URL = os.environ.get(
    "PROMETHEUS_URL",
    _mcp_config.get("prometheus", {}).get("base_url", "http://10.0.50.60:9090"),
)
JAEGER_URL = os.environ.get(
    "JAEGER_URL",
    _mcp_config.get("jaeger", {}).get("base_url", "http://10.0.50.60:16686"),
)
POLL_INTERVAL = 15


def _render_dashboard(dashboard: NOCDashboard) -> None:
    """Print the three-panel dashboard (NOCDashboard has generate_display, not render)."""
    Console().print(dashboard.generate_display())


async def main() -> None:
    """Initialize ADK tools, run polling cycles, and render dashboard state."""
    load_dotenv()

    store = IncidentStore(":memory:")
    dashboard = NOCDashboard()
    init_comms_dashboard(dashboard)
    init_norm_dashboard(dashboard)

    init_prometheus(PROMETHEUS_URL)
    init_normalizer()
    init_triage(store)
    init_correlation(store)
    init_communications()
    init_store(store)
    init_incident_store(store)

    agent = build_noc_orchestrator()
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="noc_whisperer",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="noc_whisperer",
        user_id="noc_operator",
    )

    print("NOC Whisperer — Google ADK Mode")
    print(f"Prometheus: {PROMETHEUS_URL}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n[Cycle {cycle}] Monitoring...")

            message = Content(
                role="user",
                parts=[
                    Part(
                        text=(
                            "Monitor NOC services and process any incidents "
                            "following all 6 steps."
                        )
                    )
                ],
            )

            async for event in runner.run_async(
                user_id="noc_operator",
                session_id=session.id,
                new_message=message,
            ):
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(f"[Agent] {part.text[:200]}")

                if hasattr(event, "actions") and event.actions:
                    for action in event.actions:
                        if (
                            hasattr(action, "tool_name")
                            and action.tool_name == "generate_advisory"
                        ):
                            pass  # advisory already stored via tool

            open_incidents = store.get_open_incidents()
            for incident in open_incidents:
                dashboard.update_incident_board(incident)
            _render_dashboard(dashboard)

            await asyncio.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("ADK DEMO SUMMARY")
        print("=" * 60)
        open_incidents = store.get_open_incidents()
        print(f"Open incidents: {len(open_incidents)}")


if __name__ == "__main__":
    asyncio.run(main())
