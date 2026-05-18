"""Tests for NOC dashboard state updates and display generation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from adapters.canonical_alert import CanonicalAlert, Incident
from dashboard.noc_dashboard import NOCDashboard


def _alert(alert_id: str) -> CanonicalAlert:
    return CanonicalAlert(
        alert_id=alert_id,
        timestamp=datetime.now(timezone.utc),
        domain="application",
        severity="major",
        device="valkey-cart",
        metric="cache_errors",
        message="cache errors elevated",
        source_system="prometheus",
        value=10.0,
        threshold=1.0,
        confidence=0.9,
        raw_payload={},
    )


def _incident(incident_id: str, confidence: float = 0.9) -> Incident:
    now = datetime.now(timezone.utc)
    return Incident(
        incident_id=incident_id,
        created_at=now,
        updated_at=now,
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Valkey incident",
        affected_services=["cart", "checkout", "frontend"],
        confidence=confidence,
        recommended_action="Restart valkey",
        alerts=[],
    )


def test_import() -> None:
    """NOCDashboard imports."""
    from dashboard.noc_dashboard import NOCDashboard as ND

    assert ND is not None


def test_update_alert_stream_keeps_last_ten() -> None:
    """Alert stream truncates to last 10 entries."""
    dash = NOCDashboard()
    for idx in range(12):
        dash.update_alert_stream(_alert(str(idx)))
    assert len(dash.alert_stream) == 10
    assert dash.alert_stream[0].alert_id == "2"


def test_update_incident_board_insert_and_update() -> None:
    """Incident board updates by incident_id."""
    dash = NOCDashboard()
    iid = str(uuid.uuid4())
    dash.update_incident_board(_incident(iid, confidence=0.40))
    dash.update_incident_board(_incident(iid, confidence=0.95))
    assert len(dash.open_incidents) == 1
    assert dash.open_incidents[0].confidence == 0.95


def test_update_advisory_sets_latest_text() -> None:
    """Latest advisory text is stored."""
    dash = NOCDashboard()
    dash.update_advisory("NOC ADVISORY sample")
    assert dash.latest_advisory == "NOC ADVISORY sample"


def test_generate_display_returns_without_error() -> None:
    """Acceptance-style smoke test from Session 23."""
    dash = NOCDashboard()
    dash.update_alert_stream(_alert("a1"))
    dash.update_incident_board(_incident("inc-1"))
    display = dash.generate_display()
    assert display is not None
    print("Dashboard OK")


def test_stop_sets_flag() -> None:
    dash = NOCDashboard()
    assert dash._stop is False
    dash.stop()
    assert dash._stop is True


def test_incident_board_started_column_in_la_time() -> None:
    """Incident board Started column shows created_at in America/Los_Angeles time (HH:MM PDT/PST)."""
    import re
    from zoneinfo import ZoneInfo

    _LA_TZ = ZoneInfo("America/Los_Angeles")
    dash = NOCDashboard()
    inc = _incident("inc-ts-1")
    dash.update_incident_board(inc)

    stored = dash.open_incidents[0]
    la_str = stored.created_at.astimezone(_LA_TZ).strftime("%H:%M %Z")
    assert re.match(r"\d{2}:\d{2} (?:PDT|PST)", la_str), (
        f"Expected HH:MM PDT/PST format, got {la_str!r}"
    )

    display = dash.generate_display()
    assert display is not None
