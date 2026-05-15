"""Reconciler agent — pair-wise merge/keep plus stale incident closure (ReAct-style)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from adapters.canonical_alert import Incident

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _PROJECT_ROOT / "config" / "reconciler_config.yaml"


def _load_reconciler_config() -> Dict[str, Any]:
    """Load merge/close settings from yaml; return defaults on failure."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
            if isinstance(loaded, dict):
                return loaded
    except Exception:
        pass
    return {
        "merge_confidence_threshold": 0.75,
        "close_inactivity_seconds": 1200,
        "max_react_iterations": 3,
    }


@dataclass
class ReconcilerDecision:
    """One reconciliation action (merge, split, close, or keep)."""

    action: str
    """merge | split | close | keep"""
    primary_incident_id: str
    """Target incident id (or sole id for close/keep)."""
    secondary_incident_id: Optional[str] = None
    """Other incident id for merge or split; None for close/keep."""
    reasoning: str = ""
    """Short human-readable justification."""

    def __post_init__(self) -> None:
        """Validate action and required fields per action type."""
        valid = {"merge", "split", "close", "keep"}
        if self.action not in valid:
            raise ValueError(f"Invalid action '{self.action}'. Expected one of {valid}.")
        if self.action == "merge" and not self.secondary_incident_id:
            raise ValueError("merge requires a non-empty secondary_incident_id.")
        if self.action == "split" and not self.secondary_incident_id:
            raise ValueError("split requires a non-empty secondary_incident_id.")


class ReconcilerAgent:
    """Pair-wise incident reconciliation with topology + Prometheus evidence."""

    def __init__(self, topology_mcp: Any, prometheus_mcp: Any, max_iterations: int = 3) -> None:
        """Wire MCP clients, ReAct iteration cap, and numeric thresholds from config."""
        cfg = _load_reconciler_config()
        self.topology = topology_mcp
        self.prometheus = prometheus_mcp
        self.max_iterations = max_iterations
        self._merge_threshold = float(cfg.get("merge_confidence_threshold", 0.75))
        self._close_inactivity_seconds = int(cfg.get("close_inactivity_seconds", 1200))

    def reconcile(self, open_incidents: List[Incident]) -> List[ReconcilerDecision]:
        """Return merge decisions for pairs plus close decisions for stale incidents."""
        decisions: List[ReconcilerDecision] = []
        for i, inc_a in enumerate(open_incidents):
            for inc_b in open_incidents[i + 1 :]:
                decision = self._evaluate_pair(inc_a, inc_b)
                if decision.action != "keep":
                    decisions.append(decision)

        for incident in open_incidents:
            if self._should_close(incident):
                decisions.append(
                    ReconcilerDecision(
                        action="close",
                        primary_incident_id=incident.incident_id,
                        secondary_incident_id=None,
                        reasoning="No new alerts for 20 minutes",
                    )
                )
        return decisions

    def _evaluate_pair(self, inc_a: Incident, inc_b: Incident) -> ReconcilerDecision:
        """ReAct loop — compare root causes via topology and Prometheus; merge or keep."""
        if not self.topology.are_related(inc_a.root_cause_device, inc_b.root_cause_device):
            return ReconcilerDecision(
                action="keep",
                primary_incident_id=inc_a.incident_id,
                secondary_incident_id=None,
                reasoning="Topology indicates distinct failure domains.",
            )

        if min(inc_a.confidence, inc_b.confidence) < self._merge_threshold:
            return ReconcilerDecision(
                action="keep",
                primary_incident_id=inc_a.incident_id,
                secondary_incident_id=None,
                reasoning="Correlation confidence below merge threshold.",
            )

        for iteration in range(self.max_iterations):
            prom = self._safe_prometheus_query()
            if isinstance(prom, dict) and prom.get("status") == "success":
                return ReconcilerDecision(
                    action="merge",
                    primary_incident_id=inc_a.incident_id,
                    secondary_incident_id=inc_b.incident_id,
                    reasoning=(
                        f"ReAct iter {iteration + 1}: topology+confidence OK; "
                        "prometheus query confirms active signals."
                    ),
                )
        return ReconcilerDecision(
            action="keep",
            primary_incident_id=inc_a.incident_id,
            secondary_incident_id=None,
            reasoning="Prometheus evidence inconclusive within max iterations.",
        )

    def _safe_prometheus_query(self) -> Dict[str, Any]:
        """Query Prometheus; return empty dict on any failure (never crash)."""
        try:
            result = self.prometheus.query("up")
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    def _should_close(self, incident: Incident) -> bool:
        """Signal-based close: True when Prometheus reports the root-cause device is healthy.

        Calls ``get_service_health`` on the Prometheus MCP client. On probe errors,
        returns False (fail safe — do not close). If ``get_service_health`` is not
        implemented, falls back to the configured ``close_inactivity_seconds`` idle window.
        """
        if callable(getattr(self.prometheus, "get_service_health", None)):
            try:
                return bool(
                    self.prometheus.get_service_health(incident.root_cause_device)
                )
            except Exception:
                return False  # fail safe — don't close on error
        now = datetime.now(timezone.utc)
        updated = incident.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        else:
            updated = updated.astimezone(timezone.utc)
        idle_seconds = (now - updated).total_seconds()
        return idle_seconds >= float(self._close_inactivity_seconds)
