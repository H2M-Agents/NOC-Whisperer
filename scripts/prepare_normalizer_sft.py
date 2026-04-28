"""Prepare SFT examples for the normalizer agent."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


def _alert_to_example(alert: Dict[str, Any]) -> Dict[str, str]:
    """Convert one alert dictionary into a prompt/completion SFT example."""
    source_system = str(alert.get("source_system", "unknown"))
    prompt_payload = {
        "metric": alert.get("metric"),
        "value": alert.get("value"),
        "device": alert.get("device"),
        "message": alert.get("message"),
    }
    prompt = (
        f"Raw metric event from {source_system}:\n"
        f"{json.dumps(prompt_payload, sort_keys=True)}\n"
        "Classify domain and severity."
    )

    domain = str(alert.get("domain", "application"))
    severity = str(alert.get("severity", "minor"))
    confidence = float(alert.get("confidence", 0.9))
    reasoning = (
        f"Signal from {source_system} on {alert.get('device', 'unknown-device')} "
        f"matches {domain} behavior with {severity} impact."
    )
    completion = (
        f"domain: {domain}\n"
        f"severity: {severity}\n"
        f"reasoning: {reasoning}\n"
        f"confidence: {confidence:.2f}"
    )
    return {"prompt": prompt, "completion": completion}


def _load_alerts(train_path: Path) -> List[Dict[str, Any]]:
    """Load and flatten alert dictionaries from a train incidents JSON file."""
    incidents = json.loads(train_path.read_text(encoding="utf-8"))
    alerts: List[Dict[str, Any]] = []
    for incident in incidents:
        for alert in incident.get("alerts", []):
            if isinstance(alert, dict):
                alerts.append(alert)
    return alerts


def _sample_alerts(alerts: List[Dict[str, Any]], num_examples: int, seed: int) -> List[Dict[str, Any]]:
    """Sample alerts with mild weighting toward ambiguous severities."""
    rng = random.Random(seed)
    if not alerts:
        return []

    weighted: List[Dict[str, Any]] = []
    for alert in alerts:
        sev = str(alert.get("severity", "minor"))
        weight = 3 if sev in {"minor", "warning"} else 1
        weighted.extend([alert] * weight)

    return [rng.choice(weighted) for _ in range(num_examples)]


def prepare_normalizer_sft(
    train_path: Path,
    output_path: Path,
    num_examples: int = 200,
    seed: int = 42,
) -> List[Dict[str, str]]:
    """Create SFT examples from train alerts and write JSONL output."""
    alerts = _load_alerts(train_path)
    sampled_alerts = _sample_alerts(alerts, num_examples=num_examples, seed=seed)
    examples = [_alert_to_example(alert) for alert in sampled_alerts]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for example in examples:
            file.write(json.dumps(example) + "\n")

    return examples


def main() -> None:
    """Generate 200 normalizer SFT examples from data/train.json."""
    train_path = Path("data/train.json")
    output_path = Path("data/normalizer_sft_train.jsonl")
    examples = prepare_normalizer_sft(train_path=train_path, output_path=output_path, num_examples=200, seed=42)
    print("Generated 200 SFT examples")

    preview_rng = random.Random(42)
    if examples:
        for idx, sample in enumerate(preview_rng.sample(examples, k=min(3, len(examples))), start=1):
            print(f"--- Example {idx} ---")
            print(sample["prompt"])
            print(sample["completion"])


if __name__ == "__main__":
    main()
