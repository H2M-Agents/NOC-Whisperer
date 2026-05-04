"""Tests for SQLite incident store."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident
from orchestrator.incident_store import IncidentStore


def _sample_alert(alert_id: str, device: str = "cart") -> CanonicalAlert:
    return CanonicalAlert(
        alert_id=alert_id,
        timestamp=datetime.now(timezone.utc),
        domain="application",
        severity="major",
        device=device,
        metric="http_error_rate",
        message="errors elevated",
        source_system="prometheus",
        value=10.0,
        threshold=5.0,
        confidence=0.9,
        raw_payload={"k": "v"},
    )


def _sample_incident(
    *,
    incident_id: str | None = None,
    status: str = "open",
    updated_at: datetime | None = None,
    preliminary: bool = False,
    confirmed: bool = False,
) -> Incident:
    now = updated_at or datetime.now(timezone.utc)
    return Incident(
        incident_id=incident_id or str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        status=status,
        root_cause_device="valkey-cart",
        incident_title="Cache degradation",
        affected_services=["cart", "checkout"],
        confidence=0.75,
        recommended_action="Failover read replicas",
        alerts=[_sample_alert(str(uuid.uuid4()))],
        preliminary_advisory_sent=preliminary,
        confirmed_advisory_sent=confirmed,
    )


def test_import() -> None:
    """IncidentStore imports."""
    assert IncidentStore is not None


@pytest.mark.asyncio
async def test_upsert_and_get_incident_round_trip() -> None:
    """Create incident, upsert, reload — all fields match."""
    store = IncidentStore(":memory:")
    original = _sample_incident()
    await store.upsert(original)
    loaded = store.get_incident(original.incident_id)
    assert loaded is not None
    assert loaded.incident_id == original.incident_id
    assert loaded.status == original.status
    assert loaded.root_cause_device == original.root_cause_device
    assert loaded.incident_title == original.incident_title
    assert loaded.affected_services == original.affected_services
    assert loaded.confidence == pytest.approx(original.confidence)
    assert loaded.recommended_action == original.recommended_action
    assert len(loaded.alerts) == len(original.alerts)
    assert loaded.alerts[0].alert_id == original.alerts[0].alert_id
    assert loaded.preliminary_advisory_sent == original.preliminary_advisory_sent
    assert loaded.confirmed_advisory_sent == original.confirmed_advisory_sent


@pytest.mark.asyncio
async def test_get_open_incidents_filters_status() -> None:
    """Only open incidents are returned from get_open_incidents."""
    store = IncidentStore(":memory:")
    open_inc = _sample_incident(status="open")
    closed_inc = _sample_incident(status="resolved")
    await store.upsert(open_inc)
    await store.upsert(closed_inc)
    open_list = store.get_open_incidents()
    assert len(open_list) == 1
    assert open_list[0].incident_id == open_inc.incident_id


def test_get_incident_missing_returns_none() -> None:
    """Unknown id yields None."""
    store = IncidentStore(":memory:")
    assert store.get_incident("does-not-exist") is None


@pytest.mark.asyncio
async def test_mark_advisory_sent_preliminary_and_confirmed() -> None:
    """Advisory flags update independently."""
    store = IncidentStore(":memory:")
    inc = _sample_incident()
    await store.upsert(inc)
    await store.mark_advisory_sent(inc.incident_id, "preliminary")
    after_pre = store.get_incident(inc.incident_id)
    assert after_pre is not None
    assert after_pre.preliminary_advisory_sent is True
    assert after_pre.confirmed_advisory_sent is False
    await store.mark_advisory_sent(inc.incident_id, "confirmed")
    after_conf = store.get_incident(inc.incident_id)
    assert after_conf is not None
    assert after_conf.confirmed_advisory_sent is True


@pytest.mark.asyncio
async def test_mark_advisory_sent_invalid_type_raises() -> None:
    """Invalid advisory_type raises ValueError."""
    store = IncidentStore(":memory:")
    inc = _sample_incident()
    await store.upsert(inc)
    with pytest.raises(ValueError):
        await store.mark_advisory_sent(inc.incident_id, "draft")


@pytest.mark.asyncio
async def test_get_recent_resolved_respects_window() -> None:
    """Resolved incidents outside window are excluded."""
    store = IncidentStore(":memory:")
    recent = _sample_incident(
        status="resolved",
        updated_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    old = _sample_incident(
        status="resolved",
        updated_at=datetime.now(timezone.utc) - timedelta(hours=48),
    )
    await store.upsert(recent)
    await store.upsert(old)
    recent_list = store.get_recent_resolved(hours=24)
    ids = {i.incident_id for i in recent_list}
    assert recent.incident_id in ids
    assert old.incident_id not in ids


@pytest.mark.asyncio
async def test_incident_to_dict_roundtrip_via_store() -> None:
    """Incident serialization survives store persistence."""
    store = IncidentStore(":memory:")
    inc = _sample_incident()
    await store.upsert(inc)
    loaded = store.get_incident(inc.incident_id)
    assert loaded is not None
    restored = Incident.from_dict(loaded.to_dict())
    assert restored.incident_id == inc.incident_id
    assert restored.alerts[0].device == inc.alerts[0].device
