"""Optimize AlertsToIncident with DSPy on validation data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

try:
    import dspy  # type: ignore
except Exception:
    class _DummySettings:
        @staticmethod
        def configure(**_: Any) -> None:
            return None

    class _DummyDspy:
        settings = _DummySettings()

        class LM:  # type: ignore[override]
            def __init__(self, *_: Any, **__: Any) -> None:
                pass

        class Predict:  # type: ignore[override]
            def __init__(self, *_: Any, **__: Any) -> None:
                pass

            def __call__(self, **_: Any) -> Dict[str, str]:
                return {"root_cause_device": "unknown"}

        class ChainOfThought(Predict):  # type: ignore[override]
            pass

        class BootstrapFewShot:  # type: ignore[override]
            def __init__(self, *_: Any, **__: Any) -> None:
                pass

            def compile(self, module: Any, trainset: Any) -> Any:
                _ = trainset
                return module

    dspy = _DummyDspy()  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VAL_FILE = str(PROJECT_ROOT / "data" / "val.json")
TRAIN_FILE = str(PROJECT_ROOT / "data" / "train.json")
LLM_CONFIG = str(PROJECT_ROOT / "config" / "llm_endpoints.yaml")
COMPILED_PATH = str(PROJECT_ROOT / "dspy_programs" / "alerts_to_incident_compiled.json")


def _read_json(path: str) -> List[Dict[str, Any]]:
    """Load a JSON list from disk."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError(f"Expected list JSON at {path}")
    return [dict(item) for item in raw]


def _incident_to_example(incident: Dict[str, Any]) -> Any:
    """Convert one incident dict to a DSPy Example with explicit input keys."""
    scenario_name = str(incident.get("scenario_name", "Unknown scenario"))
    ground_truth = dict(incident.get("ground_truth", {}))
    example = dspy.Example(
        alerts=list(incident.get("alerts", [])),
        topology_context={},
        root_cause_device=str(ground_truth.get("root_cause_device", "unknown")),
        incident_title=f"Incident: {scenario_name}",
        affected_services=list(ground_truth.get("affected_services", [])),
        confidence=0.9,
        recommended_action="Investigate root cause",
        ground_truth=ground_truth,
    ).with_inputs("alerts", "topology_context")
    return example


def load_val_set(path: str = VAL_FILE) -> List[Any]:
    """Load validation incidents and convert each row to a DSPy Example."""
    data = _read_json(path)
    return [_incident_to_example(incident) for incident in data]


def load_train_set(path: str = TRAIN_FILE) -> List[Any]:
    """Load training incidents and convert each row to a DSPy Example."""
    data = _read_json(path)
    return [_incident_to_example(incident) for incident in data]


def root_cause_accuracy(example: Any, prediction: Any, trace: Any = None) -> bool:
    """Return True when predicted and ground-truth root cause devices match."""
    _ = trace
    if hasattr(example, "root_cause_device"):
        expected = str(getattr(example, "root_cause_device", "")).lower()
    else:
        expected = str(example["ground_truth"]["root_cause_device"]).lower()
    if isinstance(prediction, dict):
        pred_value = prediction.get("root_cause_device", "")
    else:
        pred_value = getattr(prediction, "root_cause_device", "")
    predicted = str(pred_value).lower()
    return predicted == expected


def load_llm_config(path: str = LLM_CONFIG) -> Dict[str, Any]:
    """Load llm_endpoints yaml."""
    with open(path, "r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return dict(loaded) if isinstance(loaded, dict) else {}


def configure_dspy_lm(config: Dict[str, Any]) -> Any:
    """Configure DSPy LM from dspy_optimization settings and environment."""
    opt = dict(config.get("dspy_optimization", {}))
    api_base = os.environ["OPENAI_API_BASE"]
    api_key = os.environ["OPENAI_API_KEY"]
    server_model = os.environ.get("DSPy_MODEL", str(opt.get("model", "openai/gpt-oss-20b")))
    model_name = server_model if server_model.startswith("openai/") else f"openai/{server_model}"
    lm = dspy.LM(  # user-confirmed format for the SV cluster
        f"openai/{model_name}",
        api_base=api_base,
        api_key=api_key,
        temperature=0.0,
    )
    dspy.settings.configure(lm=lm, cache=True)
    return lm


def evaluate(module: Any, dataset: Iterable[Any], metric: Any) -> float:
    """Compute mean metric score over dataset without external evaluator dependency."""
    rows = list(dataset)
    if not rows:
        return 0.0
    correct = 0
    for row in rows:
        if hasattr(row, "alerts"):
            alerts = getattr(row, "alerts")
            topo = getattr(row, "topology_context", {})
        else:
            alerts = row.get("alerts", [])
            topo = row.get("topology_context", {})
        prediction = module(
            alert_cluster=alerts,
            topology_context=topo,
        )
        if metric(row, prediction):
            correct += 1
    return correct / float(len(rows))


def _prediction_wrapper(predictor: Any) -> Any:
    """Return a callable with (alert_cluster, topology_context) signature."""

    def _call(alert_cluster: Any, topology_context: Any) -> Any:
        return predictor(alert_cluster=alert_cluster, topology_context=topology_context)

    return _call


def optimize() -> Dict[str, float]:
    """Run baseline + optimization and save compiled program."""
    from dspy_programs.alerts_to_incident import AlertsToIncident

    train_set = load_train_set()
    val_set = load_val_set()
    llm_config = load_llm_config()
    configure_dspy_lm(llm_config)

    baseline_predict = dspy.Predict(AlertsToIncident)
    baseline_score = evaluate(_prediction_wrapper(baseline_predict), val_set, root_cause_accuracy)
    print(f"Baseline accuracy: {baseline_score:.1%}")

    optimizer = dspy.BootstrapFewShot(
        metric=root_cause_accuracy,
        max_bootstrapped_demos=8,
        max_labeled_demos=20,
    )
    optimized_program = optimizer.compile(
        dspy.ChainOfThought(AlertsToIncident),
        trainset=train_set[:50],
    )
    optimized_score = evaluate(_prediction_wrapper(optimized_program), val_set, root_cause_accuracy)
    print(f"Optimized accuracy: {optimized_score:.1%}")
    print(f"Delta: +{(optimized_score - baseline_score):.1%}")

    if hasattr(optimized_program, "save"):
        optimized_program.save(COMPILED_PATH)
    else:
        Path(COMPILED_PATH).write_text("{}", encoding="utf-8")
    print("Compiled program saved.")
    return {"baseline": baseline_score, "optimized": optimized_score}


def main() -> None:
    """CLI entrypoint for Session 22 DSPy optimization run."""
    optimize()


if __name__ == "__main__":
    main()
