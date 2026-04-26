"""Tests for FaultScenario dataclass validation and serialization."""

import pytest

from generator.fault_scenarios import FaultScenario


def _valid_alert_template() -> dict:
    return {
        "domain": "infrastructure",
        "severity": "critical",
        "device": "valkey-cart",
        "metric": "valkey_cache_miss_ratio",
        "message_template": "Cache miss ratio high on {device}",
        "value_range": [0.9, 1.0],
    }


def _valid_fault_scenario() -> FaultScenario:
    return FaultScenario(
        scenario_id="s1",
        name="Valkey Cache Failure",
        initiating_fault_domain="infrastructure",
        initiating_fault_type="cache_failure",
        initiating_device="valkey-cart",
        cascade_chain=["valkey-cart", "cart", "checkout", "frontend"],
        alert_templates=[_valid_alert_template()],
        temporal_pattern="simultaneous",
        noise_alert_domains=["service_mesh"],
        ground_truth={
            "root_cause_device": "valkey-cart",
            "initiating_domain": "infrastructure",
            "affected_services": ["cart", "checkout", "frontend"],
            "cascade_type": "load_amplification",
            "correlation_window_seconds": 120,
        },
    )


def test_import() -> None:
    from generator.fault_scenarios import FaultScenario as ImportedFaultScenario

    assert ImportedFaultScenario is not None


def test_valid_creation() -> None:
    scenario = _valid_fault_scenario()
    assert scenario.scenario_id == "s1"
    assert scenario.name == "Valkey Cache Failure"
    assert scenario.initiating_fault_domain == "infrastructure"
    assert scenario.initiating_fault_type == "cache_failure"
    assert scenario.initiating_device == "valkey-cart"
    assert scenario.cascade_chain == ["valkey-cart", "cart", "checkout", "frontend"]
    assert len(scenario.alert_templates) == 1
    assert scenario.temporal_pattern == "simultaneous"
    assert scenario.noise_alert_domains == ["service_mesh"]
    assert scenario.ground_truth["root_cause_device"] == "valkey-cart"


def test_invalid_domain() -> None:
    with pytest.raises(ValueError):
        FaultScenario(
            scenario_id="s1",
            name="Invalid Domain",
            initiating_fault_domain="invalid",
            initiating_fault_type="cache_failure",
            initiating_device="valkey-cart",
            cascade_chain=["valkey-cart"],
            alert_templates=[_valid_alert_template()],
            temporal_pattern="simultaneous",
            noise_alert_domains=["application"],
            ground_truth={},
        )


def test_invalid_temporal_pattern() -> None:
    with pytest.raises(ValueError):
        FaultScenario(
            scenario_id="s1",
            name="Invalid Pattern",
            initiating_fault_domain="infrastructure",
            initiating_fault_type="cache_failure",
            initiating_device="valkey-cart",
            cascade_chain=["valkey-cart"],
            alert_templates=[_valid_alert_template()],
            temporal_pattern="unknown",
            noise_alert_domains=["application"],
            ground_truth={},
        )


def test_empty_alert_templates() -> None:
    with pytest.raises(ValueError):
        FaultScenario(
            scenario_id="s1",
            name="Empty Templates",
            initiating_fault_domain="infrastructure",
            initiating_fault_type="cache_failure",
            initiating_device="valkey-cart",
            cascade_chain=["valkey-cart"],
            alert_templates=[],
            temporal_pattern="simultaneous",
            noise_alert_domains=["application"],
            ground_truth={},
        )


def test_alert_template_missing_key() -> None:
    bad_template = _valid_alert_template()
    bad_template.pop("domain")
    with pytest.raises(ValueError):
        FaultScenario(
            scenario_id="s1",
            name="Bad Template",
            initiating_fault_domain="infrastructure",
            initiating_fault_type="cache_failure",
            initiating_device="valkey-cart",
            cascade_chain=["valkey-cart"],
            alert_templates=[bad_template],
            temporal_pattern="simultaneous",
            noise_alert_domains=["application"],
            ground_truth={},
        )


def test_roundtrip() -> None:
    scenario = _valid_fault_scenario()
    rebuilt = FaultScenario.from_dict(scenario.to_dict())
    assert rebuilt.scenario_id == scenario.scenario_id
    assert rebuilt.name == scenario.name
