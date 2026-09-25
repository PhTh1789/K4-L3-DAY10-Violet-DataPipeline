from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate realistic data quality issues on a clean DataFrame.

    Applies six corruption scenarios that mimic production failure modes:

    1. drop_latest     – Drop the 20% most recently published records (simulate missing fresh data).
    2. blank_summary   – Erase the summary field for a random subset of rows.
    3. inject_noise    – Append garbage characters to summaries of another subset.
    4. truncate_title  – Cut titles to < 8 characters for a few rows.
    5. stale_date      – Roll published dates back 365 days for a few rows.
    6. duplicate_rows  – Append duplicate rows to inflate the dataset.

    After applying all mutations, ``text_for_embedding`` is rebuilt so that
    the corrupted text actually reaches the vector index.

    A JSON log describing every mutation is written to ``output_log_path``.

    Args:
        df: Clean DataFrame produced by ``build_clean_dataframe``.
        output_log_path: Destination path for the corruption log JSON.

    Returns:
        A corrupted copy of the input DataFrame (the original is not mutated).
    """
    corrupted = df.copy()
    log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 1. Drop latest records  (20 % of most recent papers)
    # ------------------------------------------------------------------
    n_drop = max(1, int(len(corrupted) * 0.20))
    sorted_desc = corrupted.sort_values("published", ascending=False)
    dropped_ids: list[str] = sorted_desc.head(n_drop)["paper_id"].tolist()
    corrupted = sorted_desc.iloc[n_drop:].reset_index(drop=True)
    log.append({
        "type": "drop_latest",
        "description": f"Dropped {n_drop} most recently published records (20%).",
        "affected_ids": dropped_ids,
        "count": n_drop,
    })
    print(f"[corruption] drop_latest: removed {n_drop} records.")

    # ------------------------------------------------------------------
    # 2. Blank summary  (erase abstract for 3 rows)
    # ------------------------------------------------------------------
    n_blank = min(3, len(corrupted))
    blank_idx = corrupted.sample(n_blank, random_state=42).index.tolist()
    corrupted.loc[blank_idx, "summary"] = ""
    log.append({
        "type": "blank_summary",
        "description": f"Erased summary for {n_blank} rows.",
        "affected_ids": corrupted.loc[blank_idx, "paper_id"].tolist(),
        "count": n_blank,
    })
    print(f"[corruption] blank_summary: cleared {n_blank} summaries.")

    # ------------------------------------------------------------------
    # 3. Inject noise  (append garbage chars to 3 summaries)
    # ------------------------------------------------------------------
    n_noise = min(3, len(corrupted))
    noise_idx = corrupted.sample(n_noise, random_state=7).index.tolist()
    corrupted.loc[noise_idx, "summary"] = corrupted.loc[noise_idx, "summary"].apply(
        lambda s: s + " @@##$$%%" * 3
    )
    log.append({
        "type": "inject_noise",
        "description": f"Appended garbage characters to {n_noise} summaries.",
        "affected_ids": corrupted.loc[noise_idx, "paper_id"].tolist(),
        "count": n_noise,
    })
    print(f"[corruption] inject_noise: corrupted {n_noise} summaries.")

    # ------------------------------------------------------------------
    # 4. Truncate title  (cut to < 8 chars for 2 rows)
    # ------------------------------------------------------------------
    n_trunc = min(2, len(corrupted))
    trunc_idx = corrupted.sample(n_trunc, random_state=13).index.tolist()
    corrupted.loc[trunc_idx, "title"] = corrupted.loc[trunc_idx, "title"].str[:7]
    log.append({
        "type": "truncate_title",
        "description": f"Truncated title to <8 chars for {n_trunc} rows.",
        "affected_ids": corrupted.loc[trunc_idx, "paper_id"].tolist(),
        "count": n_trunc,
    })
    print(f"[corruption] truncate_title: truncated {n_trunc} titles.")

    # ------------------------------------------------------------------
    # 5. Stale date  (roll back published date by 365 days for 4 rows)
    # ------------------------------------------------------------------
    n_stale = min(4, len(corrupted))
    stale_idx = corrupted.sample(n_stale, random_state=99).index.tolist()

    def _stale(date_str: str) -> str:
        try:
            dt = pd.to_datetime(date_str)
            return str((dt - timedelta(days=365)).date())
        except Exception:
            return date_str

    corrupted.loc[stale_idx, "published"] = corrupted.loc[stale_idx, "published"].apply(_stale)
    log.append({
        "type": "stale_date",
        "description": f"Rolled back published date by 365 days for {n_stale} rows.",
        "affected_ids": corrupted.loc[stale_idx, "paper_id"].tolist(),
        "count": n_stale,
    })
    print(f"[corruption] stale_date: aged {n_stale} records by 365 days.")

    # ------------------------------------------------------------------
    # 6. Duplicate rows  (append 3 duplicate rows)
    # ------------------------------------------------------------------
    n_dup = min(3, len(corrupted))
    dup_rows = corrupted.sample(n_dup, random_state=55)
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log.append({
        "type": "duplicate_rows",
        "description": f"Appended {n_dup} duplicate rows to the DataFrame.",
        "duplicated_ids": dup_rows["paper_id"].tolist(),
        "count": n_dup,
    })
    print(f"[corruption] duplicate_rows: added {n_dup} duplicate rows.")

    # ------------------------------------------------------------------
    # 7. Rebuild text_for_embedding after corruption
    # ------------------------------------------------------------------
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda r: (
            f"Title: {r['title']}\n"
            f"Authors: {r['authors_joined']}\n"
            f"Published: {r['published']}\n"
            f"Categories: {r['categories_joined']}\n"
            f"Summary: {r['summary']}"
        ),
        axis=1,
    )

    # ------------------------------------------------------------------
    # 8. Write corruption log
    # ------------------------------------------------------------------
    write_json(Path(output_log_path), log)
    print(f"[corruption] Log written to {output_log_path} ({len(log)} corruption types applied).")

    return corrupted
