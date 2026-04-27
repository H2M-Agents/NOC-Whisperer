"""Unit tests for Node Exporter MCP live and mock implementations."""


def test_to_canonical_produces_valid_canonical_alert() -> None:
    import time
    from datetime import datetime

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.node_exporter_mcp import NodeExporterMCP

    live = NodeExporterMCP(prometheus_base_url="http://localhost:1")
    mock_metric_result = {
        "metric": {"instance": "node-a:9100", "job": "node"},
        "value": [time.time(), "92.5"],
    }

    alert = live._to_canonical(mock_metric_result, "cpu_utilization_percent")
    assert isinstance(alert, CanonicalAlert)
    assert alert.domain == "infrastructure"
    assert alert.source_system == "node_exporter"
    assert alert.metric == "cpu_utilization_percent"
    assert alert.device == "node-a:9100"
    assert isinstance(alert.timestamp, datetime)
    assert isinstance(alert.raw_payload, dict)
    assert alert.severity in {"critical", "major", "minor", "warning"}


def test_import() -> None:
    from mcp_tools.node_exporter_mcp import NodeExporterMCP
    from mcp_tools.mocks.mock_node_exporter_mcp import MockNodeExporterMCP

    assert NodeExporterMCP is not None
    assert MockNodeExporterMCP is not None


def test_mock_returns_empty_by_default() -> None:
    from mcp_tools.mocks.mock_node_exporter_mcp import MockNodeExporterMCP

    mock = MockNodeExporterMCP()
    result = mock.get_host_alerts()
    assert isinstance(result, list)
    assert len(result) == 0


def test_mock_returns_injected_alerts() -> None:
    from datetime import datetime

    from adapters.canonical_alert import CanonicalAlert
    from mcp_tools.mocks.mock_node_exporter_mcp import MockNodeExporterMCP

    alert = CanonicalAlert(
        alert_id="test-node-001",
        timestamp=datetime.utcnow(),
        domain="infrastructure",
        severity="critical",
        device="node-a",
        metric="cpu_utilization_percent",
        message="host cpu high",
        source_system="node_exporter",
        value=95.0,
        threshold=90.0,
        confidence=0.95,
        raw_payload={},
    )
    mock = MockNodeExporterMCP(scenario_alerts=[alert])
    result = mock.get_host_alerts()
    assert len(result) == 1
    assert result[0].alert_id == "test-node-001"


def test_mock_health_check_true() -> None:
    from mcp_tools.mocks.mock_node_exporter_mcp import MockNodeExporterMCP

    mock = MockNodeExporterMCP()
    assert mock.health_check() is True


def test_live_health_check_fails_gracefully() -> None:
    from mcp_tools.node_exporter_mcp import NodeExporterMCP

    live = NodeExporterMCP(prometheus_base_url="http://localhost:1")
    result = live.health_check()
    assert result is False


def test_live_get_host_alerts_fails_gracefully() -> None:
    from mcp_tools.node_exporter_mcp import NodeExporterMCP

    live = NodeExporterMCP(prometheus_base_url="http://localhost:1")
    result = live.get_host_alerts()
    assert isinstance(result, list)
    assert len(result) == 0
