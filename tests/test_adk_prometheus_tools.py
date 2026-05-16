"""Tests for ADK Prometheus tool wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import agents.adk_tools.prometheus_tools as prometheus_tools
from adapters.canonical_alert import CanonicalAlert


@pytest.fixture(autouse=True)
def _reset_prometheus() -> None:
    """Isolate module singleton between tests."""
    prometheus_tools._prometheus = None
    yield
    prometheus_tools._prometheus = None


def test_get_active_alerts_returns_empty_when_not_initialized() -> None:
    """Uninitialized client returns empty list (fail safe)."""
    assert prometheus_tools.get_active_alerts() == []


def test_check_service_health_returns_true_when_not_initialized() -> None:
    """Uninitialized client assumes healthy (fail open)."""
    assert prometheus_tools.check_service_health("cart") is True


def test_get_active_alerts_with_mock_prometheus() -> None:
    """Initialized client serializes threshold breaches via to_dict."""
    when = datetime.now(timezone.utc)
    alert = CanonicalAlert(
        alert_id="adk-prom-1",
        timestamp=when,
        domain="service_mesh",
        severity="major",
        device="cart",
        metric="http_error_rate_per_min",
        message="breach",
        source_system="prometheus",
        value=25.0,
        threshold=20.0,
        confidence=0.9,
        raw_payload={},
    )
    mock_prom = MagicMock()
    mock_prom.get_threshold_breaches.return_value = [alert]
    prometheus_tools._prometheus = mock_prom

    result = prometheus_tools.get_active_alerts()

    assert len(result) == 1
    assert result[0]["device"] == "cart"
    assert result[0]["source_system"] == "prometheus"
    mock_prom.get_threshold_breaches.assert_called_once()


def test_check_service_health_with_mock_prometheus() -> None:
    """Initialized client delegates health check to Prometheus MCP."""
    mock_prom = MagicMock()
    mock_prom.get_service_health.return_value = False
    prometheus_tools._prometheus = mock_prom

    assert prometheus_tools.check_service_health("valkey-cart") is False
    mock_prom.get_service_health.assert_called_once_with("valkey-cart")
