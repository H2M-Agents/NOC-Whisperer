"""Tests for Session 24 consolidated evaluation runner."""

from __future__ import annotations

from pathlib import Path

from scripts import run_evaluation


def test_import() -> None:
    """Script imports without side effects."""
    from scripts.run_evaluation import build_summary, load_test_set

    assert build_summary is not None
    assert load_test_set is not None


def test_load_test_set_reads_data_test_json() -> None:
    """Held-out dataset loader returns list with expected keys."""
    rows = run_evaluation.load_test_set()
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "ground_truth" in rows[0]
    assert "alerts" in rows[0]


def test_score_advisory_range() -> None:
    """Advisory score stays in [0, 1]."""
    score = run_evaluation.score_advisory("NOC INCIDENT ACTION 12 root suspected detail")
    assert 0.0 <= score <= 1.0


def test_build_summary_returns_dataclass() -> None:
    """Summary object contains expected numeric fields."""
    dataset = run_evaluation.load_test_set()
    summary = run_evaluation.build_summary(dataset)
    assert 0.0 <= summary.root_cause_accuracy_baseline <= 1.0
    assert 0.0 <= summary.root_cause_accuracy_optimized <= 1.0
    assert 0.0 <= summary.domain_accuracy <= 1.0
    assert 0.0 <= summary.severity_accuracy <= 1.0
    assert 0.0 <= summary.advisory_compliance <= 1.0


def test_render_markdown_contains_sections() -> None:
    """Rendered markdown contains all report sections."""
    dataset = run_evaluation.load_test_set()
    summary = run_evaluation.build_summary(dataset)
    out = run_evaluation.render_markdown(summary)
    assert "## Normalizer Agent" in out
    assert "## Correlation Agent" in out
    assert "## Communications Agent" in out
    assert "## Latency" in out


def test_main_guard_present() -> None:
    """Script has standard main guard."""
    content = Path(run_evaluation.__file__).read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in content
