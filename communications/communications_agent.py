"""Communications agent stub — locked model path resolution or Ollama fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from adapters.canonical_alert import Incident


class CommunicationsAgent:
    """Stub communications agent that prefers a local checkpoint or falls back to Ollama."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        """Initialize with optional model path and resolve inference backend."""
        self.model_path = model_path
        self.backend = self._resolve_backend(model_path)

    def _resolve_backend(self, model_path: Optional[str]) -> str:
        """Load locked model directory when present; otherwise use Ollama fallback."""
        candidate = Path(model_path) if model_path else Path("models/communications_final_locked")
        if candidate.exists():
            return str(candidate)
        return "ollama/llama3.1:8b"

    def generate(self, incident: Incident, advisory_type: str = "preliminary") -> str:
        """Format prompt from incident fields and return a stub advisory string."""
        prompt = self._format_prompt(incident, advisory_type)
        # Stub: production would load transformers/Ollama using self.backend.
        return (
            f"{prompt}\n---\n"
            f"[CommunicationsAgent stub — backend={self.backend} — replace with inference]"
        )

    def _format_prompt(self, incident: Incident, advisory_type: str) -> str:
        """Format instructions for preliminary (investigating) vs confirmed (imperative) advisories."""
        kind = (advisory_type or "preliminary").strip().lower()
        services = ", ".join(incident.affected_services)
        header = (
            f"Incident title: {incident.incident_title}\n"
            f"Suspected / root-cause device: {incident.root_cause_device}\n"
            f"Affected services: {services}\n"
            f"Confidence: {incident.confidence:.0%}\n"
        )
        if kind == "confirmed":
            return (
                f"{header}"
                "Task: Write a CONFIRMED NOC advisory. Use imperative ACTION REQUIRED lines. "
                "State impact and remediation as firm facts (confirmed), not speculation.\n"
            )
        return (
            f"{header}"
            "Task: Write a PRELIMINARY NOC advisory. Emphasize INVESTIGATING status and "
            "SUSPECTED root cause — avoid stating definitive confirmation.\n"
        )
