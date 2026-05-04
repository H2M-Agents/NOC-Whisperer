"""Async streaming orchestration: poll MCP tools, normalize, triage, correlate, persist, advisories."""

from __future__ import annotations

import asyncio
from typing import Any, List

from adapters.canonical_alert import CanonicalAlert, Incident


class StreamingPipeline:
    """Poll MCP sources on an interval, dedupe alerts, run agents, persist, fire advisories."""

    def __init__(
        self,
        mcp_tools: List[Any],
        normalizer: Any,
        triage: Any,
        correlation: Any,
        communications: Any,
        incident_store: Any,
        dashboard: Any,
    ) -> None:
        """Wire tools, agents, SQLite store, and dashboard."""
        self.mcp_tools = mcp_tools
        self.normalizer = normalizer
        self.triage = triage
        self.correlation = correlation
        self.communications = communications
        self.store = incident_store
        self.dashboard = dashboard
        self.seen_alert_ids: set[str] = set()

    async def streaming_loop(self) -> None:
        """Continuously poll MCP tools every 15 seconds and process new alerts."""
        while True:
            raw_alerts: List[Any] = []
            for tool in self.mcp_tools:
                raw_alerts.extend(self._alerts_from_tool(tool))

            new_alerts = [a for a in raw_alerts if self._alert_id(a) not in self.seen_alert_ids]

            for alert in new_alerts:
                self.seen_alert_ids.add(self._alert_id(alert))
                await self.process_alert(alert)

            await asyncio.sleep(15)

    def _alert_id(self, raw_alert: Any) -> str:
        """Stable id for deduplication."""
        if isinstance(raw_alert, CanonicalAlert):
            return str(raw_alert.alert_id)
        aid = getattr(raw_alert, "alert_id", None)
        return str(aid) if aid is not None else str(id(raw_alert))

    def _canonicalize(self, raw_alert: Any) -> CanonicalAlert:
        """Normalize MCP output to CanonicalAlert (identity if already canonical)."""
        if isinstance(raw_alert, CanonicalAlert):
            return raw_alert
        raise TypeError(
            "StreamingPipeline expects CanonicalAlert instances from MCP tools in this build."
        )

    def _alerts_from_tool(self, tool: Any) -> List[Any]:
        """Collect alerts from heterogeneous MCP surfaces; swallow errors per contract."""
        try:
            if hasattr(tool, "get_alerts") and callable(getattr(tool, "get_alerts")):
                return list(tool.get_alerts())
            if hasattr(tool, "get_alerts_since"):
                return list(tool.get_alerts_since(30))
            if hasattr(tool, "get_threshold_breaches"):
                return list(tool.get_threshold_breaches())
            if hasattr(tool, "get_error_spans"):
                return list(tool.get_error_spans(30))
            if hasattr(tool, "get_host_alerts"):
                return list(tool.get_host_alerts())
        except Exception:
            return []
        return []

    async def process_alert(self, raw_alert: Any) -> None:
        """Run Normalizer→Triage→Correlation→Store→dashboard→advisory checks."""
        canonical = self._canonicalize(raw_alert)
        decision = self.triage.route(canonical)
        incident = self.correlation.correlate(decision)
        await self.store.upsert(incident)
        self.dashboard.update_alert_stream(canonical)
        self.dashboard.update_incident_board(incident)
        await self.check_advisory_triggers(incident)

    async def check_advisory_triggers(self, incident: Incident) -> None:
        """Apply advisory trigger logic from CONTEXT.md (preliminary vs confirmed thresholds)."""
        if incident.confidence > 0.50 and not incident.preliminary_advisory_sent:
            advisory = self.communications.generate(incident, advisory_type="preliminary")
            self.dashboard.update_advisory(advisory)
            incident.preliminary_advisory_sent = True
            await self.store.upsert(incident)

        elif incident.confidence > 0.85 and not incident.confirmed_advisory_sent:
            advisory = self.communications.generate(incident, advisory_type="confirmed")
            self.dashboard.update_advisory(advisory)
            incident.confirmed_advisory_sent = True
            await self.store.upsert(incident)
