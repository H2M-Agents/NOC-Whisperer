"""Unit tests for Jaeger MCP live and mock implementations."""


def test_span_to_canonical_produces_valid_canonical_alert() -> None:
    from datetime import datetime

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.jaeger_mcp import JaegerMCP

    live = JaegerMCP(base_url="http://localhost:1")

    mock_span = {
        "traceID": "abc123",
        "spanID": "def456",
        "operationName": "checkout",
        "startTime": 1714000000000000,
        "duration": 5000000,
        "tags": [
            {"key": "error", "value": True},
            {"key": "http.status_code", "value": 500},
        ],
        "logs": [],
        "references": [],
    }
    mock_process_map = {
        "p1": {"serviceName": "checkout"},
    }
    mock_span["processID"] = "p1"

    alert = live._span_to_canonical(mock_span, mock_process_map)

    assert isinstance(alert, CanonicalAlert)
    assert alert.domain == "application"
    assert alert.source_system == "jaeger"
    assert alert.severity == "major"
    assert alert.device == "checkout"
    assert isinstance(alert.timestamp, datetime)
    assert getattr(alert, "incident_id", None) is None
    assert isinstance(alert.raw_payload, dict)


def test_span_to_canonical_severity_is_valid() -> None:
    from mcp_tools.jaeger_mcp import JaegerMCP

    live = JaegerMCP(base_url="http://localhost:1")
    mock_span = {
        "traceID": "abc123",
        "spanID": "def456",
        "operationName": "cart",
        "startTime": 1714000000000000,
        "duration": 3000000,
        "tags": [{"key": "error", "value": True}],
        "logs": [],
        "references": [],
        "processID": "p1",
    }
    mock_process_map = {"p1": {"serviceName": "cart"}}
    alert = live._span_to_canonical(mock_span, mock_process_map)
    assert alert.severity in {"critical", "major", "minor", "warning"}


def test_import() -> None:
    from mcp_tools.jaeger_mcp import JaegerMCP
    from mcp_tools.mocks.mock_jaeger_mcp import MockJaegerMCP

    assert JaegerMCP is not None
    assert MockJaegerMCP is not None


def test_mock_returns_empty_by_default() -> None:
    from mcp_tools.mocks.mock_jaeger_mcp import MockJaegerMCP

    mock = MockJaegerMCP()
    result = mock.get_error_spans()
    assert isinstance(result, list)
    assert len(result) == 0


def test_mock_returns_injected_alerts() -> None:
    from datetime import datetime, timezone

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.mocks.mock_jaeger_mcp import MockJaegerMCP

    alert = CanonicalAlert(
        alert_id="test-jaeger-001",
        timestamp=datetime.now(timezone.utc),
        domain="application",
        severity="major",
        device="checkout",
        metric="error.type",
        message="checkout span error",
        source_system="jaeger",
        value=1.0,
        threshold=0.0,
        confidence=0.95,
        raw_payload={},
    )
    mock = MockJaegerMCP(scenario_alerts=[alert])
    result = mock.get_error_spans()
    assert len(result) == 1
    assert result[0].alert_id == "test-jaeger-001"


def test_mock_health_check_true() -> None:
    from mcp_tools.mocks.mock_jaeger_mcp import MockJaegerMCP

    mock = MockJaegerMCP()
    assert mock.health_check() is True


def test_live_health_check_fails_gracefully() -> None:
    from mcp_tools.jaeger_mcp import JaegerMCP

    live = JaegerMCP(base_url="http://localhost:1")
    result = live.health_check()
    assert result is False


def test_live_get_error_spans_fails_gracefully() -> None:
    from mcp_tools.jaeger_mcp import JaegerMCP

    live = JaegerMCP(base_url="http://localhost:1")
    result = live.get_error_spans()
    assert isinstance(result, list)
    assert len(result) == 0
