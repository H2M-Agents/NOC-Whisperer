"""Tests for ADK communications tool wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import agents.adk_tools.communications_tools as communications_tools
from adapters.canonical_alert import CanonicalAlert, Incident


@pytest.fixture(autouse=True)
def _reset_communications() -> None:
    """Isolate module singletons between tests."""
    communications_tools._communications = None
    communications_tools._store = None
    yield
    communications_tools._communications = None
    communications_tools._store = None


def test_generate_advisory_returns_empty_when_not_initialized() -> None:
    """Uninitialized communications returns empty string."""
    assert communications_tools.generate_advisory("inc-1", "preliminary") == ""


def test_generate_advisory_returns_string() -> None:
    """Initialized communications generates advisory from store incident."""
    when = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="inc-adv-1",
        created_at=when,
        updated_at=when,
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Cart outage",
        affected_services=["cart"],
        confidence=0.9,
        recommended_action="investigate",
        alerts=[
            CanonicalAlert(
                alert_id="a1",
                timestamp=when,
                domain="application",
                severity="major",
                device="valkey-cart",
                metric="m",
                message="msg",
                source_system="prometheus",
                value=1.0,
                threshold=0.5,
                confidence=0.9,
                raw_payload={},
            )
        ],
    )
    mock_store = MagicMock()
    mock_store.get_incident.return_value = incident
    mock_comms = MagicMock()
    mock_comms.generate.return_value = "SERVICE RESTORED advisory"
    communications_tools._communications = mock_comms
    communications_tools.init_store(mock_store)

    text = communications_tools.generate_advisory("inc-adv-1", "resolution")

    assert text == "SERVICE RESTORED advisory"
    mock_comms.generate.assert_called_once_with(incident, advisory_type="resolution")
