"""Import/config validation tests for normalizer SFT training script."""

from __future__ import annotations

import inspect
from pathlib import Path

from scripts import train_normalizer_sft


def _get_attr(config: object, key: str):
    if isinstance(config, dict):
        return config[key]
    return getattr(config, key)


def test_import() -> None:
    from scripts.train_normalizer_sft import build_lora_config

    assert build_lora_config is not None


def test_lora_config_parameters_match_spec() -> None:
    cfg = train_normalizer_sft.build_lora_config()
    assert _get_attr(cfg, "r") == 16
    assert _get_attr(cfg, "lora_alpha") == 32
    assert _get_attr(cfg, "target_modules") == ["q_proj", "v_proj"]
    assert _get_attr(cfg, "lora_dropout") == 0.05
    assert _get_attr(cfg, "bias") == "none"
    assert _get_attr(cfg, "task_type") == "CAUSAL_LM"


def test_sft_config_parameters_match_spec() -> None:
    cfg = train_normalizer_sft.build_sft_config()
    assert _get_attr(cfg, "num_train_epochs") == 3
    # Effective batch size = per_device_train_batch_size *
    # gradient_accumulation_steps = 1 * 4 = 4
    # Reduced from batch=4 to batch=1 for RTX 4060 Ti 16GB VRAM
    assert _get_attr(cfg, "per_device_train_batch_size") == 1
    assert _get_attr(cfg, "gradient_accumulation_steps") == 4
    assert _get_attr(cfg, "fp16") is True
    assert _get_attr(cfg, "learning_rate") == 2e-4


def test_output_path_configured() -> None:
    assert train_normalizer_sft.OUTPUT_DIR == "checkpoints/normalizer_sft_final/"


def test_main_guard_present() -> None:
    script_path = Path(train_normalizer_sft.__file__)
    content = script_path.read_text(encoding="utf-8")
    assert "if __name__ == \"__main__\":" in content


def test_normalizer_reward_exists_and_accepts_dicts() -> None:
    fn = train_normalizer_sft.normalizer_reward
    assert callable(fn)
    sig = inspect.signature(fn)
    assert list(sig.parameters.keys()) == ["predicted", "ground_truth"]
    out = fn({"domain": "application", "severity": "major"}, {"domain": "application", "severity": "major"})
    assert isinstance(out, float)
