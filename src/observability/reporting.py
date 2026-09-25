from __future__ import annotations

from typing import Any

from pathlib import Path

from core.utils import write_text


def _number(metrics: dict[str, Any], key: str) -> float:
    value = metrics.get(key, 0)
    return float(value) if isinstance(value, int | float) else 0.0


def _metric_rows(metrics: dict[str, Any]) -> str:
    return "\n".join(
        (
            f"| Retrieval hit rate | {_number(metrics, 'retrieval_hit_rate'):.2%} |",
            f"| Mean token F1 | {_number(metrics, 'mean_token_f1'):.4f} |",
            f"| Judge accuracy | {_number(metrics, 'judge_accuracy'):.2%} |",
            f"| Mean judge score | {_number(metrics, 'mean_judge_score'):.2f} / 5 |",
        )
    )

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline pipeline report from its generated artefacts."""
    gx_status = "PASS" if quality.get("success") else "FAIL"
    fresh_status = "Fresh" if freshness.get("is_fresh") else "Stale"
    content = f"""# Data Pipeline Phase 1 — Baseline Report

## Source summary

| Field | Value |
|---|---|
| Source API | {source_summary.get('source', 'N/A')} |
| Query | {source_summary.get('query', 'N/A')} |
| Records indexed | {source_summary.get('records', 0)} |
| Run date | {source_summary.get('run_date', 'N/A')} |

## Retrieval and evaluation metrics

| Metric | Value |
|---|---:|
{_metric_rows(metrics)}

## Data quality — Great Expectations 1.x

| Field | Value |
|---|---|
| Overall status | {gx_status} |
| Expectations evaluated | {quality.get('statistics', {}).get('evaluated_expectations', 'N/A')} |
| Expectations successful | {quality.get('statistics', {}).get('successful_expectations', 'N/A')} |

## Freshness SLA

| Field | Value |
|---|---|
| Status | {fresh_status} |
| Latest published | {freshness.get('latest_published', 'N/A')} |
| Oldest published | {freshness.get('oldest_published', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)} |
| Stale ratio | {_number(freshness, 'stale_ratio'):.1%} |
| Threshold | {freshness.get('threshold_days', 'N/A')} days |
"""
    write_text(Path(report_path), content)
    print(f"[Report] Phase 1 report written: {report_path}")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the required baseline/corrupted/repaired comparison report."""
    def fmt(metrics: dict[str, Any], key: str, percent: bool = False) -> str:
        value = _number(metrics, key)
        return f"{value:.2%}" if percent else f"{value:.4f}"

    gx_corrupted = "PASS" if corrupted_quality.get("success") else "FAIL"
    gx_repaired = "PASS" if repaired_quality.get("success") else "FAIL"
    freshness_corrupted_status = "Fresh" if corrupted_freshness.get("is_fresh") else "Stale"
    freshness_repaired_status = "Fresh" if repaired_freshness.get("is_fresh") else "Stale"
    content = f"""# Data Corruption & Repair Report — 3-State Comparison

## Baseline, corrupted, and repaired

| Metric / signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | {fmt(baseline_metrics, 'retrieval_hit_rate', True)} | {fmt(corrupted_metrics, 'retrieval_hit_rate', True)} | {fmt(repaired_metrics, 'retrieval_hit_rate', True)} |
| Mean token F1 | {fmt(baseline_metrics, 'mean_token_f1')} | {fmt(corrupted_metrics, 'mean_token_f1')} | {fmt(repaired_metrics, 'mean_token_f1')} |
| Judge accuracy | {fmt(baseline_metrics, 'judge_accuracy', True)} | {fmt(corrupted_metrics, 'judge_accuracy', True)} | {fmt(repaired_metrics, 'judge_accuracy', True)} |
| Mean judge score | {fmt(baseline_metrics, 'mean_judge_score')} | {fmt(corrupted_metrics, 'mean_judge_score')} | {fmt(repaired_metrics, 'mean_judge_score')} |
| GX quality gate | PASS (baseline artifact) | {gx_corrupted} | {gx_repaired} |
| Freshness SLA | {freshness_repaired_status} (same clean source as repair) | {freshness_corrupted_status} | {freshness_repaired_status} |

## Evidence-based interpretation

The corrupted collection was evaluated against the unchanged benchmark test set, so differences in retrieval and answer metrics are attributable to the altered data/index rather than a changed test. The quality gate is expected to flag missing summaries and duplicated document IDs. Repair rebuilds from the preserved raw source and reruns cleaning, rather than manually editing corrupted rows.

| Freshness signal | Corrupted | Repaired |
|---|---:|---:|
| Stale rows | {corrupted_freshness.get('stale_rows', 0)} / {corrupted_freshness.get('total_rows', 0)} | {repaired_freshness.get('stale_rows', 0)} / {repaired_freshness.get('total_rows', 0)} |
| Stale ratio | {_number(corrupted_freshness, 'stale_ratio'):.1%} | {_number(repaired_freshness, 'stale_ratio'):.1%} |
"""
    write_text(Path(report_path), content)
    print(f"[Report] Corruption comparison report written: {report_path}")
