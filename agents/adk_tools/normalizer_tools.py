from __future__ import annotations

from typing import Any

from agents.normalizer_agent import NormalizerAgent

_normalizer: NormalizerAgent | None = None
_dashboard: Any = None


def init_normalizer(model_path: str | None = None) -> None:
    """Initialize the NormalizerAgent."""
    global _normalizer
    _normalizer = NormalizerAgent(model_path=model_path)


def init_dashboard(dashboard: Any) -> None:
    """Initialize dashboard reference for alert stream updates."""
    global _dashboard
    _dashboard = dashboard


def normalize_alert(
    device: str,
    metric: str,
    value: float,
    source_system: str,
    message: str = "",
    threshold: float = 0.0,
) -> dict[str, Any]:
    """STEP 2: Normalize a raw alert into canonical format.

    Call once for EACH alert from get_active_alerts().
    Returns dict with: alert_id, domain, severity, device,
    metric, confidence, timestamp.
    """
    if _normalizer is None:
        return {}
    raw = {
        "device": device,
        "metric": metric,
        "value": value,
        "message": message,
        "threshold": threshold,
    }
    alert = _normalizer.process(raw, source_system)
    if _dashboard is not None:
        try:
            _dashboard.update_alert_stream(alert)
        except Exception:
            pass
    return alert.to_dict()
