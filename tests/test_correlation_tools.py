from unittest.mock import MagicMock, patch

import pytest

from agents.adk_tools.correlation_tools import correlate_alert


def _make_mock_incident(
    preliminary_advisory_sent=False,
    confirmed_advisory_sent=False,
):
    inc = MagicMock()
    inc.incident_id = "INC-TEST-001"
    inc.root_cause_device = "valkey-cart"
    inc.affected_services = ["cart", "checkout", "frontend"]
    inc.confidence = 0.91
    inc.alerts = [MagicMock(), MagicMock(), MagicMock()]
    inc.status = "open"
    inc.preliminary_advisory_sent = preliminary_advisory_sent
    inc.confirmed_advisory_sent = confirmed_advisory_sent
    return inc


def _make_mock_correlation(incident):
    mock = MagicMock()
    mock.correlate.return_value = incident
    mock.store._upsert_sync = MagicMock()
    return mock


_CORRELATE_KWARGS = dict(
    alert_id="alert-001",
    device="valkey-cart",
    domain="infrastructure",
    severity="critical",
    metric="cache_miss_ratio",
    value=0.95,
    confidence=0.91,
    source_system="prometheus",
    action="new",
    incident_id=None,
)


def test_correlate_alert_returns_preliminary_advisory_sent_false():
    inc = _make_mock_incident(preliminary_advisory_sent=False)
    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        _make_mock_correlation(inc),
    ):
        result = correlate_alert(**_CORRELATE_KWARGS)
    assert "preliminary_advisory_sent" in result
    assert result["preliminary_advisory_sent"] is False


def test_correlate_alert_returns_confirmed_advisory_sent_false():
    inc = _make_mock_incident(confirmed_advisory_sent=False)
    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        _make_mock_correlation(inc),
    ):
        result = correlate_alert(**_CORRELATE_KWARGS)
    assert "confirmed_advisory_sent" in result
    assert result["confirmed_advisory_sent"] is False


def test_correlate_alert_returns_preliminary_advisory_sent_true():
    inc = _make_mock_incident(preliminary_advisory_sent=True)
    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        _make_mock_correlation(inc),
    ):
        result = correlate_alert(**_CORRELATE_KWARGS)
    assert result["preliminary_advisory_sent"] is True


def test_correlate_alert_returns_confirmed_advisory_sent_true():
    inc = _make_mock_incident(confirmed_advisory_sent=True)
    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        _make_mock_correlation(inc),
    ):
        result = correlate_alert(**_CORRELATE_KWARGS)
    assert result["confirmed_advisory_sent"] is True


def test_correlate_alert_returns_all_required_keys():
    inc = _make_mock_incident()
    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        _make_mock_correlation(inc),
    ):
        result = correlate_alert(**_CORRELATE_KWARGS)
    required = {
        "incident_id",
        "root_cause_device",
        "affected_services",
        "confidence",
        "alert_count",
        "status",
        "preliminary_advisory_sent",
        "confirmed_advisory_sent",
    }
    assert required.issubset(result.keys())


def test_correlate_alert_returns_empty_when_not_initialized():
    with patch("agents.adk_tools.correlation_tools._correlation", None):
        result = correlate_alert(**_CORRELATE_KWARGS)
    assert result == {}
