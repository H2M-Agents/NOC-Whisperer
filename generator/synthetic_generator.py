"""Synthetic alert storm generator driven by fault scenarios."""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from adapters.canonical_alert import CanonicalAlert
from generator.fault_scenarios import ALL_SCENARIOS, FaultScenario


class ScenarioDrivenGenerator:
    """Generates correlated and noise alerts from scenario templates."""

    def __init__(self) -> None:
        """Load valid device names from topology graph."""
        graph_path = Path("topology/otel_demo_graph.json")
        with graph_path.open("r", encoding="utf-8") as f:
            graph = json.load(f)
        self.valid_devices: List[str] = list(graph.keys())

    def generate_storm(
        self,
        scenario: FaultScenario,
        noise_ratio: float = 0.3,
        base_time: datetime = None,
    ) -> dict:
        """
        Generate a correlated alert storm from a known root cause scenario.
        Returns:
          {
            "alerts": List[CanonicalAlert],  # sorted by timestamp
            "ground_truth": dict,            # from scenario.ground_truth
            "scenario_name": str,            # scenario.name
            "incident_id": str               # UUID shared by all correlated alerts
          }
        Noise alerts have alert.incident_id = None.
        Correlated alerts share the same incident_id UUID.
        """
        if base_time is None:
            base_time = datetime.utcnow()

        incident_id = str(uuid.UUID(int=random.getrandbits(128)))
        correlated_alerts: List[CanonicalAlert] = []

        for idx, template in enumerate(scenario.alert_templates):
            timestamp = self._apply_temporal_pattern(base_time, idx, scenario.temporal_pattern)
            correlated_alerts.append(
                self._instantiate_template(template=template, incident_id=incident_id, timestamp=timestamp)
            )

        noise_count = max(0, int(len(correlated_alerts) * noise_ratio))
        noise_alerts = [
            self._generate_noise_alert(base_time=base_time, valid_devices=self.valid_devices)
            for _ in range(noise_count)
        ]

        all_alerts = correlated_alerts + noise_alerts
        all_alerts.sort(key=lambda alert: alert.timestamp)

        return {
            "alerts": all_alerts,
            "ground_truth": dict(scenario.ground_truth),
            "scenario_name": scenario.name,
            "incident_id": incident_id,
        }

    def generate_dataset(
        self,
        num_incidents: int,
        noise_ratio: float,
        scenarios: List[FaultScenario] = None,
        random_seed: int = 42,
    ) -> List[dict]:
        """
        Generate a list of alert storms.
        scenarios defaults to ALL_SCENARIOS if None.
        Cycles through scenarios evenly across num_incidents.
        Sets random.seed(random_seed) before generation — never changes.
        """
        random.seed(random_seed)
        scenario_pool = scenarios if scenarios is not None else ALL_SCENARIOS
        dataset: List[dict] = []

        for i in range(num_incidents):
            scenario = scenario_pool[i % len(scenario_pool)]
            base_time = datetime.utcnow() + timedelta(minutes=i)
            dataset.append(
                self.generate_storm(scenario=scenario, noise_ratio=noise_ratio, base_time=base_time)
            )
        return dataset

    def _apply_temporal_pattern(
        self,
        base_time: datetime,
        alert_index: int,
        pattern: str,
    ) -> datetime:
        """
        Apply timing offset to base_time based on pattern and alert_index.
        Implement all 5 patterns:

        simultaneous:
          All alerts within 0-5 seconds of base_time
          timedelta(seconds=random.randint(0, 5))

        sequential:
          Each alert 30 seconds apart with 0-15s jitter
          timedelta(seconds=alert_index * 30 + random.randint(0, 15))

        gradual:
          Each alert 2 minutes apart with 0-30s jitter
          timedelta(seconds=alert_index * 120 + random.randint(0, 30))

        sudden_at_time_boundary:
          First alert at base_time, rest within 10s of each other
          timedelta(seconds=alert_index * 10 + random.randint(0, 5))

        gradual_then_sudden:
          First half: 2 minutes apart
          Second half: 10 seconds apart
          Use alert_index to determine which half
        """
        if pattern == "simultaneous":
            return base_time + timedelta(seconds=random.randint(0, 5))
        if pattern == "sequential":
            return base_time + timedelta(seconds=alert_index * 30 + random.randint(0, 15))
        if pattern == "gradual":
            return base_time + timedelta(seconds=alert_index * 120 + random.randint(0, 30))
        if pattern == "sudden_at_time_boundary":
            return base_time + timedelta(seconds=alert_index * 10 + random.randint(0, 5))
        if pattern == "gradual_then_sudden":
            split_point = 4
            if alert_index < split_point:
                return base_time + timedelta(seconds=alert_index * 120 + random.randint(0, 30))
            return base_time + timedelta(
                seconds=split_point * 120 + (alert_index - split_point) * 10 + random.randint(0, 5)
            )
        return base_time + timedelta(seconds=random.randint(0, 5))

    def _generate_noise_alert(
        self,
        base_time: datetime,
        valid_devices: List[str],
    ) -> CanonicalAlert:
        """
        Generate a single noise alert unrelated to any scenario.
        - Pick a random device from valid_devices
        - Pick a random domain from [infrastructure, service_mesh, application]
        - Pick a random severity from [minor, warning]
          (noise alerts are never critical or major)
        - incident_id must be None
        - source_system = "synthetic_noise"
        - timestamp within 0-300 seconds of base_time
        """
        device = random.choice(valid_devices)
        domain = random.choice(["infrastructure", "service_mesh", "application"])
        severity = random.choice(["minor", "warning"])
        value = random.uniform(1.0, 10.0)

        alert = CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=base_time + timedelta(seconds=random.randint(0, 300)),
            domain=domain,
            severity=severity,
            device=device,
            metric="synthetic_noise_metric",
            message=f"Noise alert on {device}",
            source_system="synthetic_noise",
            value=value,
            threshold=value * 0.9,
            confidence=random.uniform(0.5, 0.8),
            raw_payload={"noise": True},
        )
        alert.incident_id = None
        return alert

    def _instantiate_template(
        self,
        template: dict,
        incident_id: str,
        timestamp: datetime,
    ) -> CanonicalAlert:
        """
        Convert an alert_template dict into a CanonicalAlert.
        - value = random.uniform(template["value_range"][0],
                                 template["value_range"][1])
        - message = template["message_template"].format(value=value)
        - alert_id = str(uuid.uuid4())
        - source_system = "synthetic"
        - threshold = value * 0.9  (threshold slightly below the value)
        - confidence = random.uniform(0.85, 0.99)
        """
        value = random.uniform(template["value_range"][0], template["value_range"][1])
        message = template["message_template"].format(value=value)

        alert = CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=timestamp,
            domain=template["domain"],
            severity=template["severity"],
            device=template["device"],
            metric=template["metric"],
            message=message,
            source_system="synthetic",
            value=value,
            threshold=value * 0.9,
            confidence=random.uniform(0.85, 0.99),
            raw_payload={"template": dict(template)},
        )
        alert.incident_id = incident_id
        return alert
