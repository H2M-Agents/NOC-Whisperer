"""Unit tests for Prometheus MCP live and mock implementations."""


def test_to_canonical_produces_valid_canonical_alert() -> None:
    import time
    from datetime import datetime

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")

    mock_metric_result = {
        "metric": {
            "__name__": "http_error_rate_per_min",
            "job": "cart",
            "instance": "cart:8080",
        },
        "value": [time.time(), "25.5"],
    }

    alert = live._to_canonical(mock_metric_result)

    assert isinstance(alert, CanonicalAlert)
    assert alert.domain == "service_mesh"
    assert alert.source_system == "prometheus"
    assert alert.value == 25.5
    assert alert.device == "cart"
    assert isinstance(alert.timestamp, datetime)
    assert alert.confidence == 0.90
    assert isinstance(alert.raw_payload, dict)
    assert getattr(alert, "incident_id", None) is None


def test_to_canonical_severity_is_valid() -> None:
    import time

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    mock_metric_result = {
        "metric": {"__name__": "http_error_rate_per_min", "job": "checkout", "instance": "checkout:5050"},
        "value": [time.time(), "25.0"],
    }
    alert = live._to_canonical(mock_metric_result)
    assert alert.severity in {"critical", "major", "minor", "warning"}


def test_import() -> None:
    from mcp_tools.prometheus_mcp import PrometheusMCP
    from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP

    assert PrometheusMCP is not None
    assert MockPrometheusMCP is not None


def test_mock_returns_empty_by_default() -> None:
    from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP

    mock = MockPrometheusMCP()
    result = mock.get_threshold_breaches()
    assert isinstance(result, list)
    assert len(result) == 0


def test_mock_returns_injected_alerts() -> None:
    from datetime import datetime, timezone

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP

    alert = CanonicalAlert(
        alert_id="test-001",
        timestamp=datetime.now(timezone.utc),
        domain="service_mesh",
        severity="critical",
        device="cart",
        metric="http_error_rate_per_min",
        message="cart error rate high",
        source_system="prometheus",
        value=25.0,
        threshold=20.0,
        confidence=0.95,
        raw_payload={},
    )
    mock = MockPrometheusMCP(scenario_alerts=[alert])
    result = mock.get_threshold_breaches()
    assert len(result) == 1
    assert result[0].alert_id == "test-001"


def test_mock_health_check_true() -> None:
    from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP

    mock = MockPrometheusMCP()
    assert mock.health_check() is True


def test_mock_get_alerts_since() -> None:
    from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP

    mock = MockPrometheusMCP()
    result = mock.get_alerts_since(seconds=30)
    assert isinstance(result, list)


def test_live_health_check_fails_gracefully() -> None:
    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    result = live.health_check()
    assert result is False


def test_live_get_threshold_breaches_fails_gracefully() -> None:
    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    result = live.get_threshold_breaches()
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_service_health_returns_false_when_device_breaching() -> None:
    """``get_service_health`` is False when ``query`` vectors include a breach for that device."""
    from unittest.mock import patch

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    breach_vector = {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": {
                        "job": "opentelemetry-demo/cart",
                        "instance": "cart:8080",
                    },
                    "value": [0, "1.0"],
                }
            ]
        },
    }

    def fake_query(self: PrometheusMCP, _promql: str) -> dict:
        return breach_vector

    with patch.object(PrometheusMCP, "query", fake_query):
        assert live.get_service_health("cart") is False


def test_get_service_health_returns_true_when_device_not_breaching() -> None:
    """Healthy when breaches exist only for other devices (e.g. frontend, not cart)."""
    from unittest.mock import patch

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    breach_vector = {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": {
                        "job": "opentelemetry-demo/frontend",
                        "instance": "frontend:8080",
                    },
                    "value": [0, "1.0"],
                }
            ]
        },
    }

    def fake_query(self: PrometheusMCP, _promql: str) -> dict:
        return breach_vector

    with patch.object(PrometheusMCP, "query", fake_query):
        assert live.get_service_health("cart") is True


def test_get_service_health_returns_true_on_exception() -> None:
    """``get_service_health`` fails open (True) when ``query`` raises."""
    from unittest.mock import patch

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")

    def boom(self: PrometheusMCP, _promql: str) -> dict:
        raise RuntimeError("query failed")

    with patch.object(PrometheusMCP, "query", boom):
        assert live.get_service_health("cart") is True
