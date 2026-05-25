from datetime import datetime, timedelta, timezone
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


# ── same-cycle duplicate guard tests ─────────────────────


def _make_open_incident(device: str, age_seconds: float = 10.0):
    """Return a mock Incident recent enough to trigger the guard."""
    inc = MagicMock()
    inc.root_cause_device = device
    inc.incident_id = "INC-EXISTING-001"
    inc.created_at = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    inc.preliminary_advisory_sent = False
    inc.confirmed_advisory_sent = False
    return inc


def test_same_cycle_duplicate_redirected_to_append():
    """Second action=new for same device within 60s becomes append."""
    existing = _make_open_incident("cart", age_seconds=10)
    mock_correlation = _make_mock_correlation(
        _make_mock_incident(preliminary_advisory_sent=False)
    )
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture_correlate(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture_correlate

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "new",
                "incident_id": None,
            }
        )

    assert captured["action"] == "append", (
        "Expected action=append for same-device duplicate within 60s"
    )
    assert captured["incident_id"] == "INC-EXISTING-001"


def test_same_cycle_duplicate_uses_existing_incident_id():
    """Redirected append uses the existing incident_id from store."""
    existing = _make_open_incident("cart", age_seconds=5)
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture(decision):
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "new",
                "incident_id": None,
            }
        )

    assert captured["incident_id"] == "INC-EXISTING-001"


def test_old_open_incident_still_redirected_to_append():
    """Any open incident with matching device redirects to append regardless of age.

    get_open_incidents() only returns open incidents so age is irrelevant.
    """
    existing = _make_open_incident("cart", age_seconds=300)
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "new",
                "incident_id": None,
            }
        )

    assert captured["action"] == "append", (
        "Expected action=append even for open incident older than 60s"
    )
    assert captured["incident_id"] == "INC-EXISTING-001"


def test_different_device_not_redirected():
    """action=new stays new when existing incident has different device."""
    existing = _make_open_incident("ad", age_seconds=5)
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "new",
                "incident_id": None,
            }
        )

    assert captured["action"] == "new", (
        "Expected action=new when existing incident has different device"
    )


def test_existing_append_not_affected_by_guard():
    """action=append with a valid incident_id
    that exists in the store skips the dedup
    scan — explicit id is preserved."""
    existing = _make_open_incident("cart", age_seconds=5)
    explicit = MagicMock()
    explicit.root_cause_device = "cart"
    explicit.incident_id = "INC-EXPLICIT-999"
    explicit.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    explicit.preliminary_advisory_sent = False
    explicit.confirmed_advisory_sent = False
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [
        existing,
        explicit,
    ]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "append",
                "incident_id": "INC-EXPLICIT-999",
            }
        )

    assert captured["action"] == "append"
    assert captured["incident_id"] == "INC-EXPLICIT-999"


def test_append_invalid_id_resolves_by_device():
    """append + invalid id resolves to the
    existing open incident for that device."""
    existing = MagicMock()
    existing.root_cause_device = "cart"
    existing.incident_id = "INC-CART-001"
    existing.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    existing.preliminary_advisory_sent = False
    existing.confirmed_advisory_sent = False
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "append",
                "incident_id": "INVALID-UUID-NOT-IN-STORE",
            }
        )

    assert captured["action"] == "append"
    assert captured["incident_id"] == "INC-CART-001"


def test_new_cart_alert_matches_valkey_cart_root():
    """action=new with alert device=cart
    appends to open valkey-cart incident
    via _INFRA_PAIRS match."""
    existing = MagicMock()
    existing.root_cause_device = "valkey-cart"
    existing.incident_id = "INC-VALKEY-001"
    existing.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    existing.preliminary_advisory_sent = False
    existing.confirmed_advisory_sent = False
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "new",
                "incident_id": None,
            }
        )

    assert captured["action"] == "append"
    assert captured["incident_id"] == "INC-VALKEY-001"


def test_cart_alert_does_not_merge_frontend_incident():
    """cart alert must not merge into an open
    frontend incident — topology isolation
    preserved for ad/frontend noise."""
    existing = MagicMock()
    existing.root_cause_device = "frontend"
    existing.incident_id = "INC-FRONTEND-001"
    existing.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    existing.preliminary_advisory_sent = False
    existing.confirmed_advisory_sent = False
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [existing]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "new",
                "incident_id": None,
            }
        )

    assert captured["action"] == "new"
    assert captured["incident_id"] != "INC-FRONTEND-001"


def test_append_valid_id_kept_when_in_store():
    """append with valid explicit id is kept
    even when another matching incident exists
    first in the open list."""
    first = _make_open_incident("cart", age_seconds=5)
    second = MagicMock()
    second.root_cause_device = "cart"
    second.incident_id = "INC-EXPLICIT-999"
    second.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    second.preliminary_advisory_sent = False
    second.confirmed_advisory_sent = False
    mock_correlation = _make_mock_correlation(_make_mock_incident())
    mock_correlation.store.get_open_incidents.return_value = [
        first,
        second,
    ]

    captured = {}

    def capture(decision):
        captured["action"] = decision.action
        captured["incident_id"] = decision.incident_id
        return _make_mock_incident()

    mock_correlation.correlate.side_effect = capture

    with patch(
        "agents.adk_tools.correlation_tools._correlation",
        mock_correlation,
    ):
        correlate_alert(
            **{
                **_CORRELATE_KWARGS,
                "device": "cart",
                "action": "append",
                "incident_id": "INC-EXPLICIT-999",
            }
        )

    assert captured["action"] == "append"
    assert captured["incident_id"] == "INC-EXPLICIT-999"
