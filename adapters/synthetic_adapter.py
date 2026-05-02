"""Stub adapter for synthetic alert payload conversion."""

from __future__ import annotations

from datetime import datetime, timezone

from adapters.canonical_alert import CanonicalAlert


class SyntheticAdapter:
    """Converts synthetic raw dict payloads into canonical alerts."""

    def to_canonical(self, raw_dict: dict) -> CanonicalAlert:
        """Return a hardcoded canonical alert for initial testing."""
        _ = raw_dict
        return CanonicalAlert(
            alert_id="synthetic-alert-1",
            timestamp=datetime.now(timezone.utc),
            domain="infrastructure",
            severity="major",
            device="synthetic-device",
            metric="synthetic_metric",
            message="Synthetic test alert",
            source_system="synthetic",
            value=1.0,
            threshold=0.5,
            confidence=0.99,
            raw_payload={"stub": True},
        )
