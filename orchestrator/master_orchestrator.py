"""Entry point: run the streaming alert pipeline and batch reconciler concurrently."""

from __future__ import annotations

import asyncio
from typing import Any


class MasterOrchestrator:
    """Schedules `asyncio.gather` over the hot path (streaming) and batch reconciler loop."""

    def __init__(self, streaming_pipeline: Any, batch_reconciler: Any) -> None:
        """Store references to the live streaming pipeline and batch reconciler instances."""
        self.streaming = streaming_pipeline
        self.batch = batch_reconciler

    async def run(self) -> None:
        """Run both asyncio loops in parallel until cancellation or process exit."""
        await asyncio.gather(
            self.streaming.streaming_loop(),
            self.batch.batch_loop(),
        )

    def start(self) -> None:
        """Block on a new event loop and execute :meth:`run`."""
        asyncio.run(self.run())
