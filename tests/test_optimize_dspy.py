"""Config/import validation tests for DSPy optimization script (no network calls)."""

from __future__ import annotations

from pathlib import Path

from scripts import optimize_dspy


def test_import() -> None:
    """Script imports without error."""
    from scripts.optimize_dspy import load_val_set, root_cause_accuracy

    assert load_val_set is not None
    assert root_cause_accuracy is not None


def test_root_cause_accuracy_true_when_match() -> None:
    """Metric returns True on matching root-cause device."""
    example = {"ground_truth": {"root_cause_device": "valkey-cart"}}
    prediction = {"root_cause_device": "valkey-cart"}
    assert optimize_dspy.root_cause_accuracy(example, prediction) is True


def test_root_cause_accuracy_false_when_mismatch() -> None:
    """Metric returns False on non-matching root-cause device."""
    example = {"ground_truth": {"root_cause_device": "valkey-cart"}}
    prediction = {"root_cause_device": "kafka"}
    assert optimize_dspy.root_cause_accuracy(example, prediction) is False


def test_dataset_loading_works_with_val_json() -> None:
    """Validation set loads and contains expected keys."""
    val_set = optimize_dspy.load_val_set()
    assert isinstance(val_set, list)
    assert len(val_set) > 0
    assert "ground_truth" in val_set[0]
    assert "alerts" in val_set[0]


def test_main_guard_present() -> None:
    """Script includes a standard main guard."""
    content = Path(optimize_dspy.__file__).read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in content


def test_configure_lm_uses_dspy_lm_no_network(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """LM config wires dspy.LM with env-backed values and never performs API calls in test."""
    captured: dict[str, object] = {}

    class FakeSettings:
        @staticmethod
        def configure(**kwargs: object) -> None:
            captured["settings"] = kwargs

    class FakeDspy:
        settings = FakeSettings()

        @staticmethod
        def LM(model: str, api_base: str, api_key: str, temperature: float) -> dict[str, object]:
            captured["model"] = model
            captured["api_base"] = api_base
            captured["api_key"] = api_key
            captured["temperature"] = temperature
            return {"ok": True}

    monkeypatch.setattr(optimize_dspy, "dspy", FakeDspy)
    monkeypatch.setenv("OPENAI_API_BASE", "http://SV_CLUSTER_IP:PORT/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder-key")
    monkeypatch.setenv("DSPy_MODEL", "openai/gpt-oss-20b")

    cfg = optimize_dspy.load_llm_config()
    lm = optimize_dspy.configure_dspy_lm(cfg)
    assert lm == {"ok": True}
    assert captured["model"] == "openai/openai/gpt-oss-20b"
    assert captured["api_base"] == "http://SV_CLUSTER_IP:PORT/v1"
    assert captured["api_key"] == "placeholder-key"
    assert captured["temperature"] == 0.0
