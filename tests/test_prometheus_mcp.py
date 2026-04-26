"""Unit tests for Prometheus MCP live and mock implementations."""


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
    from datetime import datetime

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.mocks.mock_prometheus_mcp import MockPrometheusMCP

    alert = CanonicalAlert(
        alert_id="test-001",
        timestamp=datetime.utcnow(),
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
