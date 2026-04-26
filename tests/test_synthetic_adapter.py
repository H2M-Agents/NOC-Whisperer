"""Unit tests for adapters.synthetic_adapter."""

from adapters.canonical_alert import CanonicalAlert
from adapters.synthetic_adapter import SyntheticAdapter


def test_import() -> None:
    """SyntheticAdapter is importable."""
    assert SyntheticAdapter is not None


def test_returns_canonical_alert() -> None:
    """to_canonical returns a CanonicalAlert instance."""
    adapter = SyntheticAdapter()
    result = adapter.to_canonical({"anything": "ok"})
    assert isinstance(result, CanonicalAlert)


def test_hardcoded_values_are_valid() -> None:
    """Hardcoded stub values satisfy CanonicalAlert constraints."""
    adapter = SyntheticAdapter()
    result = adapter.to_canonical({"raw": "value"})

    assert result.domain == "infrastructure"
    assert result.severity == "major"
    assert result.source_system == "synthetic"
    assert result.alert_id == "synthetic-alert-1"
