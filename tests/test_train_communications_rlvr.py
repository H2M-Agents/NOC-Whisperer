"""Import and config validation tests for communications RLVR training script."""

from __future__ import annotations

from pathlib import Path

from scripts import train_communications_rlvr


def _get_attr(config: object, key: str):
    """Read TrainingArguments-style config whether dataclass or shim dict."""
    if isinstance(config, dict):
        return config[key]
    return getattr(config, key)


def test_import() -> None:
    """Script imports without error."""
    from scripts.train_communications_rlvr import advisory_reward, build_grpo_config

    assert advisory_reward is not None
    assert build_grpo_config is not None


def test_advisory_reward_returns_float_in_unit_interval() -> None:
    """advisory_reward exists and returns float in [0, 1]."""
    sample = (
        "NOC ADVISORY — INCIDENT FAILURE IN cart valkey-cart checkout\n"
        "ACTION REQUIRED at 12:00\n"
        "Operations investigating degradation with suspected impact."
    )
    score = train_communications_rlvr.advisory_reward(sample)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_advisory_reward_empty_string_zero() -> None:
    """Blank advisory text scores zero."""
    assert train_communications_rlvr.advisory_reward("") == 0.0
    assert train_communications_rlvr.advisory_reward("   ") == 0.0


def test_grpo_num_generations_eight() -> None:
    """GRPO uses G=8 rollouts per CONTEXT.md."""
    cfg = train_communications_rlvr.build_grpo_config()
    assert _get_attr(cfg, "num_generations") == 8


def test_grpo_save_steps_fifty() -> None:
    """Periodic checkpointing every 50 steps."""
    cfg = train_communications_rlvr.build_grpo_config()
    assert _get_attr(cfg, "save_steps") == 50


def test_main_guard_present() -> None:
    """Script defines a standard main guard."""
    script_path = Path(train_communications_rlvr.__file__)
    content = script_path.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in content


def test_output_dir_communications_final_locked() -> None:
    """OUTPUT_DIR resolves to repo models/communications_final_locked."""
    root = Path(train_communications_rlvr.__file__).resolve().parents[1]
    expected = str(root / "models" / "communications_final_locked")
    assert train_communications_rlvr.OUTPUT_DIR == expected
