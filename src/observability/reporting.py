from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def _number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key, 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a reproducible Markdown report for the baseline pipeline."""
    source_count = source_summary.get("records_loaded", source_summary.get("records", 0))
    source_name = source_summary.get("mode", source_summary.get("source", "unknown"))
    content = f"""# Data Pipeline Phase 1 - Baseline Report

## Source summary

| Field | Value |
|---|---|
| Source | {source_name} |
| Query | {source_summary.get('query', 'N/A')} |
| Records indexed | {source_count} |
| Run date | {source_summary.get('run_date', 'N/A')} |

## Retrieval and evaluation metrics

| Metric | Value |
|---|---:|
| Retrieval hit rate | {_number(metrics, 'retrieval_hit_rate'):.2%} |
| Mean token F1 | {_number(metrics, 'mean_token_f1'):.4f} |
| Judge accuracy | {_number(metrics, 'judge_accuracy'):.2%} |
| Mean judge score | {_number(metrics, 'mean_judge_score'):.2f} / 5 |

## Data quality - Great Expectations 1.x

| Field | Value |
|---|---|
| Overall status | {'PASS' if quality.get('success') else 'FAIL'} |
| Rows checked | {quality.get('row_count', 0)} |
| Expectations evaluated | {quality.get('statistics', {}).get('evaluated_expectations', len(quality.get('expectations', [])))} |
| Expectations successful | {quality.get('statistics', {}).get('successful_expectations', 'N/A')} |

## Freshness SLA

| Field | Value |
|---|---|
| Status | {'Fresh' if freshness.get('is_fresh') else 'Stale'} |
| Latest published | {freshness.get('latest_published', 'N/A')} |
| Oldest published | {freshness.get('oldest_published', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)} |
| Stale ratio | {_number(freshness, 'stale_ratio'):.2%} |
| Threshold | {freshness.get('threshold_days', 'N/A')} days |
"""
    write_text(Path(report_path), content)


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
    """Write the baseline/corrupted/repaired comparison report."""
    content = f"""# Data Corruption and Repair Report - 3-State Comparison

## Baseline, corrupted, and repaired

| Metric / signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | {_number(baseline_metrics, 'retrieval_hit_rate'):.2%} | {_number(corrupted_metrics, 'retrieval_hit_rate'):.2%} | {_number(repaired_metrics, 'retrieval_hit_rate'):.2%} |
| Mean token F1 | {_number(baseline_metrics, 'mean_token_f1'):.4f} | {_number(corrupted_metrics, 'mean_token_f1'):.4f} | {_number(repaired_metrics, 'mean_token_f1'):.4f} |
| Judge accuracy | {_number(baseline_metrics, 'judge_accuracy'):.2%} | {_number(corrupted_metrics, 'judge_accuracy'):.2%} | {_number(repaired_metrics, 'judge_accuracy'):.2%} |
| Mean judge score | {_number(baseline_metrics, 'mean_judge_score'):.2f} / 5 | {_number(corrupted_metrics, 'mean_judge_score'):.2f} / 5 | {_number(repaired_metrics, 'mean_judge_score'):.2f} / 5 |
| GX quality gate | PASS | {'PASS' if corrupted_quality.get('success') else 'FAIL'} | {'PASS' if repaired_quality.get('success') else 'FAIL'} |
| Freshness SLA | Fresh | {'Fresh' if corrupted_freshness.get('is_fresh') else 'Stale'} | {'Fresh' if repaired_freshness.get('is_fresh') else 'Stale'} |

## Freshness evidence

| Signal | Corrupted | Repaired |
|---|---:|---:|
| Stale rows | {corrupted_freshness.get('stale_rows', 0)} / {corrupted_freshness.get('total_rows', 0)} | {repaired_freshness.get('stale_rows', 0)} / {repaired_freshness.get('total_rows', 0)} |
| Stale ratio | {_number(corrupted_freshness, 'stale_ratio'):.2%} | {_number(repaired_freshness, 'stale_ratio'):.2%} |

## Interpretation

The unchanged benchmark test set is used for all three states, so metric differences measure the effect of data/index corruption rather than a changed evaluation set. The corrupted state is expected to fail on duplicate IDs, blank summaries, and stale records. Repair rebuilds the clean dataset and vector index from the preserved raw source.
"""
    write_text(Path(report_path), content)
