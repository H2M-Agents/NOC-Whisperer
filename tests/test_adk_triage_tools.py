"""Tests for ADK triage tool wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import agents.adk_tools.triage_tools as triage_tools
from adapters.canonical_alert import CanonicalAlert, TriageDecision


@pytest.fixture(autouse=True)
def _reset_triage() -> None:
    """Isolate module singleton between tests."""
    triage_tools._triage = None
    yield
    triage_tools._triage = None


def test_route_alert_returns_empty_when_not_initialized() -> None:
    """Uninitialized triage returns empty dict."""
    assert (
        triage_tools.route_alert(
            alert_id="a1",
            device="cart",
            domain="application",
            severity="major",
            metric="m",
            value=1.0,
            confidence=0.9,
            source_system="prometheus",
        )
        == {}
    )


def test_route_alert_returns_decision_dict() -> None:
    """Initialized triage returns serialized TriageDecision."""
    when = datetime.now(timezone.utc)
    alert = CanonicalAlert(
        alert_id="triage-1",
        timestamp=when,
        domain="application",
        severity="major",
        device="cart",
        metric="m",
        message="msg",
        source_system="prometheus",
        value=1.0,
        threshold=0.5,
        confidence=0.9,
        raw_payload={},
    )
    decision = TriageDecision(alert=alert, action="new", incident_id=None)
    mock_triage = MagicMock()
    mock_triage.route.return_value = decision
    triage_tools._triage = mock_triage

    result = triage_tools.route_alert(
        alert_id="triage-1",
        device="cart",
        domain="application",
        severity="major",
        metric="m",
        value=1.0,
        confidence=0.9,
        source_system="prometheus",
    )

    assert result["action"] == "new"
    assert result["incident_id"] is None
    assert result["alert"]["device"] == "cart"
    mock_triage.route.assert_called_once()
