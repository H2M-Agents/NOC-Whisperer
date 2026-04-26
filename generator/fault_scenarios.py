"""Fault scenario dataclass definitions for synthetic incident generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


_VALID_INITIATING_DOMAINS: set[str] = {
    "infrastructure",
    "service_mesh",
    "application",
    "dependency",
}
_VALID_TEMPORAL_PATTERNS: set[str] = {
    "simultaneous",
    "sequential",
    "gradual",
    "sudden_at_time_boundary",
    "gradual_then_sudden",
}
_ALERT_TEMPLATE_REQUIRED_KEYS: set[str] = {
    "domain",
    "severity",
    "device",
    "metric",
    "message_template",
    "value_range",
}


@dataclass
class FaultScenario:
    """Represents one synthetic fault scenario template."""

    scenario_id: str
    name: str
    initiating_fault_domain: str
    initiating_fault_type: str
    initiating_device: str
    cascade_chain: List[str]
    alert_templates: List[dict]
    temporal_pattern: str
    noise_alert_domains: List[str]
    ground_truth: dict

    def __post_init__(self) -> None:
        """Validate scenario fields and alert template shape."""
        if self.initiating_fault_domain not in _VALID_INITIATING_DOMAINS:
            raise ValueError(
                "initiating_fault_domain must be one of "
                f"{sorted(_VALID_INITIATING_DOMAINS)}."
            )

        if self.temporal_pattern not in _VALID_TEMPORAL_PATTERNS:
            raise ValueError(
                "temporal_pattern must be one of "
                f"{sorted(_VALID_TEMPORAL_PATTERNS)}."
            )

        if not isinstance(self.initiating_device, str) or not self.initiating_device.strip():
            raise ValueError("initiating_device must be a non-empty string.")

        if not isinstance(self.alert_templates, list) or len(self.alert_templates) == 0:
            raise ValueError("alert_templates must be a non-empty list.")

        for template in self.alert_templates:
            if not isinstance(template, dict):
                raise ValueError("each alert_template must be a dict.")
            missing = _ALERT_TEMPLATE_REQUIRED_KEYS - set(template.keys())
            if missing:
                raise ValueError(
                    "each alert_template dict must have keys "
                    f"{sorted(_ALERT_TEMPLATE_REQUIRED_KEYS)}."
                )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this scenario to a dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "initiating_fault_domain": self.initiating_fault_domain,
            "initiating_fault_type": self.initiating_fault_type,
            "initiating_device": self.initiating_device,
            "cascade_chain": list(self.cascade_chain),
            "alert_templates": [dict(template) for template in self.alert_templates],
            "temporal_pattern": self.temporal_pattern,
            "noise_alert_domains": list(self.noise_alert_domains),
            "ground_truth": dict(self.ground_truth),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FaultScenario:
        """Deserialize a scenario from dictionary data."""
        return cls(
            scenario_id=str(data["scenario_id"]),
            name=str(data["name"]),
            initiating_fault_domain=str(data["initiating_fault_domain"]),
            initiating_fault_type=str(data["initiating_fault_type"]),
            initiating_device=str(data["initiating_device"]),
            cascade_chain=[str(item) for item in data["cascade_chain"]],
            alert_templates=[dict(item) for item in data["alert_templates"]],
            temporal_pattern=str(data["temporal_pattern"]),
            noise_alert_domains=[str(item) for item in data["noise_alert_domains"]],
            ground_truth=dict(data["ground_truth"]),
        )
