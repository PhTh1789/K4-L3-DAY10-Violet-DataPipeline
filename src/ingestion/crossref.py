from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

import requests

from core.config import Settings
from core.utils import normalize_whitespace, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse and normalize a Crossref REST response."""

    def clean_markup(value: str) -> str:
        return normalize_whitespace(re.sub(r"<[^>]+>", " ", value or ""))

    def iso_date(value: object) -> str:
        parts = value.get("date-parts", []) if isinstance(value, dict) else []
        parts = parts[0] if parts else []
        if not parts:
            return ""
        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            return ""

    records: list[PaperRecord] = []
    for item in payload.get("message", {}).get("items", []):
        paper_id = normalize_whitespace(str(item.get("DOI") or item.get("doi") or "")).lower()
        title_value = item.get("title", "")
        if isinstance(title_value, list):
            title_value = title_value[0] if title_value else ""
        title = clean_markup(str(title_value))
        summary = clean_markup(str(item.get("abstract") or item.get("summary") or ""))

        authors: list[str] = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            given = normalize_whitespace(str(author.get("given") or ""))
            family = normalize_whitespace(str(author.get("family") or author.get("name") or ""))
            full_name = normalize_whitespace(f"{given} {family}")
            if full_name:
                authors.append(full_name)

        categories = [
            normalize_whitespace(str(value))
            for value in (item.get("subject") or item.get("category") or [])
            if normalize_whitespace(str(value))
        ]
        published = iso_date(item.get("published") or item.get("published-print") or item.get("issued"))
        created = item.get("created", {})
        updated = str(created.get("date-time") or "")[:10] if isinstance(created, dict) else ""
        try:
            updated = date.fromisoformat(updated).isoformat()
        except ValueError:
            updated = published

        if not paper_id or not title or not summary or not published:
            continue
        abs_url = normalize_whitespace(str(item.get("URL") or f"https://doi.org/{paper_id}"))
        links = item.get("link") or []
        pdf_url = normalize_whitespace(str(links[0].get("URL", "") if links else "")) or abs_url
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated or published,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=normalize_whitespace(str(item.get("comment") or f"Crossref record {paper_id}")),
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records and fall back to the bundled offline snapshot."""
    snapshot_path = settings.paths.raw_api_response
    payload: dict | None = None
    if not settings.refresh_source and snapshot_path.exists():
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    else:
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params={
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "rows": settings.max_results,
                },
                headers={"User-Agent": "data-observability-lab/1.0"},
                timeout=15,
            )
            if response.status_code in {429, 502, 503, 504}:
                raise requests.HTTPError(f"Crossref returned {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            write_json(snapshot_path, payload)
        except (requests.RequestException, ValueError):
            if not snapshot_path.exists():
                raise
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    records = parse_crossref_payload(payload or {})
    write_json(settings.paths.raw_records_json, [record.__dict__ for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load normalized records or parse a raw Crossref payload."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "message" in payload:
        return parse_crossref_payload(payload)
    return [item if isinstance(item, PaperRecord) else PaperRecord(**item) for item in payload]
