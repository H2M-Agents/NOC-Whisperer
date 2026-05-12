"""Communications agent — fine-tuned advisory generation with GPU load or Ollama fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from adapters.canonical_alert import Incident


class CommunicationsAgent:
    """Generate NOC advisories via local Qwen+LoRA when available, else Ollama."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path
        self._backend = self._resolve_backend(model_path)
        self._model = None
        self._tokenizer = None
        self._ollama_model = "qwen3:8b"
        self._loaded = False

    def _resolve_backend(self, model_path: Optional[str]) -> str:
        candidate = Path(model_path) if model_path else Path("models/communications_final_locked")
        if candidate.is_dir() and (candidate / "adapter_model.safetensors").exists():
            return str(candidate)
        return "ollama"

    def _load_model(self) -> None:
        if self._backend == "ollama":
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            base = AutoModelForCausalLM.from_pretrained(
                "Qwen/Qwen2.5-7B-Instruct",
                quantization_config=bnb_config,
                device_map="auto",
            )
            self._model = PeftModel.from_pretrained(base, self._backend)
            self._tokenizer = AutoTokenizer.from_pretrained(self._backend)
            self._model.eval()
        except Exception as e:
            print(f"CommunicationsAgent: model load failed ({e}) — falling back to Ollama")
            self._backend = "ollama"
            self._model = None
            self._tokenizer = None

    def generate(self, incident: Incident, advisory_type: str = "preliminary") -> str:
        if not self._loaded:
            self._load_model()
            self._loaded = True
        prompt = self._format_prompt(incident, advisory_type)
        if self._backend != "ollama" and self._model is not None:
            return self._infer_local(prompt)
        return self._infer_ollama(prompt)

    def _infer_local(self, prompt: str) -> str:
        try:
            import torch

            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            decoded = self._tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )
            out = decoded.strip()
            # Truncate at first END marker — model may repeat
            end_markers = [
                "[END] [NO CUSTOMER ACTION REQUIRED]",
                "[END]",
                "---\n**END OF MESSAGE**",
                "**END OF MESSAGE**",
            ]
            for marker in end_markers:
                if marker in out:
                    out = out[: out.index(marker) + len(marker)].strip()
                    break
            return out if out else "[inference: empty decode]"
        except Exception as e:
            return f"[inference error: {e}]"

    def _infer_ollama(self, prompt: str) -> str:
        try:
            import requests

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.3, "num_predict": 512},
                },
                timeout=60,
            )
            data = response.json()
            text = str(data.get("response") or "").strip()
            return text if text else "[ollama: empty response]"
        except Exception as e:
            return f"[ollama error: {e}]"

    def _format_prompt(self, incident: Incident, advisory_type: str) -> str:
        kind = (advisory_type or "preliminary").strip().lower()
        services = ", ".join(incident.affected_services)
        header = (
            f"Incident title: {incident.incident_title}\n"
            f"Suspected / root-cause device: {incident.root_cause_device}\n"
            f"Affected services: {services}\n"
            f"Confidence: {incident.confidence:.0%}\n"
        )
        if kind == "confirmed":
            return (
                f"{header}"
                "Task: Write a CONFIRMED NOC advisory. Use imperative ACTION REQUIRED lines. "
                "State impact and remediation as firm facts (confirmed), not speculation.\n"
            )
        return (
            f"{header}"
            "Task: Write a PRELIMINARY NOC advisory. Emphasize INVESTIGATING status and "
            "SUSPECTED root cause — avoid stating definitive confirmation.\n"
        )
