"""Import and structure validation for DSPy alerts-to-incident program."""

from __future__ import annotations

from pathlib import Path


def test_alerts_to_incident_signature_importable() -> None:
    """AlertsToIncident signature must import without side effects."""
    from dspy_programs.alerts_to_incident import AlertsToIncident

    assert AlertsToIncident is not None


def test_signature_has_two_input_fields() -> None:
    """Signature exposes exactly two input fields with expected names."""
    from dspy_programs.alerts_to_incident import AlertsToIncident

    inputs = []
    for name, field in AlertsToIncident.fields.items():
        extra = field.json_schema_extra or {}
        if extra.get("__dspy_field_type") == "input":
            inputs.append(name)
    assert set(inputs) == {"alert_cluster", "topology_context"}


def test_signature_has_five_output_fields() -> None:
    """Signature exposes five outputs matching CONTEXT.md."""
    from dspy_programs.alerts_to_incident import AlertsToIncident

    outputs = []
    for name, field in AlertsToIncident.fields.items():
        extra = field.json_schema_extra or {}
        if extra.get("__dspy_field_type") == "output":
            outputs.append(name)
    assert set(outputs) == {
        "root_cause_device",
        "incident_title",
        "affected_services",
        "confidence",
        "recommended_action",
    }


def test_correlators_importable() -> None:
    """Baseline and DSPy correlator classes import."""
    from dspy_programs.alerts_to_incident import BaselineCorrelator, DSPyCorrelator

    assert BaselineCorrelator is not None
    assert DSPyCorrelator is not None


def test_baseline_correlator_predict_returns_five_keys() -> None:
    """Baseline predict returns all five incident fields."""
    from dspy_programs.alerts_to_incident import BaselineCorrelator

    out = BaselineCorrelator().predict('[{"device":"cart"}]', {})
    assert set(out.keys()) == {
        "root_cause_device",
        "incident_title",
        "affected_services",
        "confidence",
        "recommended_action",
    }


def test_train_normalizer_rlvr_has_main_guard() -> None:
    """RLVR training script defines a standard main guard."""
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "train_normalizer_rlvr.py"
    content = script_path.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in content
