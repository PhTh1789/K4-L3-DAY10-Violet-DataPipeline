from __future__ import annotations

from typing import Any

import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the Great Expectations 1.x data quality gate on a dataframe."""
    required_columns = {"paper_id", "title", "summary", "text_for_embedding", "published", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Quality gate cannot run; missing columns: {', '.join(missing_columns)}")

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"{report_name}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{report_name}_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"{report_name}_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        ExpectColumnValuesToNotBeNull(column="paper_id"),
        ExpectColumnValuesToNotBeNull(column="title"),
        ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        ExpectColumnValuesToBeUnique(column="paper_id"),
        ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results: list[dict[str, Any]] = []
    for expectation in expectations:
        try:
            result = batch.validate(expectation)
            results.append(result.to_json_dict())
        except Exception as exc:
            results.append(
                {
                    "success": False,
                    "expectation_config": expectation.configuration.to_json_dict(),
                    "exception_info": {
                        "raised_exception": True,
                        "exception_message": str(exc),
                    },
                }
            )

    blank_values: dict[str, int] = {}
    for column in ("paper_id", "title", "text_for_embedding"):
        blank_values[column] = int(
            df[column].isna().sum()
            + df[column].astype("string").str.strip().eq("").sum()
        )
    non_empty = all(count == 0 for count in blank_values.values())
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    payload = {
        "success": all(item.get("success", False) for item in results)
        and non_empty
        and freshness["is_fresh"],
        "report_name": report_name,
        "row_count": int(len(df)),
        "statistics": {
            "evaluated_expectations": len(results),
            "successful_expectations": sum(1 for item in results if item.get("success")),
        },
        "expectations": results,
        "blank_value_counts": blank_values,
        "freshness": freshness,
    }

    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize age distribution and enforce the 25% stale-row SLA."""
    required_columns = {"published", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Freshness report cannot run; missing columns: {', '.join(missing_columns)}")

    if df.empty:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": settings.freshness_threshold_days,
            "max_stale_ratio": 0.25,
            "is_fresh": False,
        }
    else:
        published = pd.to_datetime(df["published"], errors="coerce")
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((ages > settings.freshness_threshold_days).sum())
        total_rows = int(len(df))
        stale_ratio = stale_rows / total_rows if total_rows else 1.0
        payload = {
            "latest_published": published.max().date().isoformat() if published.notna().any() else None,
            "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": stale_ratio,
            "threshold_days": settings.freshness_threshold_days,
            "max_stale_ratio": 0.25,
            "is_fresh": stale_ratio <= 0.25,
        }
    write_json(report_path, payload)
    return payload
