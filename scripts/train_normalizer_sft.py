"""Train the normalizer SFT model with LoRA."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from datasets import Dataset
except Exception:
    class Dataset:  # type: ignore[override]
        """Fallback shim for local test environments without datasets."""

        @staticmethod
        def from_list(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return raw_data

hf_token = os.environ.get("HF_TOKEN", None)
if hf_token:
    from huggingface_hub import login

    login(token=hf_token)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
OUTPUT_DIR = "checkpoints/normalizer_sft_final/"
TRAIN_FILE = "data/normalizer_sft_train.jsonl"
LOSS_LOG = "logs/normalizer_sft_loss.txt"


def build_lora_config() -> Any:
    """Build LoRA configuration for normalizer SFT."""
    try:
        from peft import LoraConfig  # type: ignore

        return LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
    except Exception:
        # Fallback for import/config validation without heavy dependencies.
        return {
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "v_proj"],
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": "CAUSAL_LM",
        }


def build_sft_config() -> Any:
    """Build SFT trainer config."""
    try:
        from trl import SFTConfig  # type: ignore

        return SFTConfig(
            output_dir=OUTPUT_DIR,
            num_train_epochs=3,
            per_device_train_batch_size=4,
            learning_rate=2e-4,
            logging_steps=1,
        )
    except Exception:
        return {
            "output_dir": OUTPUT_DIR,
            "num_train_epochs": 3,
            "per_device_train_batch_size": 4,
            "learning_rate": 2e-4,
        }


def normalizer_reward(predicted: Dict[str, str], ground_truth: Dict[str, str]) -> float:
    """Simple reward placeholder used for interface consistency in tests."""
    domain_ok = float(predicted.get("domain") == ground_truth.get("domain"))
    severity_ok = float(predicted.get("severity") == ground_truth.get("severity"))
    return (domain_ok + severity_ok) / 2.0


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load training rows from JSONL file."""
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _extract_loss_entries(log_history: Iterable[Dict[str, Any]]) -> List[Tuple[int, float]]:
    """Extract (step, loss) pairs from trainer log history."""
    losses: List[Tuple[int, float]] = []
    for item in log_history:
        if "loss" in item:
            losses.append((int(item.get("step", 0)), float(item["loss"])))
    return losses


def train() -> float:
    """Run SFT training and return final loss."""
    from peft import get_peft_model  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    from trl import SFTTrainer  # type: ignore

    os.makedirs("logs", exist_ok=True)
    os.makedirs("checkpoints", exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL)
    model = get_peft_model(model, build_lora_config())
    raw_data = _load_jsonl(TRAIN_FILE)
    formatted_data = [
        {"text": f"{record['prompt']}\n{record['completion']}"}
        for record in raw_data
    ]
    train_dataset = Dataset.from_list(formatted_data)

    trainer = SFTTrainer(
        model=model,
        args=build_sft_config(),
        train_dataset=train_dataset,
        dataset_text_field="text",
        processing_class=tokenizer,
    )
    result = trainer.train()
    trainer.save_model(OUTPUT_DIR)

    loss_entries = _extract_loss_entries(trainer.state.log_history)
    with open(LOSS_LOG, "w", encoding="utf-8") as file:
        if loss_entries:
            for step, loss in loss_entries:
                file.write(f"step={step}, loss={loss}\n")
            final_loss = loss_entries[-1][1]
        else:
            final_loss = float(result.training_loss)
            file.write(f"final_loss={final_loss}\n")
    return final_loss


def main() -> None:
    """Execute SFT training."""
    final_loss = train()
    print(f"SFT training complete. Loss: {final_loss}")


if __name__ == "__main__":
    main()
