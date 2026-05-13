"""Normalizer agent — fine-tuned domain/severity classification with rule-based fallback."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from adapters.canonical_alert import CanonicalAlert

_VALID_DOMAINS: frozenset[str] = frozenset({"infrastructure", "service_mesh", "application"})
_VALID_SEVERITIES: frozenset[str] = frozenset({"critical", "major", "minor", "warning"})


class NormalizerAgent:
    """Classify raw metric events via local Qwen+LoRA when available, else deterministic rules."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        """Initialize with optional adapter path; model loads lazily on first ``process()``."""
        self.model_path = model_path
        self._backend = self._resolve_backend(model_path)
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._last_infer_confidence: Optional[float] = None

    def _resolve_backend(self, model_path: Optional[str]) -> str:
        """Return adapter directory path when locked weights exist, else rule-based inference."""
        candidate = Path(model_path) if model_path else Path("models/normalizer_final_locked")
        if candidate.is_dir() and (candidate / "adapter_model.safetensors").exists():
            return str(candidate)
        return "rules"

    def _load_model(self) -> None:
        """Load Qwen2.5-7B + LoRA in 4-bit; on failure keep rule-based path."""
        if self._backend == "rules":
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
            print(f"NormalizerAgent: model load failed ({e}) — using rule-based classification")
            self._backend = "rules"
            self._model = None
            self._tokenizer = None

    def _rule_based_domain_severity(self, source_system: str, value: float) -> Tuple[str, str]:
        """Deterministic domain and severity from source system and metric value."""
        if source_system == "node_exporter":
            domain = "infrastructure"
        elif source_system == "prometheus":
            domain = "service_mesh"
        else:
            domain = "application"
        severity = "major" if value >= 1 else "minor"
        return domain, severity

    def _normalize_domain_token(self, raw: str) -> Optional[str]:
        """Map model output to a valid CanonicalAlert domain."""
        token = raw.strip().lower().replace(" ", "_").replace("-", "_")
        if token in _VALID_DOMAINS:
            return token
        if token == "service_mesh" or "service" in token and "mesh" in token:
            return "service_mesh"
        return None

    def _normalize_severity_token(self, raw: str) -> Optional[str]:
        """Map model output to a valid CanonicalAlert severity."""
        token = raw.strip().lower()
        if token in _VALID_SEVERITIES:
            return token
        return None

    def _parse_model_completion(self, text: str) -> Optional[Tuple[str, str, Optional[float]]]:
        """Parse training-style completion for domain, severity, and optional confidence."""
        domain: Optional[str] = None
        severity: Optional[str] = None
        confidence: Optional[float] = None
        for line in text.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("domain:"):
                domain = self._normalize_domain_token(stripped.split(":", 1)[1])
            elif lower.startswith("severity:"):
                severity = self._normalize_severity_token(stripped.split(":", 1)[1])
            elif lower.startswith("confidence:"):
                rest = stripped.split(":", 1)[1].strip()
                match = re.search(r"[-+]?\d*\.?\d+", rest)
                if match:
                    try:
                        confidence = float(match.group())
                    except ValueError:
                        confidence = None
        if domain is None or severity is None:
            return None
        if confidence is not None and not (0.0 <= confidence <= 1.0):
            confidence = None
        return domain, severity, confidence

    def _infer(self, raw_payload: Dict[str, Any], source_system: str) -> Optional[Tuple[str, str]]:
        """Run local LM classification; return ``(domain, severity)`` or ``None`` to use rule-based path."""
        try:
            import torch

            prompt = (
                f"Raw metric event from {source_system}:\n"
                f"{json.dumps(raw_payload)}\n"
                "Classify domain and severity."
            )
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=100,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            decoded = self._tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )
            parsed = self._parse_model_completion(decoded)
            if parsed is None:
                return None
            domain, severity, conf = parsed
            self._last_infer_confidence = conf
            return domain, severity
        except Exception:
            return None

    def process(self, raw_payload: Dict[str, Any], source_system: str) -> CanonicalAlert:
        """Convert raw payload to ``CanonicalAlert`` using the fine-tuned model when loaded, else rules."""
        if not self._loaded:
            self._load_model()
            self._loaded = True

        metric = str(raw_payload.get("metric", "unknown_metric"))
        value = float(raw_payload.get("value", 0.0))
        device = str(raw_payload.get("device", "unknown-device"))
        message = str(raw_payload.get("message", f"Normalized event from {source_system}"))

        domain: str
        severity: str
        confidence = 0.90

        if self._backend != "rules" and self._model is not None:
            self._last_infer_confidence = None
            pair = self._infer(raw_payload, source_system)
            if pair is not None:
                domain, severity = pair
                confidence = (
                    self._last_infer_confidence
                    if self._last_infer_confidence is not None
                    else 0.90
                )
            else:
                domain, severity = self._rule_based_domain_severity(source_system, value)
        else:
            domain, severity = self._rule_based_domain_severity(source_system, value)

        return CanonicalAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            domain=domain,
            severity=severity,
            device=device,
            metric=metric,
            message=message,
            source_system=source_system,
            value=value,
            threshold=float(raw_payload.get("threshold", 0.0)),
            confidence=confidence,
            raw_payload=raw_payload,
        )
