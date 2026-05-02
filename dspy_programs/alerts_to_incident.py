"""DSPy signature and correlator stubs for alert-to-incident reasoning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import dspy


class AlertsToIncident(dspy.Signature):
    """Correlate a cluster of alerts into a unified incident report."""

    alert_cluster = dspy.InputField(
        desc="JSON list of canonical alerts — timestamp, domain, severity, "
        "device, metric, message, value"
    )
    topology_context = dspy.InputField(
        desc="JSON dict of service dependency relationships for devices "
        "in the alert cluster"
    )
    root_cause_device = dspy.OutputField(
        desc="Specific device most likely responsible for triggering the cascade"
    )
    incident_title = dspy.OutputField(
        desc="One-line description suitable for a NOC dashboard"
    )
    affected_services = dspy.OutputField(
        desc="Comma-separated list of downstream affected services"
    )
    confidence = dspy.OutputField(
        desc="Score 0.0-1.0 followed by one sentence of reasoning"
    )
    recommended_action = dspy.OutputField(
        desc="Single most important action for a NOC engineer right now"
    )


def _normalize_alert_cluster(alert_cluster: Any) -> str:
    """Normalize alert_cluster input to a JSON string for heuristics."""
    if isinstance(alert_cluster, str):
        return alert_cluster
    return json.dumps(alert_cluster, sort_keys=True)


def _normalize_topology(topology_context: Any) -> Dict[str, Any]:
    """Normalize topology_context to a dict."""
    if isinstance(topology_context, dict):
        return topology_context
    if isinstance(topology_context, str):
        try:
            loaded = json.loads(topology_context)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


class BaselineCorrelator:
    """Hand-written baseline correlator (no DSPy optimization, no external LLM in predict)."""

    def predict(self, alert_cluster: Any, topology_context: Any) -> Dict[str, str]:
        """Return the five incident fields using lightweight string heuristics."""
        raw = _normalize_alert_cluster(alert_cluster)
        topo = _normalize_topology(topology_context)
        device_hint = "unknown-device"
        try:
            parsed: List[Any] = json.loads(raw) if raw.strip().startswith("[") else []
            if parsed and isinstance(parsed[0], dict) and "device" in parsed[0]:
                device_hint = str(parsed[0].get("device", device_hint))
        except (json.JSONDecodeError, TypeError, IndexError):
            for token in ("valkey-cart", "cart", "checkout", "frontend"):
                if token in raw:
                    device_hint = token
                    break

        affected = []
        for key, meta in topo.items():
            if isinstance(meta, dict):
                downstream = meta.get("feeds_into") or []
                if isinstance(downstream, list):
                    affected.extend(str(x) for x in downstream)
        affected_str = ",".join(sorted(set(affected))) if affected else "unknown"

        return {
            "root_cause_device": device_hint,
            "incident_title": f"Incident involving {device_hint}",
            "affected_services": affected_str,
            "confidence": "0.55 Heuristic baseline without LLM generation.",
            "recommended_action": "Page on-call and validate downstream services from topology.",
        }


class DSPyCorrelator:
    """DSPy-style correlator stub; loads compiled JSON when present."""

    def __init__(self, compiled_path: str | None = None) -> None:
        """Store optional path to compiled DSPy program JSON."""
        default_path = Path(__file__).resolve().with_name("alerts_to_incident_compiled.json")
        self._compiled_path = Path(compiled_path) if compiled_path else default_path

    def predict(self, alert_cluster: Any, topology_context: Any) -> Dict[str, str]:
        """Predict incident fields; falls back to baseline when no compiled program."""
        if self._compiled_path.is_file():
            _ = self._compiled_path.read_text(encoding="utf-8")
            return BaselineCorrelator().predict(alert_cluster, topology_context)
        return BaselineCorrelator().predict(alert_cluster, topology_context)
