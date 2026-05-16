"""Tests for ADK normalizer tool wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import agents.adk_tools.normalizer_tools as normalizer_tools
from adapters.canonical_alert import CanonicalAlert


@pytest.fixture(autouse=True)
def _reset_normalizer() -> None:
    """Isolate module singleton between tests."""
    normalizer_tools._normalizer = None
    yield
    normalizer_tools._normalizer = None


def test_normalize_alert_returns_empty_when_not_initialized() -> None:
    """Uninitialized normalizer returns empty dict."""
    assert normalizer_tools.normalize_alert("cart", "m", 1.0, "prometheus") == {}


def test_normalize_alert_returns_dict_when_initialized() -> None:
    """Initialized normalizer returns canonical alert dict from process()."""
    when = datetime.now(timezone.utc)
    canonical = CanonicalAlert(
        alert_id="norm-1",
        timestamp=when,
        domain="service_mesh",
        severity="major",
        device="cart",
        metric="http_error_rate_per_min",
        message="msg",
        source_system="prometheus",
        value=25.0,
        threshold=20.0,
        confidence=0.88,
        raw_payload={},
    )
    mock_normalizer = MagicMock()
    mock_normalizer.process.return_value = canonical
    normalizer_tools._normalizer = mock_normalizer

    result = normalizer_tools.normalize_alert(
        device="cart",
        metric="http_error_rate_per_min",
        value=25.0,
        source_system="prometheus",
        message="msg",
        threshold=20.0,
    )

    assert result["alert_id"] == "norm-1"
    assert result["device"] == "cart"
    assert result["domain"] == "service_mesh"
    mock_normalizer.process.assert_called_once()
