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
    """DSPy correlator that loads and runs a compiled program when available."""

    def __init__(self) -> None:
        self._compiled_path = Path(__file__).parent / "alerts_to_incident_compiled.json"
        self._program = None
        self._load_program()

    def _load_program(self) -> None:
        if self._compiled_path.is_file():
            try:
                import dspy
                import os

                from dotenv import load_dotenv

                load_dotenv()

                api_base = os.environ.get("OPENAI_API_BASE")
                api_key = os.environ.get("OPENAI_API_KEY")
                model = os.environ.get("DSPy_MODEL", "openai/gpt-oss-20b")

                if not api_base or not api_key:
                    print(
                        "DSPyCorrelator: OPENAI_API_BASE or OPENAI_API_KEY "
                        "not set — skipping compiled program load. "
                        "Set these in .env to enable optimized inference."
                    )
                    self._program = None
                    return

                lm = dspy.LM(
                    f"openai/{model}",
                    api_base=api_base,
                    api_key=api_key,
                    temperature=0.0,
                )
                dspy.configure(lm=lm)

                program = dspy.ChainOfThought(AlertsToIncident)
                program.load(str(self._compiled_path))
                self._program = program
                print("DSPyCorrelator: compiled program loaded successfully")
            except Exception as e:
                print(f"DSPyCorrelator: failed to load program: {e}")
                self._program = None

    def predict(self, alert_cluster: Any, topology_context: Any) -> Dict[str, str]:
        if self._program is not None:
            try:
                result = self._program(
                    alert_cluster=alert_cluster,
                    topology_context=topology_context,
                )
                return {
                    "root_cause_device": result.root_cause_device,
                    "incident_title": result.incident_title,
                    "affected_services": result.affected_services,
                    "confidence": result.confidence,
                    "recommended_action": result.recommended_action,
                }
            except Exception:
                pass
        return BaselineCorrelator().predict(alert_cluster, topology_context)
