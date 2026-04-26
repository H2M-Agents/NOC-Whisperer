"""Tests for instantiated fault scenarios."""

from __future__ import annotations

import json

from generator.fault_scenarios import ALL_SCENARIOS, VALKEY_CART_CASCADE_SCENARIO


def test_all_scenarios_count() -> None:
    assert len(ALL_SCENARIOS) == 12


def test_valkey_cart_is_first() -> None:
    assert ALL_SCENARIOS[0].scenario_id == "scenario_01"


def test_valkey_cart_root_cause() -> None:
    assert VALKEY_CART_CASCADE_SCENARIO.ground_truth["root_cause_device"] == "valkey-cart"


def test_valkey_cart_affected_services() -> None:
    services = VALKEY_CART_CASCADE_SCENARIO.ground_truth["affected_services"]
    assert "cart" in services
    assert "checkout" in services
    assert "frontend" in services


def test_valkey_cart_alert_templates_count() -> None:
    assert len(VALKEY_CART_CASCADE_SCENARIO.alert_templates) >= 7


def test_valkey_cart_initiating_device() -> None:
    assert VALKEY_CART_CASCADE_SCENARIO.initiating_device == "valkey-cart"


def test_all_devices_valid() -> None:
    with open("topology/otel_demo_graph.json", "r", encoding="utf-8") as f:
        graph = json.load(f)
    valid_devices = set(graph.keys())
    for scenario in ALL_SCENARIOS:
        assert scenario.initiating_device in valid_devices, (
            f"{scenario.name}: initiating_device '{scenario.initiating_device}' not in graph"
        )
        for device in scenario.cascade_chain:
            assert device in valid_devices, (
                f"{scenario.name}: cascade device '{device}' not in graph"
            )
        for template in scenario.alert_templates:
            assert template["device"] in valid_devices, (
                f"{scenario.name}: template device '{template['device']}' not in graph"
            )


def test_all_scenarios_have_required_ground_truth_keys() -> None:
    required_keys = {
        "root_cause_device",
        "initiating_domain",
        "affected_services",
        "cascade_type",
        "correlation_window_seconds",
    }
    for scenario in ALL_SCENARIOS:
        for key in required_keys:
            assert key in scenario.ground_truth, (
                f"{scenario.name}: missing ground_truth key '{key}'"
            )


def test_all_scenarios_have_min_alert_templates() -> None:
    for scenario in ALL_SCENARIOS:
        assert len(scenario.alert_templates) >= 3, (
            f"{scenario.name}: has fewer than 3 alert_templates"
        )


def test_all_temporal_patterns_valid() -> None:
    valid_patterns = {
        "simultaneous",
        "sequential",
        "gradual",
        "sudden_at_time_boundary",
        "gradual_then_sudden",
    }
    for scenario in ALL_SCENARIOS:
        assert scenario.temporal_pattern in valid_patterns, (
            f"{scenario.name}: invalid temporal_pattern '{scenario.temporal_pattern}'"
        )


def test_all_scenarios_unique_ids() -> None:
    ids = [s.scenario_id for s in ALL_SCENARIOS]
    assert len(ids) == len(set(ids)), "Duplicate scenario_ids found"


def test_no_duplicate_names() -> None:
    names = [s.name for s in ALL_SCENARIOS]
    assert len(names) == len(set(names)), "Duplicate scenario names found"
