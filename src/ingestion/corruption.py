from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def _rebuild_embedding_text(row) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Inject six controlled data quality failures while keeping the row count stable."""
    corrupted = df.copy(deep=True).reset_index(drop=True)
    log: list[dict[str, Any]] = []
    if corrupted.empty:
        write_json(Path(output_log_path), {"input_rows": 0, "output_rows": 0, "scenarios": log})
        return corrupted

    input_rows = len(corrupted)

    drop_count = min(max(1, input_rows // 5), input_rows - 1)
    latest_indices = corrupted.sort_values("published", ascending=False).head(drop_count).index.tolist()
    dropped_ids = corrupted.loc[latest_indices, "paper_id"].tolist()
    corrupted = corrupted.drop(index=latest_indices).reset_index(drop=True)
    log.append({"type": "drop_latest_records", "count": drop_count, "affected_ids": dropped_ids})

    blank_count = min(3, len(corrupted))
    blank_indices = list(range(blank_count))
    corrupted.loc[blank_indices, "summary"] = ""
    log.append({"type": "blank_summary", "count": blank_count, "affected_ids": corrupted.loc[blank_indices, "paper_id"].tolist()})

    noise_count = min(3, len(corrupted))
    noise_indices = list(range(blank_count, min(blank_count + noise_count, len(corrupted))))
    corrupted.loc[noise_indices, "summary"] = (
        corrupted.loc[noise_indices, "summary"].fillna("").astype(str)
        + " @@##$$%% NULL_VECTOR_NOISE 000"
    )
    log.append({"type": "inject_text_noise", "count": len(noise_indices), "affected_ids": corrupted.loc[noise_indices, "paper_id"].tolist()})

    title_count = min(2, len(corrupted))
    title_start = min(blank_count + noise_count, len(corrupted) - title_count)
    title_indices = list(range(title_start, title_start + title_count))
    corrupted.loc[title_indices, "title"] = corrupted.loc[title_indices, "title"].astype(str).str.slice(0, 8)
    log.append({"type": "truncate_title", "count": title_count, "affected_ids": corrupted.loc[title_indices, "paper_id"].tolist()})

    stale_count = min(7, len(corrupted))
    stale_indices = list(range(len(corrupted) - stale_count, len(corrupted)))
    stale_dates = pd.to_datetime(corrupted.loc[stale_indices, "published"], errors="coerce") - pd.Timedelta(days=365 * 5)
    corrupted.loc[stale_indices, "published"] = stale_dates.dt.date.astype(str).tolist()
    corrupted.loc[stale_indices, "age_days"] = pd.to_numeric(corrupted.loc[stale_indices, "age_days"], errors="coerce") + 365 * 5
    log.append({"type": "stale_date", "count": stale_count, "affected_ids": corrupted.loc[stale_indices, "paper_id"].tolist()})

    duplicate_count = input_rows - len(corrupted)
    duplicate_rows = corrupted.head(duplicate_count).copy()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    log.append({"type": "duplicate_rows", "count": duplicate_count, "affected_ids": duplicate_rows["paper_id"].tolist()})

    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_embedding_text, axis=1)
    write_json(
        Path(output_log_path),
        {"input_rows": int(input_rows), "output_rows": int(len(corrupted)), "scenarios": log},
    )
    return corrupted
