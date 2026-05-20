from unittest.mock import MagicMock, patch

import pytest

import agents.adk_tools.communications_tools as ct


def _make_store(preliminary_sent=False, confirmed_sent=False):
    incident = MagicMock()
    incident.preliminary_advisory_sent = preliminary_sent
    incident.confirmed_advisory_sent = confirmed_sent
    store = MagicMock()
    store.get_incident.return_value = incident
    store._mark_advisory_sent_sync = MagicMock()
    return store, incident


def _make_comms(advisory_text="NOC ADVISORY 2026-05-17 14:00 PDT"):
    comms = MagicMock()
    comms.generate.return_value = advisory_text
    return comms


# ── guard tests (Bug A) ───────────────────────────────────────────


def test_generate_advisory_preliminary_guard_blocks_resend():
    store, _ = _make_store(preliminary_sent=True)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        result = ct.generate_advisory("INC-001", "preliminary")
    assert result == "already_sent:preliminary"
    store._mark_advisory_sent_sync.assert_not_called()


def test_generate_advisory_confirmed_guard_blocks_resend():
    store, _ = _make_store(confirmed_sent=True)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        result = ct.generate_advisory("INC-001", "confirmed")
    assert result == "already_sent:confirmed"
    store._mark_advisory_sent_sync.assert_not_called()


def test_generate_advisory_preliminary_fires_when_not_sent():
    store, _ = _make_store(preliminary_sent=False)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        result = ct.generate_advisory("INC-001", "preliminary")
    assert result != ""
    assert "already_sent" not in result


def test_generate_advisory_confirmed_fires_when_not_sent():
    store, _ = _make_store(confirmed_sent=False)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        result = ct.generate_advisory("INC-001", "confirmed")
    assert result != ""
    assert "already_sent" not in result


# ── flag persistence tests (Bug B) ───────────────────────────────


def test_generate_advisory_persists_preliminary_flag():
    store, _ = _make_store(preliminary_sent=False)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        ct.generate_advisory("INC-001", "preliminary")
    store._mark_advisory_sent_sync.assert_called_once_with("INC-001", "preliminary")


def test_generate_advisory_persists_confirmed_flag():
    store, _ = _make_store(confirmed_sent=False)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        ct.generate_advisory("INC-001", "confirmed")
    # Fix calls _mark_advisory_sent_sync twice:
    # once for confirmed, once for preliminary (REMINDER-017)
    assert store._mark_advisory_sent_sync.call_count == 2
    store._mark_advisory_sent_sync.assert_any_call("INC-001", "confirmed")
    store._mark_advisory_sent_sync.assert_any_call("INC-001", "preliminary")


def test_generate_advisory_does_not_persist_resolution_flag():
    store, _ = _make_store()
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        ct.generate_advisory("INC-001", "resolution")
    store._mark_advisory_sent_sync.assert_not_called()


# ── error path tests ─────────────────────────────────────────────


def test_generate_advisory_returns_empty_when_comms_none():
    with patch.object(ct, "_communications", None):
        result = ct.generate_advisory("INC-001", "preliminary")
    assert result == ""


def test_generate_advisory_returns_empty_when_store_none():
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", None
    ):
        result = ct.generate_advisory("INC-001", "preliminary")
    assert result == ""


def test_generate_advisory_returns_empty_when_incident_not_found():
    store = MagicMock()
    store.get_incident.return_value = None
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        result = ct.generate_advisory("INC-999", "preliminary")
    assert result == ""


def test_generate_advisory_updates_dashboard_on_success():
    store, _ = _make_store()
    dashboard = MagicMock()
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", dashboard):
        ct.generate_advisory("INC-001", "preliminary")
    dashboard.update_advisory.assert_called_once()


def test_generate_advisory_confirmed_also_marks_preliminary():
    """REMINDER-017: confirmed advisory also marks preliminary so the panel cannot downgrade."""
    store, _ = _make_store(preliminary_sent=False, confirmed_sent=False)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        ct.generate_advisory("INC-001", "confirmed")

    store._mark_advisory_sent_sync.assert_any_call("INC-001", "preliminary")
    store._mark_advisory_sent_sync.assert_any_call("INC-001", "confirmed")
    assert store._mark_advisory_sent_sync.call_count == 2


def test_generate_advisory_preliminary_not_double_marked():
    """Generating preliminary only marks preliminary once — double-mark is exclusive to confirmed."""
    store, _ = _make_store(preliminary_sent=False, confirmed_sent=False)
    with patch.object(ct, "_communications", _make_comms()), patch.object(
        ct, "_store", store
    ), patch.object(ct, "_dashboard", None):
        ct.generate_advisory("INC-001", "preliminary")

    store._mark_advisory_sent_sync.assert_called_once_with("INC-001", "preliminary")
