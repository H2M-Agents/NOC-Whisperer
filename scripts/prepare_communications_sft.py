"""Prepare SFT examples for the communications agent (NOC advisories)."""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_KNOWN_DEVICES = [
    "valkey-cart",
    "cart",
    "checkout",
    "frontend",
    "payment",
    "product-catalog",
    "recommendation",
]


def _pst_time_string() -> str:
    """Format current time in America/Los_Angeles for advisory headers."""
    return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M")


def _format_preliminary_advisory(incident: Dict[str, Any]) -> str:
    """Build preliminary NOC advisory text with rich impact and action lines."""
    time = incident["time"]
    root = incident["root_cause_device"]
    affected = incident["affected_services"]
    confidence = float(incident["confidence"])
    primary = incident["primary_affected_service"]
    return (
        f"NOC ADVISORY — {time} PST\n"
        f"STATUS: PRELIMINARY — INVESTIGATING\n"
        f"SUSPECTED: {root} failure\n"
        f"AFFECTED: {affected}\n"
        f"CONFIDENCE: {confidence:.0%} — under investigation\n"
        f"IMPACT: {root} service showing elevated error rates.\n"
        f"        Downstream {primary} service degraded.\n"
        f"        Investigation ongoing — root cause unconfirmed.\n"
        f"ACTIONS:\n"
        f"  NOC L1: Monitor {root} error rate and latency\n"
        f"  NOC L1: Watch {primary} for further degradation\n"
        f"  NOC L2: Check {root} pod health and recent logs\n"
        f"  NOC L2: Verify {primary} downstream dependencies\n"
        f"Next update: 5 minutes or on status change"
    )


def _format_confirmed_advisory(incident: Dict[str, Any]) -> str:
    """Build confirmed NOC advisory text with impact and multi-party actions."""
    time = incident["time"]
    title = incident["incident_title"]
    root = incident["root_cause_device"]
    affected = incident["affected_services"]
    severity = incident["severity"]
    duration = int(incident["duration_minutes"])
    confidence = float(incident["confidence"])
    action = incident["recommended_action"]
    primary = incident["primary_affected_service"]
    return (
        f"NOC ADVISORY — {time} PST\n"
        f"INCIDENT: {title}\n"
        f"ROOT CAUSE: {root} confirmed — service failure detected\n"
        f"AFFECTED: {affected}\n"
        f"SEVERITY: {severity} — {duration} minutes duration\n"
        f"CONFIDENCE: {confidence:.0%}\n"
        f"IMPACT CONFIRMED:\n"
        f"  {root}: failure confirmed, downstream cascade active\n"
        f"  {primary}: degraded due to {root} dependency\n"
        f"ACTION REQUIRED:\n"
        f"  NOC L2: {action}\n"
        f"  NOC L2: Verify {root} service restores successfully\n"
        f"  Platform: Monitor {primary} recovery metrics\n"
        f"  Platform: Confirm error rates return to baseline\n"
        f"  On-call: Page {root} team if not resolved in 10 min\n"
        f"RESOLUTION: Incident closes when all services nominal\n"
        f"Next update: On status change"
    )


def _synthetic_incident(
    rng: random.Random,
    *,
    advisory_kind: str,
) -> Dict[str, Any]:
    """Create one synthetic incident payload for advisory generation."""
    root = rng.choice(_KNOWN_DEVICES)
    others = [d for d in _KNOWN_DEVICES if d != root]
    if not others:
        affected_str = root
        primary = root
    else:
        n_extra = rng.randint(0, min(2, len(others)))
        extra = rng.sample(others, k=n_extra) if n_extra > 0 else []
        affected_list = [root] + extra
        affected_str = ", ".join(affected_list)
        primary = affected_list[0]
    if advisory_kind == "preliminary":
        confidence = round(rng.uniform(0.50, 0.84), 3)
    else:
        confidence = round(rng.uniform(0.85, 1.00), 3)
    duration = rng.randint(5, 120)
    severity = rng.choice(["critical", "major", "minor"])
    title = f"{root} cascade impacting {primary}"
    recommended = f"Validate {root} health and scale {primary} if needed"
    return {
        "time": _pst_time_string(),
        "root_cause_device": root,
        "incident_title": title,
        "affected_services": affected_str,
        "severity": severity,
        "duration_minutes": duration,
        "recommended_action": recommended,
        "primary_affected_service": primary,
        "confidence": confidence,
        "advisory_kind": advisory_kind,
    }


def _incident_to_prompt(incident: Dict[str, Any]) -> str:
    """Build model prompt describing the incident for advisory generation."""
    payload = {k: v for k, v in incident.items() if k != "time"}
    return "Generate a NOC advisory for this incident (JSON):\n" + json.dumps(payload, sort_keys=True)


def _incident_to_example(incident: Dict[str, Any]) -> Dict[str, str]:
    """Pair prompt with preliminary or confirmed advisory completion."""
    prompt = _incident_to_prompt(incident)
    if incident["advisory_kind"] == "preliminary":
        completion = _format_preliminary_advisory(incident)
    else:
        completion = _format_confirmed_advisory(incident)
    return {"prompt": prompt, "completion": completion}


def prepare_communications_sft(
    output_path: Path,
    num_examples: int = 120,
    seed: int = 42,
    holdout_path: Path | None = None,
) -> List[Dict[str, str]]:
    """Write communications SFT JSONL; at 120 examples, split 80 train / 40 holdout by advisory kind."""
    rng = random.Random(seed)
    if num_examples == 120:
        preliminary_rows = [
            _incident_to_example(_synthetic_incident(rng, advisory_kind="preliminary")) for _ in range(60)
        ]
        confirmed_rows = [
            _incident_to_example(_synthetic_incident(rng, advisory_kind="confirmed")) for _ in range(60)
        ]
        train_rows = preliminary_rows[:40] + confirmed_rows[:40]
        holdout_rows = preliminary_rows[40:60] + confirmed_rows[40:60]
        rng.shuffle(train_rows)
        rng.shuffle(holdout_rows)
        out_holdout = holdout_path if holdout_path is not None else output_path.parent / "communications_sft_holdout.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            for row in train_rows:
                file.write(json.dumps(row) + "\n")
        with out_holdout.open("w", encoding="utf-8") as file:
            for row in holdout_rows:
                file.write(json.dumps(row) + "\n")
        return train_rows + holdout_rows

    num_preliminary = (num_examples + 1) // 2
    num_confirmed = num_examples - num_preliminary
    rows: List[Dict[str, str]] = []
    for _ in range(num_preliminary):
        inc = _synthetic_incident(rng, advisory_kind="preliminary")
        rows.append(_incident_to_example(inc))
    for _ in range(num_confirmed):
        inc = _synthetic_incident(rng, advisory_kind="confirmed")
        rows.append(_incident_to_example(inc))
    rng.shuffle(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")
    return rows


def main() -> None:
    """Generate 120 communications SFT examples; 80 train + 40 holdout."""
    output_path = Path("data/communications_sft_train.jsonl")
    examples = prepare_communications_sft(output_path=output_path, num_examples=120, seed=42)
    print(f"Generated {len(examples)} communications SFT examples (80 train + 40 holdout) at {output_path}")


if __name__ == "__main__":
    main()
