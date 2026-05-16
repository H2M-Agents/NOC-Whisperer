"""Tests for ADK NOC orchestrator factory."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from orchestrator.adk_orchestrator import NOC_INSTRUCTION, build_noc_orchestrator


def test_build_noc_orchestrator_returns_llm_agent() -> None:
    """Factory returns a configured LlmAgent named NOCOrchestrator."""
    agent = build_noc_orchestrator()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "NOCOrchestrator"


def test_noc_orchestrator_has_8_tools() -> None:
    """Orchestrator wires all eight NOC pipeline tools."""
    agent = build_noc_orchestrator()
    assert len(agent.tools) == 8


def test_noc_orchestrator_tool_names() -> None:
    """Each ADK FunctionTool exposes the expected callable name."""
    agent = build_noc_orchestrator()
    tool_names = [t.name for t in agent.tools]
    assert "get_active_alerts" in tool_names
    assert "normalize_alert" in tool_names
    assert "route_alert" in tool_names
    assert "correlate_alert" in tool_names
    assert "generate_advisory" in tool_names
    assert "check_open_incidents" in tool_names
    assert "check_service_health" in tool_names
    assert "close_incident" in tool_names


def test_noc_instruction_contains_all_steps() -> None:
    """NOC instruction documents the full six-step monitoring cycle."""
    assert "STEP 1" in NOC_INSTRUCTION
    assert "STEP 2" in NOC_INSTRUCTION
    assert "STEP 3" in NOC_INSTRUCTION
    assert "STEP 4" in NOC_INSTRUCTION
    assert "STEP 5" in NOC_INSTRUCTION
    assert "STEP 6" in NOC_INSTRUCTION
