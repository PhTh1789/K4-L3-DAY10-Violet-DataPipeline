from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _strip_jats(text: str) -> str:
    """Remove any residual JATS / HTML XML tags and normalise whitespace."""
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", text or ""))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Transform raw PaperRecord list into a clean, embedding-ready DataFrame.

    Steps:
    1. Convert list[PaperRecord] -> pd.DataFrame.
    2. Normalise text fields (title, summary) and strip residual JATS tags.
    3. Build helper columns: authors_joined, categories_joined.
    4. Parse 'published' to datetime, compute age_days relative to run_date.
    5. Add summary_chars (character count of cleaned summary).
    6. Build 'text_for_embedding' as a structured 5-part block.
    7. Drop exact duplicates by paper_id (keep first occurrence).
    8. Filter out rows with empty paper_id or title.
    9. Sort by published descending, reset index, return.
    """
    if not records:
        return pd.DataFrame()

    # 1. Flatten dataclasses to dicts -> DataFrame
    rows = []
    for r in records:
        rows.append({
            "paper_id":        r.paper_id,
            "title":           r.title,
            "summary":         r.summary,
            "authors":         r.authors,
            "categories":      r.categories,
            "primary_category": r.primary_category,
            "published":       r.published,
            "updated":         r.updated,
            "abs_url":         r.abs_url,
            "pdf_url":         r.pdf_url,
            "comment":         r.comment,
        })
    df = pd.DataFrame(rows)

    # 2. Normalise text
    df["title"]   = df["title"].fillna("").apply(_strip_jats)
    df["summary"] = df["summary"].fillna("").apply(_strip_jats)

    # 3. Helper joined columns
    df["authors_joined"]    = df["authors"].apply(
        lambda lst: compact_join(lst) if isinstance(lst, list) else normalize_whitespace(str(lst))
    )
    df["categories_joined"] = df["categories"].apply(
        lambda lst: compact_join(lst) if isinstance(lst, list) else normalize_whitespace(str(lst))
    )

    # 4. Parse published date and compute age_days
    df["published_dt"] = pd.to_datetime(df["published"], format="%Y-%m-%d", errors="coerce")

    run_date_only = run_date.date() if hasattr(run_date, "date") else run_date
    df["age_days"] = df["published_dt"].apply(
        lambda d: int((run_date_only - d.date()).days) if pd.notna(d) else 9999
    )

    # Overwrite 'published' with clean ISO string (YYYY-MM-DD)
    df["published"] = df["published_dt"].dt.strftime("%Y-%m-%d").fillna("")
    df.drop(columns=["published_dt"], inplace=True)

    # 5. Summary character count
    df["summary_chars"] = df["summary"].str.len()

    # 6. Build text_for_embedding (5-part canonical format)
    df["text_for_embedding"] = df.apply(
        lambda r: (
            f"Title: {r['title']}\n"
            f"Authors: {r['authors_joined']}\n"
            f"Published: {r['published']}\n"
            f"Categories: {r['categories_joined']}\n"
            f"Summary: {r['summary']}"
        ),
        axis=1,
    )

    # 7. Deduplicate on paper_id (keep first occurrence)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # 8. Filter out rows with empty paper_id or title
    df = df[
        df["paper_id"].str.strip().astype(bool) &
        df["title"].str.strip().astype(bool)
    ]

    # 9. Sort by published descending and reset index
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    return df
