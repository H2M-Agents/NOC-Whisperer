"""Periodic batch reconciler loop — optional stub execution for close decisions."""

from __future__ import annotations

import asyncio
from typing import Any


class BatchReconciler:
    """Polls open incidents on a fixed interval and applies reconciler decisions (stub for close)."""

    def __init__(
        self,
        reconciler_agent: Any,
        incident_store: Any,
        communications: Any | None = None,
        dashboard: Any | None = None,
        interval_seconds: int = 30,
    ) -> None:
        """Wire the reconciler, shared store, and sleep interval between passes."""
        self.reconciler = reconciler_agent
        self.store = incident_store
        self.communications = communications
        self.dashboard = dashboard
        self.interval = interval_seconds

    async def batch_loop(self) -> None:
        """Run forever: reconcile when multiple open incidents exist; never crash the loop body."""
        while True:
            try:
                open_incidents = self.store.get_open_incidents()
                if open_incidents:
                    print(f"\n[ReAct] Reconciler running on {len(open_incidents)} open incidents...")
                if len(open_incidents) >= 1:
                    decisions = self.reconciler.reconcile(open_incidents)
                    if decisions:
                        print(f"[ReAct] {len(decisions)} decisions made")
                        for d in decisions:
                            print(f"  → {d.action}: {d.reasoning}")
                    open_incidents_map = {i.incident_id: i for i in open_incidents}
                    for decision in decisions:
                        if decision.action == "close":
                            incident_id = decision.primary_incident_id
                            incident = open_incidents_map.get(incident_id)
                            if incident:
                                incident.status = "closed"
                                await self.store.upsert(incident)
                                print(
                                    f"  → Incident {incident_id[:8]} closed — service healthy"
                                )
                                if self.communications and self.dashboard:
                                    try:
                                        advisory = self.communications.generate(
                                            incident, advisory_type="resolution"
                                        )
                                        self.dashboard.update_advisory(advisory)
                                        print(f"\n{'=' * 60}")
                                        print("RESOLUTION ADVISORY FIRED:")
                                        print(advisory)
                                        print(f"{'=' * 60}\n")
                                    except Exception as e:
                                        print(f"  → Resolution advisory failed: {e}")
            except Exception as e:
                import traceback

                print(f"[ReAct ERROR] {e}")
                traceback.print_exc()
            await asyncio.sleep(self.interval)
