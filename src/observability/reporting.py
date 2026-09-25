from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a concise Markdown report for the baseline run."""
    source_count = source_summary.get("records_loaded", source_summary.get("records", 0))
    source_mode = source_summary.get("mode", source_summary.get("source", "unknown"))
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source",
        f"- Records loaded: {source_count}",
        f"- Source: {source_mode}",
        f"- Run date: {source_summary.get('run_date', 'unknown')}",
        "",
        "## RAG Metrics",
        f"- Retrieval hit rate: {metrics.get('retrieval_hit_rate', 0):.3f}",
        f"- Mean token F1: {metrics.get('mean_token_f1', 0):.3f}",
        f"- Judge accuracy: {metrics.get('judge_accuracy', 0):.3f}",
        f"- Mean judge score: {metrics.get('mean_judge_score', 0):.3f}",
        "",
        "## Data Quality Gate",
        f"- Status: {'PASS' if quality.get('success') else 'FAIL'}",
        f"- Rows checked: {quality.get('row_count', 0)}",
        "",
        "## Freshness",
        f"- Latest published: {freshness.get('latest_published')}",
        f"- Oldest published: {freshness.get('oldest_published')}",
        f"- Stale ratio: {freshness.get('stale_ratio', 0):.3f}",
        f"- Freshness SLA: {'PASS' if freshness.get('is_fresh') else 'WARN'}",
        "",
    ]
    write_text(report_path, "\n".join(lines))


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
    """Write a three-state comparison for baseline, corrupted, and repaired data."""
    rows = [
        ("Retrieval hit rate", "retrieval_hit_rate"),
        ("Mean token F1", "mean_token_f1"),
        ("Judge accuracy", "judge_accuracy"),
        ("Mean judge score", "mean_judge_score"),
    ]
    lines = [
        "# Corruption and Repair Report",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "|---|---:|---:|---:|",
    ]
    for label, key in rows:
        lines.append(
            f"| {label} | {baseline_metrics.get(key, 0):.3f} | "
            f"{corrupted_metrics.get(key, 0):.3f} | {repaired_metrics.get(key, 0):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Quality Gate",
            f"- Corrupted: {'PASS' if corrupted_quality.get('success') else 'FAIL'}",
            f"- Repaired: {'PASS' if repaired_quality.get('success') else 'FAIL'}",
            "",
            "## Freshness SLA",
            f"- Corrupted stale ratio: {corrupted_freshness.get('stale_ratio', 0):.3f}",
            f"- Repaired stale ratio: {repaired_freshness.get('stale_ratio', 0):.3f}",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))
