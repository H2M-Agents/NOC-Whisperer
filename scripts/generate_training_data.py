"""Generate fixed train/val/test synthetic datasets."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generator.fault_scenarios import ALL_SCENARIOS
from generator.synthetic_generator import ScenarioDrivenGenerator


def serialize_storm(storm: dict) -> dict:
    """Serialize a generated storm into JSON-safe structures."""
    return {
        "incident_id": storm["incident_id"],
        "scenario_name": storm["scenario_name"],
        "ground_truth": storm["ground_truth"],
        "alerts": [a.to_dict() for a in storm["alerts"]],
    }


def main(output_dir: str = "data") -> None:
    """Generate train/val/test datasets and write JSON files."""
    os.makedirs(output_dir, exist_ok=True)

    generator = ScenarioDrivenGenerator()

    train = generator.generate_dataset(
        num_incidents=100,
        noise_ratio=0.3,
        scenarios=ALL_SCENARIOS,
        random_seed=42,
    )

    val = generator.generate_dataset(
        num_incidents=30,
        noise_ratio=0.3,
        scenarios=ALL_SCENARIOS,
        random_seed=43,
    )

    test = generator.generate_dataset(
        num_incidents=20,
        noise_ratio=0.4,
        scenarios=ALL_SCENARIOS,
        random_seed=44,
    )

    with open(os.path.join(output_dir, "train.json"), "w", encoding="utf-8") as f:
        json.dump([serialize_storm(s) for s in train], f, indent=2, default=str)
    with open(os.path.join(output_dir, "val.json"), "w", encoding="utf-8") as f:
        json.dump([serialize_storm(s) for s in val], f, indent=2, default=str)
    with open(os.path.join(output_dir, "test.json"), "w", encoding="utf-8") as f:
        json.dump([serialize_storm(s) for s in test], f, indent=2, default=str)

    for split_name, dataset in [("train", train), ("val", val), ("test", test)]:
        for storm in dataset:
            assert "root_cause_device" in storm["ground_truth"], (
                f"{split_name}: missing root_cause_device in ground_truth"
            )
            assert "affected_services" in storm["ground_truth"], (
                f"{split_name}: missing affected_services in ground_truth"
            )

    total_train_alerts = sum(len(s["alerts"]) for s in train)
    total_val_alerts = sum(len(s["alerts"]) for s in val)
    total_test_alerts = sum(len(s["alerts"]) for s in test)
    print(f"Train: {len(train)} incidents, {total_train_alerts} total alerts")
    print(f"Val:   {len(val)} incidents, {total_val_alerts} total alerts")
    print(f"Test:  {len(test)} incidents, {total_test_alerts} total alerts")
    print("All ground truth verified.")
    print("Dataset generation complete.")


if __name__ == "__main__":
    main()
