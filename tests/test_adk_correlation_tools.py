"""Tests for ADK correlation tool wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import agents.adk_tools.correlation_tools as correlation_tools
from adapters.canonical_alert import CanonicalAlert, Incident


@pytest.fixture(autouse=True)
def _reset_correlation() -> None:
    """Isolate module singleton between tests."""
    correlation_tools._correlation = None
    yield
    correlation_tools._correlation = None


def test_correlate_alert_returns_empty_when_not_initialized() -> None:
    """Uninitialized correlation returns empty dict."""
    assert (
        correlation_tools.correlate_alert(
            alert_id="a1",
            device="cart",
            domain="application",
            severity="major",
            metric="m",
            value=1.0,
            confidence=0.9,
            source_system="prometheus",
            action="new",
            incident_id=None,
        )
        == {}
    )


def test_correlate_alert_returns_incident_dict() -> None:
    """Initialized correlation returns incident summary dict."""
    when = datetime.now(timezone.utc)
    alert = CanonicalAlert(
        alert_id="corr-1",
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
    incident = Incident(
        incident_id="inc-corr-1",
        created_at=when,
        updated_at=when,
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Cart outage",
        affected_services=["cart"],
        confidence=0.91,
        recommended_action="restart valkey",
        alerts=[alert],
    )
    mock_correlation = MagicMock()
    mock_correlation.correlate.return_value = incident
    correlation_tools._correlation = mock_correlation

    result = correlation_tools.correlate_alert(
        alert_id="corr-1",
        device="valkey-cart",
        domain="application",
        severity="major",
        metric="m",
        value=1.0,
        confidence=0.9,
        source_system="prometheus",
        action="new",
        incident_id=None,
    )

    assert result["incident_id"] == "inc-corr-1"
    assert result["root_cause_device"] == "valkey-cart"
    assert result["affected_services"] == ["cart"]
    assert result["confidence"] == pytest.approx(0.91)
    assert result["alert_count"] == 1
    assert result["status"] == "open"
    mock_correlation.correlate.assert_called_once()
