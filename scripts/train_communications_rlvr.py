"""Train the communications agent with GRPO (RLVR) from the SFT LoRA checkpoint."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple

try:
    import torch
except Exception:
    class _TorchShim:
        """Fallback shim for local test environments without torch."""

        float16 = "float16"

        class cuda:
            """Minimal CUDA stub."""

            @staticmethod
            def is_available() -> bool:
                return False

    torch = _TorchShim()  # type: ignore[assignment]

try:
    from transformers import BitsAndBytesConfig
except Exception:
    class BitsAndBytesConfig:  # type: ignore[override]
        """Fallback shim for local test environments without transformers."""

        def __init__(self, **_: Any) -> None:
            pass

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

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
SFT_ADAPTER_DIR = "checkpoints/communications_sft_final/"
OUTPUT_DIR = str(PROJECT_ROOT / "models" / "communications_final_locked")
TRAIN_FILE = "data/communications_sft_train.jsonl"
REWARD_LOG = "logs/communications_rlvr_rewards.txt"

KNOWN_SERVICES = [
    "valkey-cart",
    "cart",
    "checkout",
    "payment",
    "product-catalog",
    "recommendation",
    "shipping",
    "currency",
    "email",
    "ad",
    "frontend",
    "frontend-proxy",
    "kafka",
    "accounting",
    "fraud-detection",
    "image-provider",
    "quote",
    "flagd",
]


def advisory_reward(generated: str) -> float:
    """RLVR advisory quality score — matches CONTEXT.md (Communications Reward)."""
    if not (generated or "").strip():
        return 0.0
    from textstat import flesch_kincaid_grade

    scores = []
    scores.append(
        float(any(w in generated.upper() for w in ["INCIDENT", "FAILURE", "OUTAGE", "DEGRADATION"]))
    )
    named = sum(1 for s in KNOWN_SERVICES if s.lower() in generated.lower())
    scores.append(min(1.0, named / 2))
    scores.append(float(bool(re.search(r"\d{1,2}:\d{2}", generated))))
    scores.append(float("ACTION" in generated.upper()))
    scores.append(float("NOC" in generated.upper()))
    fk = flesch_kincaid_grade(generated)
    scores.append(1.0 if 7 <= fk <= 10 else 0.5)
    return sum(scores) / len(scores)


def build_lora_config() -> Any:
    """Build LoRA configuration — must match SFT training."""
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
        return {
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "v_proj"],
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": "CAUSAL_LM",
        }


def build_grpo_config() -> Any:
    """GRPO hyperparameters: G=8, 2 epochs, full communications JSONL, periodic checkpoints."""
    # RTX 4090 25GB VRAM
    # Full dataset: 80 examples × 2 epochs = 160 steps
    # Estimated: 160 × 18s = ~48 minutes on RTX 4090
    try:
        from trl import GRPOConfig  # type: ignore

        return GRPOConfig(
            output_dir=OUTPUT_DIR,
            num_train_epochs=2,
            num_generations=8,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=5e-6,
            logging_steps=1,
            save_steps=50,
            report_to="none",
        )
    except Exception:
        return {
            "output_dir": OUTPUT_DIR,
            "num_train_epochs": 2,
            "num_generations": 8,
            "per_device_train_batch_size": 1,
            "gradient_accumulation_steps": 8,
            "learning_rate": 5e-6,
            "logging_steps": 1,
            "save_steps": 50,
        }


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load JSONL rows (full file — no row cap)."""
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _ordered_prompts(rows: List[Dict[str, Any]]) -> List[str]:
    """Prompts in file order for GRPO dataset."""
    return [str(row["prompt"]) for row in rows]


def _mean_compliance_for_prompts(
    model: Any,
    tokenizer: Any,
    prompts: List[str],
    max_samples: int,
) -> float:
    """Greedy-decoding proxy: mean advisory_reward on generated completions."""
    import torch

    model.eval()
    scores: List[float] = []
    device = next(model.parameters()).device
    for prompt in prompts[:max_samples]:
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        input_len = inputs["input_ids"].shape[1]
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=getattr(tokenizer, "pad_token_id", None),
            )
        new_tokens = generated[0][input_len:]
        completion_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        scores.append(advisory_reward(completion_text))
    return sum(scores) / float(len(scores)) if scores else 0.0


def _make_reward_fn() -> Callable[..., List[float]]:
    """Build TRL reward closure using advisory_reward only."""

    def reward_func(prompts: Any, completions: Any, **kwargs: Any) -> List[float]:
        """TRL-compatible reward: list parallel to completions."""
        comp = completions if isinstance(completions, list) else list(completions)
        rewards: List[float] = []
        for raw_completion in comp:
            text = raw_completion if isinstance(raw_completion, str) else str(raw_completion)
            rewards.append(advisory_reward(text))
        return rewards

    return reward_func


def _log_epoch_rewards(log_history: Iterable[Dict[str, Any]], path: str) -> None:
    """Write reward-related entries and epoch markers to disk."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        for item in log_history:
            if "reward" in item:
                ep = item.get("epoch", "?")
                rw = item["reward"]
                file.write(f"epoch={ep}, reward={rw}\n")
            elif "train_reward" in item:
                ep = item.get("epoch", "?")
                file.write(f"epoch={ep}, reward={item['train_reward']}\n")


def train() -> Tuple[float, float, float]:
    """Run GRPO training; returns baseline compliance, final compliance, delta."""
    import torch
    from peft import PeftModel  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    from trl import GRPOTrainer  # type: ignore

    if not torch.cuda.is_available():
        print("CUDA not available — skipping RLVR training (use GPU for Session 18 Part 2).")
        print("Baseline compliance: n/a")
        print("Final compliance: n/a")
        print("Delta: n/a")
        return 0.0, 0.0, 0.0

    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    rows = _load_jsonl(TRAIN_FILE)
    prompts = _ordered_prompts(rows)
    train_dataset = Dataset.from_list([{"prompt": p} for p in prompts])

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = PeftModel.from_pretrained(base, SFT_ADAPTER_DIR)

    baseline = _mean_compliance_for_prompts(
        model, tokenizer, prompts, max_samples=min(32, len(prompts))
    )

    reward_fn = _make_reward_fn()
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[reward_fn],
        args=build_grpo_config(),
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(OUTPUT_DIR)

    final = _mean_compliance_for_prompts(
        model, tokenizer, prompts, max_samples=min(32, len(prompts))
    )

    _log_epoch_rewards(trainer.state.log_history, REWARD_LOG)

    delta = final - baseline
    return baseline, final, delta


def main() -> None:
    """Entry point: RLVR communications training."""
    baseline, final, delta = train()
    if baseline or final:
        print(f"Baseline compliance: {baseline:.4f}")
        print(f"Final compliance: {final:.4f}")
        print(f"Delta: {delta:.4f}")


if __name__ == "__main__":
    main()
