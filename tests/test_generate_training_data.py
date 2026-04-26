"""Tests for dataset generation script."""

from __future__ import annotations

import json
from pathlib import Path

from generator.fault_scenarios import ALL_SCENARIOS, VALKEY_CART_CASCADE_SCENARIO
from generator.synthetic_generator import ScenarioDrivenGenerator
from scripts.generate_training_data import serialize_storm


def _sample_storm() -> dict:
    gen = ScenarioDrivenGenerator()
    return gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO)


def generate_splits(
    train_count: int,
    val_count: int,
    test_count: int,
    output_dir: Path,
    noise_ratio_test: float = 0.4,
) -> None:
    """Generate train/val/test JSON files with configurable split sizes."""
    output_dir.mkdir(parents=True, exist_ok=True)
    gen = ScenarioDrivenGenerator()

    train = gen.generate_dataset(
        num_incidents=train_count,
        noise_ratio=0.3,
        scenarios=ALL_SCENARIOS,
        random_seed=42,
    )
    val = gen.generate_dataset(
        num_incidents=val_count,
        noise_ratio=0.3,
        scenarios=ALL_SCENARIOS,
        random_seed=43,
    )
    test = gen.generate_dataset(
        num_incidents=test_count,
        noise_ratio=noise_ratio_test,
        scenarios=ALL_SCENARIOS,
        random_seed=44,
    )

    with open(output_dir / "train.json", "w", encoding="utf-8") as f:
        json.dump([serialize_storm(s) for s in train], f, indent=2, default=str)
    with open(output_dir / "val.json", "w", encoding="utf-8") as f:
        json.dump([serialize_storm(s) for s in val], f, indent=2, default=str)
    with open(output_dir / "test.json", "w", encoding="utf-8") as f:
        json.dump([serialize_storm(s) for s in test], f, indent=2, default=str)


def test_import() -> None:
    from scripts.generate_training_data import serialize_storm as imported_serialize_storm

    assert imported_serialize_storm is not None


def test_serialize_storm_structure() -> None:
    storm = _sample_storm()
    serialized = serialize_storm(storm)
    assert "incident_id" in serialized
    assert "scenario_name" in serialized
    assert "ground_truth" in serialized
    assert "alerts" in serialized
    assert isinstance(serialized["alerts"], list)
    assert isinstance(serialized["alerts"][0], dict)


def test_serialize_storm_alerts_are_dicts() -> None:
    storm = _sample_storm()
    serialized = serialize_storm(storm)
    for alert in serialized["alerts"]:
        assert isinstance(alert, dict)
        assert "alert_id" in alert
        assert "domain" in alert
        assert "severity" in alert
        assert "device" in alert
        assert "timestamp" in alert


def test_serialize_preserves_ground_truth() -> None:
    storm = _sample_storm()
    serialized = serialize_storm(storm)
    assert serialized["ground_truth"]["root_cause_device"] == "valkey-cart"


def test_script_runs_without_error(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)


def test_output_files_exist(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    assert (tmp_path / "train.json").exists()
    assert (tmp_path / "val.json").exists()
    assert (tmp_path / "test.json").exists()


def test_train_has_3_incidents(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    train = json.load(open(tmp_path / "train.json", encoding="utf-8"))
    assert len(train) == 3


def test_val_has_2_incidents(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    val = json.load(open(tmp_path / "val.json", encoding="utf-8"))
    assert len(val) == 2


def test_test_has_1_incident(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    test = json.load(open(tmp_path / "test.json", encoding="utf-8"))
    assert len(test) == 1


def test_all_incidents_have_ground_truth(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    for filename in ["train.json", "val.json", "test.json"]:
        dataset = json.load(open(tmp_path / filename, encoding="utf-8"))
        for incident in dataset:
            assert "ground_truth" in incident
            assert "root_cause_device" in incident["ground_truth"]
            assert "affected_services" in incident["ground_truth"]


def test_all_incidents_have_alerts(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    train = json.load(open(tmp_path / "train.json", encoding="utf-8"))
    for incident in train:
        assert "alerts" in incident
        assert len(incident["alerts"]) >= 3


def test_train_val_test_are_different(tmp_path: Path, monkeypatch) -> None:
    _ = monkeypatch
    generate_splits(3, 2, 1, tmp_path)
    train = json.load(open(tmp_path / "train.json", encoding="utf-8"))
    val = json.load(open(tmp_path / "val.json", encoding="utf-8"))
    assert train[0]["incident_id"] != val[0]["incident_id"]


def test_reproducible_with_same_seed() -> None:
    gen_a = ScenarioDrivenGenerator()
    gen_b = ScenarioDrivenGenerator()
    a = gen_a.generate_dataset(5, 0.3, random_seed=42)
    b = gen_b.generate_dataset(5, 0.3, random_seed=42)
    assert serialize_storm(a[0])["incident_id"] == serialize_storm(b[0])["incident_id"]
