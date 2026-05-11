"""Tests for CommunicationsAgent stub."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from adapters.canonical_alert import Incident
from communications.communications_agent import CommunicationsAgent


def _sample_incident() -> Incident:
    return Incident(
        incident_id="test-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Valkey cache failure",
        affected_services=["cart", "checkout"],
        confidence=0.67,
        recommended_action="Restart valkey-cart",
        alerts=[],
    )


def test_import() -> None:
    """CommunicationsAgent imports from package."""
    from communications.communications_agent import CommunicationsAgent as CA

    assert CA is not None


def test_instantiation_no_model_path() -> None:
    """Agent constructs with default path resolution."""
    agent = CommunicationsAgent(model_path=None)
    assert agent is not None


def test_generate_returns_string() -> None:
    """Preliminary generate returns non-empty string."""
    agent = CommunicationsAgent(model_path=None)
    incident = _sample_incident()
    with patch.object(CommunicationsAgent, '_infer_ollama',
                      return_value="Mock preliminary advisory"):
        result = agent.generate(incident, advisory_type="preliminary")
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_confirmed_returns_string() -> None:
    """Confirmed generate returns non-empty string."""
    agent = CommunicationsAgent(model_path=None)
    incident = _sample_incident()
    with patch.object(CommunicationsAgent, '_infer_ollama',
                      return_value="Mock confirmed advisory"):
        result = agent.generate(incident, advisory_type="confirmed")
    assert isinstance(result, str)
    assert len(result) > 0


def test_format_prompt_preliminary_contains_investigating() -> None:
    """Preliminary instructions mention investigation / suspicion."""
    agent = CommunicationsAgent(model_path=None)
    incident = _sample_incident()
    prompt = agent._format_prompt(incident, "preliminary")
    assert any(word in prompt.lower() for word in ["investigating", "suspected", "preliminary"])


def test_format_prompt_confirmed_contains_confirmed() -> None:
    """Confirmed instructions mention confirmation and actions."""
    agent = CommunicationsAgent(model_path=None)
    incident = _sample_incident()
    prompt = agent._format_prompt(incident, "confirmed")
    assert any(word in prompt.lower() for word in ["confirmed", "action", "root cause"])
