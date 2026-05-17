"""Tests for REMINDER-015 — LA timezone prompts and stale date scrubbing in advisories."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from communications.communications_agent import (
    CommunicationsAgent,
    _STALE_DATE_RE,
    _la_now_str,
)

_LA_TZ = ZoneInfo("America/Los_Angeles")


# ── _la_now_str ───────────────────────────────────────────────────


def test_la_now_str_format() -> None:
    s = _la_now_str()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} (?:PDT|PST)", s), (
        f"Bad format: {s!r}"
    )


def test_la_now_str_contains_current_year() -> None:
    assert str(datetime.now(_LA_TZ).year) in _la_now_str()


def test_la_now_str_not_stale_2024() -> None:
    assert "2024" not in _la_now_str()


def test_la_now_str_not_stale_2023() -> None:
    assert "2023" not in _la_now_str()


def test_la_now_str_uses_zoneinfo_not_fixed_offset() -> None:
    dt = datetime.now(_LA_TZ)
    assert isinstance(dt.tzinfo, ZoneInfo), (
        "tzinfo must be ZoneInfo, not a fixed timedelta offset"
    )
    offset_h = dt.utcoffset().total_seconds() / 3600
    assert offset_h in (-7.0, -8.0), f"Unexpected offset: {offset_h}h"


# ── _STALE_DATE_RE ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "stale",
    [
        "2024-01-17 13:00 PST",
        "2023-10-04 17:18 PST",
        "2024-01-17 13:00 PDT",
        "2024-01-17 13:00",
        "2022-06-01 09:00 PT",
    ],
)
def test_stale_date_re_matches(stale: str) -> None:
    assert _STALE_DATE_RE.search(stale), f"Should match: {stale!r}"


@pytest.mark.parametrize(
    "safe",
    [
        "Next update: 60 seconds",
        "ACTION REQUIRED",
        "valkey-cart",
        "confidence: 91%",
        "NOC ADVISORY",
    ],
)
def test_stale_date_re_no_false_positive(safe: str) -> None:
    assert not _STALE_DATE_RE.search(safe), f"Should not match: {safe!r}"


# ── generate() post-processing ────────────────────────────────────


def _make_incident() -> MagicMock:
    inc = MagicMock()
    inc.incident_id = "INC-TEST-001"
    inc.incident_title = "Valkey-cart cache failure cascade"
    inc.root_cause_device = "valkey-cart"
    inc.affected_services = ["cart", "checkout", "frontend"]
    inc.confidence = 0.91
    inc.recommended_action = "Restart valkey-cart container"
    now = datetime.now(_LA_TZ)
    inc.created_at = now - timedelta(minutes=5)
    inc.updated_at = now
    return inc


_STALE_ADVISORY = (
    "NOC ADVISORY — 2024-01-17 13:00 PST\n"
    "STATUS: CONFIRMED\n"
    "ROOT CAUSE: valkey-cart confirmed\n"
    "Next update: On status change\n"
)


def test_generate_scrubs_stale_date() -> None:
    agent = CommunicationsAgent(model_path=None)
    with (
        patch.object(agent, "_infer_local", return_value=_STALE_ADVISORY),
        patch.object(agent, "_infer_ollama", return_value=_STALE_ADVISORY),
    ):
        out = agent.generate(_make_incident(), "confirmed")
    assert "2024-01-17" not in out


def test_generate_inserts_current_year() -> None:
    agent = CommunicationsAgent(model_path=None)
    with (
        patch.object(agent, "_infer_local", return_value=_STALE_ADVISORY),
        patch.object(agent, "_infer_ollama", return_value=_STALE_ADVISORY),
    ):
        out = agent.generate(_make_incident(), "confirmed")
    assert str(datetime.now(_LA_TZ).year) in out


def test_generate_preserves_non_date_content() -> None:
    agent = CommunicationsAgent(model_path=None)
    with (
        patch.object(agent, "_infer_local", return_value=_STALE_ADVISORY),
        patch.object(agent, "_infer_ollama", return_value=_STALE_ADVISORY),
    ):
        out = agent.generate(_make_incident(), "confirmed")
    assert "valkey-cart confirmed" in out
    assert "On status change" in out


def test_generate_scrubs_multiple_stale_dates() -> None:
    multi = (
        "NOC ADVISORY — 2024-01-17 13:00 PST\n"
        "PREVIOUS UPDATE: 2023-10-04 17:18 PST\n"
        "STATUS: CONFIRMED\n"
    )
    agent = CommunicationsAgent(model_path=None)
    with (
        patch.object(agent, "_infer_local", return_value=multi),
        patch.object(agent, "_infer_ollama", return_value=multi),
    ):
        out = agent.generate(_make_incident(), "confirmed")
    assert "2024" not in out
    assert "2023" not in out


def test_generate_clean_advisory_content_unchanged() -> None:
    clean = (
        "NOC ADVISORY\n"
        "STATUS: CONFIRMED\n"
        "ROOT CAUSE: valkey-cart confirmed\n"
    )
    agent = CommunicationsAgent(model_path=None)
    with (
        patch.object(agent, "_infer_local", return_value=clean),
        patch.object(agent, "_infer_ollama", return_value=clean),
    ):
        out = agent.generate(_make_incident(), "confirmed")
    assert "valkey-cart confirmed" in out


# ── prometheus_mcp.py timezone audit ──────────────────────────────


def test_prometheus_mcp_has_no_hardcoded_utc_offset() -> None:
    import pathlib

    text = pathlib.Path("mcp_tools/prometheus_mcp.py").read_text(encoding="utf-8")
    assert "timedelta(hours=-8)" not in text, (
        "prometheus_mcp.py must not hardcode UTC-8; CanonicalAlert timestamps must be UTC"
    )
    assert "timedelta(hours=-7)" not in text, (
        "prometheus_mcp.py must not hardcode UTC-7; CanonicalAlert timestamps must be UTC"
    )
