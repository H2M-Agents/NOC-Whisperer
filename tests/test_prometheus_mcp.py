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


# ── Option C relabeling: frontend /api/data → ad ─────────


def test_to_canonical_frontend_api_data_relabeled_to_ad() -> None:
    """frontend + target=/api/data must produce device=ad."""
    import time

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    metric_result = {
        "metric": {
            "service_name": "frontend",
            "job": "opentelemetry-demo/frontend",
            "instance": "frontend:8080",
            "target": "/api/data",
            "status": "500",
        },
        "value": [time.time(), "0.88"],
    }
    alert = live._to_canonical(metric_result)
    assert alert.device == "ad", (
        f"Expected device='ad' for frontend /api/data 5xx, got {alert.device!r}"
    )


def test_to_canonical_frontend_other_target_not_relabeled() -> None:
    """frontend + target other than /api/data stays device=frontend."""
    import time

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    metric_result = {
        "metric": {
            "service_name": "frontend",
            "job": "opentelemetry-demo/frontend",
            "instance": "frontend:8080",
            "target": "/checkout",
            "status": "500",
        },
        "value": [time.time(), "0.12"],
    }
    alert = live._to_canonical(metric_result)
    assert alert.device == "frontend", (
        f"Expected device='frontend' for /checkout 5xx, got {alert.device!r}"
    )


def test_to_canonical_frontend_no_target_not_relabeled() -> None:
    """frontend with no target label stays device=frontend."""
    import time

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    metric_result = {
        "metric": {
            "service_name": "frontend",
            "job": "opentelemetry-demo/frontend",
            "instance": "frontend:8080",
        },
        "value": [time.time(), "0.05"],
    }
    alert = live._to_canonical(metric_result)
    assert alert.device == "frontend", (
        f"Expected device='frontend' with no target label, got {alert.device!r}"
    )


def test_to_canonical_non_frontend_with_api_data_not_relabeled() -> None:
    """Non-frontend device must never be relabeled even with target=/api/data."""
    import time

    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    metric_result = {
        "metric": {
            "service_name": "cart",
            "job": "opentelemetry-demo/cart",
            "instance": "cart:8080",
            "target": "/api/data",
        },
        "value": [time.time(), "0.50"],
    }
    alert = live._to_canonical(metric_result)
    assert alert.device == "cart", (
        f"Expected device='cart' unchanged, got {alert.device!r}"
    )


# ── PromQL window config ─────────────────────────────────────


def test_load_window_config_default_no_env_no_yaml(monkeypatch) -> None:
    """No env vars and missing yaml file returns hardcoded (5, 5)."""
    from unittest.mock import patch

    from mcp_tools.prometheus_mcp import _load_window_config

    monkeypatch.delenv("DETECTION_WINDOW_MINUTES", raising=False)
    monkeypatch.delenv("HEALTH_WINDOW_MINUTES", raising=False)

    with patch(
        "mcp_tools.prometheus_mcp.open",
        side_effect=FileNotFoundError,
    ):
        assert _load_window_config() == (5, 5)


def test_load_window_config_env_overrides_yaml(monkeypatch) -> None:
    """Environment variables take precedence over yaml values."""
    from unittest.mock import mock_open, patch

    from mcp_tools.prometheus_mcp import _load_window_config

    yaml_content = (
        "detection_window_minutes: 3\n"
        "health_window_minutes: 4\n"
    )
    monkeypatch.setenv("DETECTION_WINDOW_MINUTES", "2")
    monkeypatch.setenv("HEALTH_WINDOW_MINUTES", "3")
    with patch(
        "mcp_tools.prometheus_mcp.open",
        mock_open(read_data=yaml_content),
    ):
        assert _load_window_config() == (2, 3)


def test_load_window_config_yaml_overrides_default(monkeypatch) -> None:
    """Yaml values apply when env vars are unset."""
    from unittest.mock import mock_open, patch

    from mcp_tools.prometheus_mcp import _load_window_config

    yaml_content = (
        "detection_window_minutes: 3\n"
        "health_window_minutes: 4\n"
    )
    monkeypatch.delenv("DETECTION_WINDOW_MINUTES", raising=False)
    monkeypatch.delenv("HEALTH_WINDOW_MINUTES", raising=False)
    with patch(
        "mcp_tools.prometheus_mcp.open",
        mock_open(read_data=yaml_content),
    ):
        assert _load_window_config() == (3, 4)


def test_load_window_config_split_precedence(monkeypatch) -> None:
    """Env wins on detection; yaml wins on health when only detection env set."""
    from unittest.mock import mock_open, patch

    from mcp_tools.prometheus_mcp import _load_window_config

    yaml_content = (
        "detection_window_minutes: 3\n"
        "health_window_minutes: 4\n"
    )
    monkeypatch.setenv("DETECTION_WINDOW_MINUTES", "2")
    monkeypatch.delenv("HEALTH_WINDOW_MINUTES", raising=False)
    with patch(
        "mcp_tools.prometheus_mcp.open",
        mock_open(read_data=yaml_content),
    ):
        assert _load_window_config() == (2, 4)


def test_load_window_config_bad_env_falls_back_to_yaml(monkeypatch) -> None:
    """Invalid env values fall back to yaml without raising."""
    from unittest.mock import mock_open, patch

    from mcp_tools.prometheus_mcp import _load_window_config

    yaml_content = (
        "detection_window_minutes: 3\n"
        "health_window_minutes: 4\n"
    )
    monkeypatch.setenv("DETECTION_WINDOW_MINUTES", "abc")
    monkeypatch.setenv("HEALTH_WINDOW_MINUTES", "xyz")
    with patch(
        "mcp_tools.prometheus_mcp.open",
        mock_open(read_data=yaml_content),
    ):
        assert _load_window_config() == (3, 4)


def test_load_window_config_bad_yaml_falls_back_to_five(monkeypatch) -> None:
    """Invalid yaml values fall back to hardcoded 5 without raising."""
    from unittest.mock import mock_open, patch

    from mcp_tools.prometheus_mcp import _load_window_config

    yaml_content = (
        "detection_window_minutes: foo\n"
        "health_window_minutes: bar\n"
    )
    monkeypatch.delenv("DETECTION_WINDOW_MINUTES", raising=False)
    monkeypatch.delenv("HEALTH_WINDOW_MINUTES", raising=False)
    with patch(
        "mcp_tools.prometheus_mcp.open",
        mock_open(read_data=yaml_content),
    ):
        assert _load_window_config() == (5, 5)


def test_build_breach_queries_five_minute_window() -> None:
    """_build_breach_queries('5m') returns four queries with correct shape."""
    from mcp_tools.prometheus_mcp import PrometheusMCP

    live = PrometheusMCP(base_url="http://localhost:1")
    result = live._build_breach_queries("5m")
    assert len(result) == 4
    assert "[5m]" in result[0]
    assert "[5m]" in result[1]
    assert "[5m]" in result[2]
    assert result[3] == 'up{job=~"opentelemetry-demo/.*"} == 0'
