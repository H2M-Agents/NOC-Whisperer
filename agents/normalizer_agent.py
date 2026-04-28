"""Normalizer agent stub for development fallback."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from adapters.canonical_alert import CanonicalAlert


class NormalizerAgent:
    """Stub normalizer agent that falls back to Ollama in development."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        """Initialize with optional model path and load backend."""
        self.model_path = model_path
        self.backend = self.load_model(model_path)

    def load_model(self, model_path: Optional[str]) -> str:
        """Load local fine-tuned model if available, otherwise Ollama fallback."""
        candidate = Path(model_path) if model_path else Path("models/normalizer_final_locked")
        if candidate.exists():
            return str(candidate)
        return "ollama/llama3.1:8b"

    def process(self, raw_payload: Dict[str, Any], source_system: str) -> CanonicalAlert:
        """Convert raw payload to CanonicalAlert using stub classification rules."""
        metric = str(raw_payload.get("metric", "unknown_metric"))
        value = float(raw_payload.get("value", 0.0))
        device = str(raw_payload.get("device", "unknown-device"))
        message = str(raw_payload.get("message", f"Normalized event from {source_system}"))

        if source_system == "node_exporter":
            domain = "infrastructure"
        elif source_system == "prometheus":
            domain = "service_mesh"
        else:
            domain = "application"

        severity = "major" if value >= 1 else "minor"

        return CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            domain=domain,
            severity=severity,
            device=device,
            metric=metric,
            message=message,
            source_system=source_system,
            value=value,
            threshold=float(raw_payload.get("threshold", 0.0)),
            confidence=0.90,
            raw_payload=raw_payload,
        )
