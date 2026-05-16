"""Lightweight tests for BatchReconciler wiring."""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adapters.canonical_alert import CanonicalAlert, Incident
from orchestrator.batch_reconciler import BatchReconciler
from orchestrator.reconciler_agent import ReconcilerDecision


class _FakeReconciler:
    """Minimal reconciler stub."""

    def reconcile(self, open_incidents):  # noqa: ANN001
        """Return no decisions."""
        return []


class _FakeStore:
    """Minimal store stub."""

    def get_open_incidents(self):  # noqa: ANN001
        """Return empty open list."""
        return []


def _open_incident(incident_id: str = "inc-close-1") -> Incident:
    """Single open incident for close-decision tests."""
    when = datetime.now(timezone.utc)
    return Incident(
        incident_id=incident_id,
        created_at=when,
        updated_at=when,
        status="open",
        root_cause_device="valkey-cart",
        incident_title="Cart cascade",
        affected_services=["cart"],
        confidence=0.9,
        recommended_action="investigate",
        alerts=[
            CanonicalAlert(
                alert_id="alert-1",
                timestamp=when,
                domain="application",
                severity="major",
                device="valkey-cart",
                metric="m",
                message="msg",
                source_system="synthetic",
                value=1.0,
                threshold=0.5,
                confidence=0.9,
                raw_payload={},
            )
        ],
    )


def _close_decision(incident_id: str = "inc-close-1") -> ReconcilerDecision:
    """Reconciler close decision targeting the given incident."""
    return ReconcilerDecision(
        action="close",
        primary_incident_id=incident_id,
        secondary_incident_id=None,
        reasoning="Service healthy per Prometheus",
    )


async def _run_one_batch_iteration(batch: BatchReconciler) -> None:
    """Run batch_loop until the first sleep, then cancel via CancelledError."""

    async def _cancel_on_sleep(_interval: float) -> None:
        raise asyncio.CancelledError()

    with patch(
        "orchestrator.batch_reconciler.asyncio.sleep",
        side_effect=_cancel_on_sleep,
    ):
        with pytest.raises(asyncio.CancelledError):
            await batch.batch_loop()


def test_import() -> None:
    """BatchReconciler imports."""
    from orchestrator.batch_reconciler import BatchReconciler as BR

    assert BR is not None


def test_instantiation() -> None:
    """Constructor assigns reconciler, store, and interval."""
    rec = _FakeReconciler()
    store = _FakeStore()
    batch = BatchReconciler(rec, store, interval_seconds=15)
    assert batch.reconciler is rec
    assert batch.store is store
    assert batch.interval == 15


def test_batch_loop_is_coroutine() -> None:
    """batch_loop is an async method (coroutine function)."""
    assert inspect.iscoroutinefunction(BatchReconciler.batch_loop)


@pytest.mark.asyncio
async def test_close_decision_marks_incident_closed() -> None:
    """Close decision sets incident status closed and persists via store.upsert."""
    incident = _open_incident()
    store = MagicMock()
    store.get_open_incidents.return_value = [incident]
    store.upsert = AsyncMock()
    reconciler = MagicMock()
    reconciler.reconcile.return_value = [_close_decision()]
    batch = BatchReconciler(reconciler, store, interval_seconds=0)

    await _run_one_batch_iteration(batch)

    assert incident.status == "closed"
    store.upsert.assert_awaited_once_with(incident)


@pytest.mark.asyncio
async def test_close_decision_fires_resolution_advisory() -> None:
    """Close decision triggers resolution advisory on communications and dashboard."""
    incident = _open_incident()
    store = MagicMock()
    store.get_open_incidents.return_value = [incident]
    store.upsert = AsyncMock()
    reconciler = MagicMock()
    reconciler.reconcile.return_value = [_close_decision()]
    communications = MagicMock()
    communications.generate.return_value = "SERVICE RESTORED advisory"
    dashboard = MagicMock()
    batch = BatchReconciler(
        reconciler,
        store,
        communications=communications,
        dashboard=dashboard,
        interval_seconds=0,
    )

    await _run_one_batch_iteration(batch)

    communications.generate.assert_called_once_with(incident, advisory_type="resolution")
    dashboard.update_advisory.assert_called_once_with("SERVICE RESTORED advisory")


@pytest.mark.asyncio
async def test_close_decision_no_advisory_without_communications() -> None:
    """Close still persists when communications and dashboard are not wired."""
    incident = _open_incident()
    store = MagicMock()
    store.get_open_incidents.return_value = [incident]
    store.upsert = AsyncMock()
    reconciler = MagicMock()
    reconciler.reconcile.return_value = [_close_decision()]
    batch = BatchReconciler(reconciler, store, interval_seconds=0)

    await _run_one_batch_iteration(batch)

    assert incident.status == "closed"
    store.upsert.assert_awaited_once_with(incident)
