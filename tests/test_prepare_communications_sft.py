"""Tests for communications SFT preparation script."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.prepare_communications_sft import prepare_communications_sft


def test_import() -> None:
    """prepare_communications_sft must import."""
    from scripts.prepare_communications_sft import prepare_communications_sft as imported

    assert imported is not None


def test_prepare_creates_output_file(tmp_path: Path) -> None:
    """prepare_communications_sft writes JSONL output."""
    output_path = tmp_path / "communications_sft_train.jsonl"
    prepare_communications_sft(output_path=output_path, num_examples=5, seed=1)
    assert output_path.exists()


def test_prepare_writes_max_five_examples_in_tests(tmp_path: Path) -> None:
    """Tests stay light — at most five JSONL rows."""
    output_path = tmp_path / "communications_sft_train.jsonl"
    prepare_communications_sft(output_path=output_path, num_examples=5, seed=2)
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5


def test_output_jsonl_has_prompt_and_completion(tmp_path: Path) -> None:
    """Each row is prompt/completion pair."""
    output_path = tmp_path / "communications_sft_train.jsonl"
    prepare_communications_sft(output_path=output_path, num_examples=5, seed=3)
    first = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    assert "prompt" in first
    assert "completion" in first


def test_preliminary_and_confirmed_templates_present(tmp_path: Path) -> None:
    """Completions use preliminary vs confirmed advisory templates."""
    output_path = tmp_path / "communications_sft_train.jsonl"
    prepare_communications_sft(output_path=output_path, num_examples=5, seed=4)
    completions = [json.loads(line)["completion"] for line in output_path.read_text(encoding="utf-8").splitlines()]
    has_prelim = any("STATUS: PRELIMINARY — INVESTIGATING" in c for c in completions)
    has_confirmed = any("ROOT CAUSE:" in c and "confirmed" in c for c in completions)
    assert has_prelim
    assert has_confirmed


def test_prompt_contains_incident_json(tmp_path: Path) -> None:
    """Prompt asks for advisory from JSON incident payload."""
    output_path = tmp_path / "communications_sft_train.jsonl"
    rows = prepare_communications_sft(output_path=output_path, num_examples=5, seed=5)
    assert rows[0]["prompt"].startswith("Generate a NOC advisory for this incident (JSON):\n")
    payload = rows[0]["prompt"].split("\n", 1)[1]
    data = json.loads(payload)
    assert "root_cause_device" in data
    assert "confidence" in data
