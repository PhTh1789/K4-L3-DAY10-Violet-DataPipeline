from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the required Great Expectations 1.x quality gate on ``df``.

    The ephemeral context deliberately keeps GX state in memory; the portable JSON
    validation result is the artefact retained by the pipeline.
    """
    required_columns = {"paper_id", "title", "summary", "text_for_embedding"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Quality gate cannot run; missing columns: {', '.join(missing_columns)}")

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        f"papers_batch_{report_name}"
    )

    suite = context.suites.add(gx.ExpectationSuite(name=f"papers_suite_{report_name}"))
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    )
    for column in ("paper_id", "title", "text_for_embedding"):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=column))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="summary", min_value=30, max_value=None
        )
    )

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"papers_validation_{report_name}",
            data=batch_definition,
            suite=suite,
        )
    )
    result = validation_definition.run(batch_parameters={"dataframe": df})
    result_json = result.to_json_dict()
    payload: dict[str, Any] = {
        "success": bool(result.success),
        "report_name": report_name,
        "statistics": result_json.get("statistics", {}),
        "results": [item.to_json_dict() for item in result.results],
    }

    report_path = (
        settings.paths.baseline_quality_report
        if report_name == "baseline"
        else settings.paths.corrupted_quality_report
    )
    write_json(report_path, payload)
    print(f"[GX] Quality check ({report_name}): {'PASS' if payload['success'] else 'FAIL'}")
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise freshness from the ``age_days`` data contract and persist it."""
    required_columns = {"published", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Freshness report cannot run; missing columns: {', '.join(missing_columns)}")

    published = pd.to_datetime(df["published"], errors="coerce")
    age_days = pd.to_numeric(df["age_days"], errors="coerce")
    stale_mask = age_days > settings.freshness_threshold_days
    stale_rows = int(stale_mask.fillna(False).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    is_fresh = stale_ratio <= 0.25

    latest = published.max()
    oldest = published.min()
    payload: dict[str, Any] = {
        "latest_published": str(latest.date()) if pd.notna(latest) else None,
        "oldest_published": str(oldest.date()) if pd.notna(oldest) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }
    write_json(report_path, payload)
    if is_fresh:
        print(f"[Freshness] OK — {stale_ratio:.1%} stale ({stale_rows}/{total_rows}).")
    else:
        print(
            f"[Freshness] ALERT — {stale_ratio:.1%} of records are older than "
            f"{settings.freshness_threshold_days} days."
        )
    return payload
