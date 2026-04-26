"""Tests for scenario-driven synthetic alert generator."""

from __future__ import annotations

import json

from generator.fault_scenarios import VALKEY_CART_CASCADE_SCENARIO
from generator.synthetic_generator import ScenarioDrivenGenerator


def test_import() -> None:
    from generator.synthetic_generator import ScenarioDrivenGenerator as ImportedGenerator

    assert ImportedGenerator is not None


def test_generate_storm_returns_correct_keys() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    assert "alerts" in storm
    assert "ground_truth" in storm
    assert "scenario_name" in storm
    assert "incident_id" in storm


def test_generate_storm_alert_count() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO, noise_ratio=0.3)
    assert len(storm["alerts"]) >= 7


def test_correlated_alerts_share_incident_id() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    incident_id = storm["incident_id"]
    correlated = [a for a in storm["alerts"] if a.incident_id is not None]
    assert len(correlated) >= 7
    for alert in correlated:
        assert alert.incident_id == incident_id


def test_noise_alerts_have_no_incident_id() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO, noise_ratio=0.4)
    noise = [a for a in storm["alerts"] if a.incident_id is None]
    assert len(noise) > 0
    for alert in noise:
        assert alert.incident_id is None


def test_noise_alerts_are_never_critical_or_major() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO, noise_ratio=0.5)
    noise = [a for a in storm["alerts"] if a.incident_id is None]
    for alert in noise:
        assert alert.severity in {"minor", "warning"}


def test_alerts_sorted_by_timestamp() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    timestamps = [a.timestamp for a in storm["alerts"]]
    assert timestamps == sorted(timestamps)


def test_ground_truth_matches_scenario() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    assert storm["ground_truth"]["root_cause_device"] == "valkey-cart"
    assert storm["scenario_name"] == VALKEY_CART_CASCADE_SCENARIO.name


def test_all_devices_valid() -> None:
    gen = ScenarioDrivenGenerator()
    with open("topology/otel_demo_graph.json", "r", encoding="utf-8") as f:
        graph = json.load(f)
    valid_devices = set(graph.keys())
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    for alert in storm["alerts"]:
        assert alert.device in valid_devices, f"Invalid device: {alert.device}"


def test_all_alert_domains_valid() -> None:
    gen = ScenarioDrivenGenerator()
    valid_domains = {"infrastructure", "service_mesh", "application"}
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    for alert in storm["alerts"]:
        assert alert.domain in valid_domains


def test_generate_dataset_count() -> None:
    gen2 = ScenarioDrivenGenerator()
    dataset = gen2.generate_dataset(num_incidents=10, noise_ratio=0.3, random_seed=42)
    assert len(dataset) == 10


def test_generate_dataset_reproducible() -> None:
    gen_a = ScenarioDrivenGenerator()
    gen_b = ScenarioDrivenGenerator()
    dataset_a = gen_a.generate_dataset(10, 0.3, random_seed=42)
    dataset_b = gen_b.generate_dataset(10, 0.3, random_seed=42)
    assert dataset_a[0]["incident_id"] == dataset_b[0]["incident_id"]
    assert len(dataset_a[0]["alerts"]) == len(dataset_b[0]["alerts"])


def test_temporal_pattern_sequential_ordering() -> None:
    gen = ScenarioDrivenGenerator()
    storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)
    correlated = [a for a in storm["alerts"] if a.incident_id is not None]
    for i in range(1, len(correlated)):
        delta = (correlated[i].timestamp - correlated[i - 1].timestamp).total_seconds()
        assert delta >= 15, f"Alert {i} too close to previous: {delta}s"
