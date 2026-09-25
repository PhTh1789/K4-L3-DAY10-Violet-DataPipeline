from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize records, calculate age, deduplicate, and build embedding text."""
    run_date = run_date.replace(tzinfo=None)
    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(re.sub(r"<[^>]+>", " ", record.summary or ""))
        authors = [normalize_whitespace(str(value)) for value in record.authors if normalize_whitespace(str(value))]
        categories = [normalize_whitespace(str(value)) for value in record.categories if normalize_whitespace(str(value))]
        try:
            published_date = pd.to_datetime(record.published, utc=True).date()
        except (TypeError, ValueError):
            continue
        try:
            updated_date = pd.to_datetime(record.updated or record.published, utc=True).date()
        except (TypeError, ValueError):
            updated_date = published_date
        if not paper_id or not title or not summary:
            continue
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category),
                "published": published_date.isoformat(),
                "updated": updated_date.isoformat(),
                "age_days": max(0, (run_date.date() - published_date).days),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": "\n".join(
                    [
                        f"Title: {title}",
                        f"Authors: {authors_joined}",
                        f"Published: {published_date.isoformat()}",
                        f"Categories: {categories_joined}",
                        f"Summary: {summary}",
                    ]
                ),
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
            }
        )
    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category",
        "published", "updated", "age_days", "authors_joined", "categories_joined",
        "summary_chars", "text_for_embedding", "abs_url", "pdf_url", "comment",
    ]
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return (
        result.drop_duplicates(subset=["paper_id"], keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
