"""Train the normalizer with GRPO (RLVR) starting from the SFT LoRA checkpoint."""

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
SFT_ADAPTER_DIR = "checkpoints/normalizer_sft_final/"
OUTPUT_DIR = str(PROJECT_ROOT / "models" / "normalizer_final_locked")
TRAIN_FILE = "data/normalizer_sft_train.jsonl"
REWARD_LOG = "logs/normalizer_rlvr_rewards.txt"


def normalizer_reward(predicted: dict, ground_truth: dict) -> float:
    """RLVR reward for domain and severity — matches CONTEXT.md exactly."""
    domain_correct = float(predicted["domain"] == ground_truth["domain"])
    severity_ranks = {"critical": 3, "major": 2, "minor": 1, "warning": 0}
    delta = abs(
        severity_ranks.get(predicted["severity"], 0) - severity_ranks.get(ground_truth["severity"], 0)
    )
    severity_score = {0: 1.0, 1: 0.5, 2: 0.0}.get(delta, 0.0)
    return 0.6 * domain_correct + 0.4 * severity_score


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
    """GRPO hyperparameters: G=8, 2 epochs, memory-safe batch settings."""
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
    """Load JSONL rows."""
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _parse_completion_labels(completion: str) -> Dict[str, str]:
    """Parse domain and severity from SFT completion text."""
    domain_m = re.search(r"(?im)^domain:\s*(\S+)", completion)
    severity_m = re.search(r"(?im)^severity:\s*(\S+)", completion)
    domain = domain_m.group(1).strip() if domain_m else "application"
    severity = severity_m.group(1).strip() if severity_m else "minor"
    return {"domain": domain, "severity": severity}


def _parse_prediction_from_text(text: str) -> Dict[str, str]:
    """Extract predicted domain/severity from model output."""
    return _parse_completion_labels(text)


def _build_prompt_lookup(rows: List[Dict[str, Any]]) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Return ordered prompts and prompt -> ground_truth labels."""
    prompts: List[str] = []
    lookup: Dict[str, Dict[str, str]] = {}
    for row in rows:
        prompt = str(row["prompt"])
        completion = str(row.get("completion", ""))
        gt = _parse_completion_labels(completion)
        prompts.append(prompt)
        lookup[prompt] = gt
    return prompts, lookup


def _mean_reward_for_prompts(
    model: Any,
    tokenizer: Any,
    prompts: List[str],
    prompt_to_gt: Dict[str, Dict[str, str]],
    max_samples: int,
) -> float:
    """Greedy-decoding accuracy proxy: mean normalizer_reward vs ground truth."""
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
                max_new_tokens=96,
                do_sample=False,
                pad_token_id=getattr(tokenizer, "pad_token_id", None),
            )
        new_tokens = generated[0][input_len:]
        completion_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        pred = _parse_prediction_from_text(completion_text)
        gt = prompt_to_gt[prompt]
        scores.append(normalizer_reward(pred, gt))
    return sum(scores) / float(len(scores)) if scores else 0.0


def _make_reward_fn(prompt_to_gt: Dict[str, Dict[str, str]]) -> Callable[..., List[float]]:
    """Build TRL reward closure keyed by exact prompt string."""

    def reward_func(prompts: Any, completions: Any, **kwargs: Any) -> List[float]:
        """TRL-compatible reward: list parallel to completions."""
        pre = prompts if isinstance(prompts, list) else list(prompts)
        comp = completions if isinstance(completions, list) else list(completions)
        rewards: List[float] = []
        for pr, raw_completion in zip(pre, comp):
            text = raw_completion if isinstance(raw_completion, str) else str(raw_completion)
            pred = _parse_prediction_from_text(text)
            gt = prompt_to_gt[str(pr)]
            rewards.append(normalizer_reward(pred, gt))
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
    """Run GRPO training; returns baseline accuracy, final accuracy, delta."""
    import torch
    from peft import PeftModel  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    from trl import GRPOTrainer  # type: ignore

    if not torch.cuda.is_available():
        print("CUDA not available — skipping RLVR training (use GPU for Session 14 Part 2).")
        print("Baseline accuracy: n/a")
        print("Final accuracy: n/a")
        print("Delta: n/a")
        return 0.0, 0.0, 0.0

    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    rows = _load_jsonl(TRAIN_FILE)
    prompts, prompt_to_gt = _build_prompt_lookup(rows)
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

    baseline_accuracy = _mean_reward_for_prompts(
        model, tokenizer, prompts, prompt_to_gt, max_samples=min(32, len(prompts))
    )

    reward_fn = _make_reward_fn(prompt_to_gt)
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[reward_fn],
        args=build_grpo_config(),
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(OUTPUT_DIR)

    final_accuracy = _mean_reward_for_prompts(
        model, tokenizer, prompts, prompt_to_gt, max_samples=min(32, len(prompts))
    )

    _log_epoch_rewards(trainer.state.log_history, REWARD_LOG)

    delta = final_accuracy - baseline_accuracy
    return baseline_accuracy, final_accuracy, delta


def main() -> None:
    """Entry point: RLVR normalizer training."""
    baseline_accuracy, final_accuracy, delta = train()
    if baseline_accuracy or final_accuracy:
        print(f"Baseline accuracy: {baseline_accuracy:.4f}")
        print(f"Final accuracy: {final_accuracy:.4f}")
        print(f"Delta: {delta:.4f}")


if __name__ == "__main__":
    main()
