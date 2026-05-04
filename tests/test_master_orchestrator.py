"""Tests for MasterOrchestrator — gather plumbing only (no infinite loops)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from orchestrator.master_orchestrator import MasterOrchestrator


class _ImmediateStream:
    """Stub streaming loop that finishes immediately."""

    def __init__(self) -> None:
        """Track invocation."""
        self.ran = False

    async def streaming_loop(self) -> None:
        """Mark ran for assertions."""
        self.ran = True


class _ImmediateBatch:
    """Stub batch loop that finishes immediately."""

    def __init__(self) -> None:
        """Track invocation."""
        self.ran = False

    async def batch_loop(self) -> None:
        """Mark ran for assertions."""
        self.ran = True


def test_import() -> None:
    """MasterOrchestrator imports."""
    from orchestrator.master_orchestrator import MasterOrchestrator as MO

    assert MO is not None


def test_init_wires_streaming_and_batch() -> None:
    """Constructor stores pipeline and batch reconciler."""
    stream = _ImmediateStream()
    batch = _ImmediateBatch()
    master = MasterOrchestrator(stream, batch)
    assert master.streaming is stream
    assert master.batch is batch


@pytest.mark.asyncio
async def test_run_gather_executes_both_loops() -> None:
    """run() awaits both async loop methods via asyncio.gather."""
    stream = _ImmediateStream()
    batch = _ImmediateBatch()
    master = MasterOrchestrator(stream, batch)
    await master.run()
    assert stream.ran is True
    assert batch.ran is True


def test_start_calls_asyncio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """start() delegates to asyncio.run(run())."""
    ran: dict[str, bool] = {}

    def fake_run(main: Any) -> None:
        ran["called"] = True
        assert asyncio.iscoroutine(main)
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main)
        finally:
            loop.close()

    monkeypatch.setattr(asyncio, "run", fake_run)
    master = MasterOrchestrator(_ImmediateStream(), _ImmediateBatch())
    master.start()
    assert ran.get("called") is True


def test_acceptance_master_orchestrator_ok() -> None:
    """Session 21 acceptance smoke."""
    print("Master orchestrator OK")
