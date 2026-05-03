"""Import/config validation tests for communications SFT training script."""

from __future__ import annotations

from pathlib import Path

from scripts import train_communications_sft


def _get_attr(config: object, key: str) -> object:
    if isinstance(config, dict):
        return config[key]
    return getattr(config, key)


def test_import() -> None:
    """Communications training helpers import."""
    from scripts.train_communications_sft import build_lora_config

    assert build_lora_config is not None


def test_lora_config_parameters_match_spec() -> None:
    """LoRA matches normalizer / project spec."""
    cfg = train_communications_sft.build_lora_config()
    assert _get_attr(cfg, "r") == 16
    assert _get_attr(cfg, "lora_alpha") == 32
    assert _get_attr(cfg, "target_modules") == ["q_proj", "v_proj"]
    assert _get_attr(cfg, "lora_dropout") == 0.05
    assert _get_attr(cfg, "bias") == "none"
    assert _get_attr(cfg, "task_type") == "CAUSAL_LM"


def test_sft_config_parameters_match_spec() -> None:
    """SFT config mirrors normalizer SFT (4-bit path — no fp16 in config)."""
    cfg = train_communications_sft.build_sft_config()
    assert _get_attr(cfg, "num_train_epochs") == 3
    assert _get_attr(cfg, "per_device_train_batch_size") == 1
    assert _get_attr(cfg, "gradient_accumulation_steps") == 4
    assert _get_attr(cfg, "learning_rate") == 2e-4


def test_output_path_configured() -> None:
    """Checkpoint directory for communications SFT."""
    assert train_communications_sft.OUTPUT_DIR == "checkpoints/communications_sft_final/"


def test_train_file_path_configured() -> None:
    """Training data path points at communications JSONL."""
    assert train_communications_sft.TRAIN_FILE == "data/communications_sft_train.jsonl"


def test_main_guard_present() -> None:
    """Script is runnable as a module."""
    script_path = Path(train_communications_sft.__file__)
    content = script_path.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in content


def test_cuda_alloc_env_set_in_script() -> None:
    """GPU allocator env matches .cursorrules training scripts."""
    script_path = Path(train_communications_sft.__file__)
    content = script_path.read_text(encoding="utf-8")
    assert 'os.environ["PYTORCH_CUDA_ALLOC_CONF"]' in content
    assert "expandable_segments:True" in content
