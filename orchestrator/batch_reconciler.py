"""Periodic batch reconciler loop — optional stub execution for close decisions."""

from __future__ import annotations

import asyncio
from typing import Any


class BatchReconciler:
    """Polls open incidents on a fixed interval and applies reconciler decisions (stub for close)."""

    def __init__(self, reconciler_agent: Any, incident_store: Any, interval_seconds: int = 30) -> None:
        """Wire the reconciler, shared store, and sleep interval between passes."""
        self.reconciler = reconciler_agent
        self.store = incident_store
        self.interval = interval_seconds

    async def batch_loop(self) -> None:
        """Run forever: reconcile when multiple open incidents exist; never crash the loop body."""
        while True:
            try:
                open_incidents = self.store.get_open_incidents()
                if len(open_incidents) > 1:
                    decisions = self.reconciler.reconcile(open_incidents)
                    for decision in decisions:
                        if decision.action == "close":
                            # mark closed in store
                            pass
            except Exception:
                pass
            await asyncio.sleep(self.interval)
