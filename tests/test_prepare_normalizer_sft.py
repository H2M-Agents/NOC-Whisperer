"""Tests for normalizer SFT preparation script."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.prepare_normalizer_sft import prepare_normalizer_sft


def _write_small_train_file(path: Path) -> None:
    incidents = [
        {
            "incident_id": "inc-1",
            "alerts": [
                {
                    "source_system": "prometheus",
                    "domain": "service_mesh",
                    "severity": "critical",
                    "device": "cart",
                    "metric": "http_error_rate_per_min",
                    "value": 25.0,
                    "message": "cart error rate high",
                    "confidence": 0.95,
                },
                {
                    "source_system": "jaeger",
                    "domain": "application",
                    "severity": "major",
                    "device": "checkout",
                    "metric": "error.type",
                    "value": 1.0,
                    "message": "span error",
                    "confidence": 0.9,
                },
            ],
        },
        {
            "incident_id": "inc-2",
            "alerts": [
                {
                    "source_system": "node_exporter",
                    "domain": "infrastructure",
                    "severity": "minor",
                    "device": "host-a",
                    "metric": "cpu_utilization_percent",
                    "value": 72.0,
                    "message": "cpu elevated",
                    "confidence": 0.85,
                }
            ],
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(incidents), encoding="utf-8")


def test_import() -> None:
    from scripts.prepare_normalizer_sft import prepare_normalizer_sft as imported

    assert imported is not None


def test_prepare_creates_output_file(tmp_path: Path) -> None:
    train_path = tmp_path / "train.json"
    output_path = tmp_path / "normalizer_sft_train.jsonl"
    _write_small_train_file(train_path)

    prepare_normalizer_sft(train_path=train_path, output_path=output_path, num_examples=5, seed=42)
    assert output_path.exists()


def test_prepare_writes_max_five_examples_in_tests(tmp_path: Path) -> None:
    train_path = tmp_path / "train.json"
    output_path = tmp_path / "normalizer_sft_train.jsonl"
    _write_small_train_file(train_path)

    prepare_normalizer_sft(train_path=train_path, output_path=output_path, num_examples=5, seed=42)
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5


def test_output_jsonl_has_prompt_and_completion(tmp_path: Path) -> None:
    train_path = tmp_path / "train.json"
    output_path = tmp_path / "normalizer_sft_train.jsonl"
    _write_small_train_file(train_path)

    prepare_normalizer_sft(train_path=train_path, output_path=output_path, num_examples=5, seed=42)
    first = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    assert "prompt" in first
    assert "completion" in first


def test_prompt_and_completion_format(tmp_path: Path) -> None:
    train_path = tmp_path / "train.json"
    output_path = tmp_path / "normalizer_sft_train.jsonl"
    _write_small_train_file(train_path)

    examples = prepare_normalizer_sft(train_path=train_path, output_path=output_path, num_examples=5, seed=42)
    sample = examples[0]
    assert sample["prompt"].startswith("Raw metric event from ")
    assert "Classify domain and severity." in sample["prompt"]
    assert "domain:" in sample["completion"]
    assert "severity:" in sample["completion"]
    assert "reasoning:" in sample["completion"]
    assert "confidence:" in sample["completion"]
