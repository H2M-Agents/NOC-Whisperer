"""Lightweight tests for BatchReconciler wiring."""

from __future__ import annotations

import inspect

from orchestrator.batch_reconciler import BatchReconciler


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
