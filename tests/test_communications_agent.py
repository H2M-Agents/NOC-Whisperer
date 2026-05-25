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


def test_format_prompt_confirmed_one_action_required() -> None:
    """Confirmed prompt instructs exactly one
    ACTION REQUIRED line and caps at 10 lines.
    Old plural 'ACTION REQUIRED lines' instruction
    must be absent.
    """
    from datetime import datetime, timezone

    from adapters.canonical_alert import Incident
    from communications.communications_agent import CommunicationsAgent

    inc = Incident(
        incident_id="test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status="open",
        root_cause_device="cart",
        incident_title="Cart threshold breach",
        affected_services=["cart"],
        confidence=0.95,
        recommended_action="probe",
        alerts=[],
    )
    agent = CommunicationsAgent.__new__(CommunicationsAgent)
    prompt = agent._format_prompt(inc, "confirmed")

    assert "exactly one" in prompt.lower()
    assert "at most 10 lines" in prompt.lower()
    assert "ACTION REQUIRED lines" not in prompt
    assert "confirmed" in prompt.lower()
    assert "speculation" in prompt.lower()


def test_infer_local_caps_action_required_lines() -> None:
    """_infer_local stops after 2nd ACTION REQUIRED
    line and caps total at 12 lines. Does not need
    GPU — full infer chain is mocked.
    """
    from unittest.mock import MagicMock

    from communications.communications_agent import CommunicationsAgent

    thirty_ar_lines = "\n".join(
        f"ACTION REQUIRED: item {i}"
        for i in range(30)
    )

    agent = CommunicationsAgent.__new__(CommunicationsAgent)

    mock_tokenizer = MagicMock()
    mock_input_ids = MagicMock()
    mock_input_ids.shape = (1, 5)
    mock_inputs = MagicMock()
    mock_inputs.__getitem__ = lambda _self, key: mock_input_ids
    mock_inputs.to = lambda _device: mock_inputs
    mock_tokenizer.return_value = mock_inputs
    mock_tokenizer.decode.return_value = thirty_ar_lines
    mock_tokenizer.eos_token_id = 0
    agent._tokenizer = mock_tokenizer

    mock_model = MagicMock()
    mock_outputs = MagicMock()
    mock_outputs.__getitem__ = lambda _self, _idx: mock_input_ids
    mock_model.generate.return_value = mock_outputs
    mock_model.device = "cpu"
    agent._model = mock_model

    result = agent._infer_local("test prompt")
    result_lines = [
        l for l in result.splitlines() if l.strip()
    ]
    ar_count = sum(
        1 for l in result_lines
        if "ACTION REQUIRED" in l.upper()
    )

    assert ar_count <= 2, (
        f"Expected <=2 ACTION REQUIRED lines, got {ar_count}"
    )
    assert len(result_lines) <= 12, (
        f"Expected <=12 lines total, got {len(result_lines)}"
    )
