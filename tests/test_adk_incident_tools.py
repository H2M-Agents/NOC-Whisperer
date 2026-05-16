"""Tests for ADK incident store tool wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

import agents.adk_tools.incident_tools as incident_tools
from adapters.canonical_alert import CanonicalAlert, Incident


@pytest.fixture(autouse=True)
def _reset_incident_store() -> None:
    """Isolate module singleton between tests."""
    incident_tools._store = None
    yield
    incident_tools._store = None


def test_check_open_incidents_returns_empty_when_not_initialized() -> None:
    """Uninitialized store returns empty list."""
    assert incident_tools.check_open_incidents() == []


def test_close_incident_returns_error_when_not_found() -> None:
    """Missing incident returns error dict without upsert."""
    mock_store = MagicMock()
    mock_store.get_incident.return_value = None
    incident_tools.init_incident_store(mock_store)

    result = incident_tools.close_incident("missing-id")

    assert result == {"error": "Incident missing-id not found"}
    mock_store.upsert.assert_not_called()


def test_close_incident_marks_resolved() -> None:
    """Found incident is marked resolved and persisted via upsert."""
    when = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="inc-close-1",
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
    mock_store.upsert = AsyncMock()
    incident_tools.init_incident_store(mock_store)

    result = incident_tools.close_incident("inc-close-1")

    assert result == {"incident_id": "inc-close-1", "status": "resolved"}
    assert incident.status == "resolved"
    mock_store.upsert.assert_awaited_once_with(incident)
