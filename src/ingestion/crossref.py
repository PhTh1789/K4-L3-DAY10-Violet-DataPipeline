from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import ensure_parent, write_json


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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_jats(text: str) -> str:
    """Strip JATS XML tags (e.g. <jats:p>, </jats:italic>) and normalise whitespace."""
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_date_parts(date_parts: list) -> str:
    """Convert Crossref date-parts [[YYYY, MM, DD]] to 'YYYY-MM-DD' string."""
    if not date_parts:
        return ""
    parts = date_parts[0]
    try:
        if len(parts) >= 3:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        if len(parts) == 2:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
        if len(parts) == 1:
            return f"{int(parts[0]):04d}-01-01"
    except (TypeError, ValueError):
        pass
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref Works API JSON payload into a list of PaperRecord objects.

    Handles:
    - DOI as paper_id
    - title (Crossref returns a list, take first element)
    - abstract with JATS XML tags stripped
    - authors assembled as "Given Family" strings
    - subject list as categories
    - published date-parts converted to ISO date string
    - URL as abs_url
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = (item.get("DOI") or "").strip()
        title_list = item.get("title") or []
        title = _clean_jats(title_list[0]) if title_list else ""

        # Skip records without a usable DOI or title
        if not paper_id or not title:
            continue

        summary = _clean_jats(item.get("abstract") or "")

        authors: list[str] = []
        for author in item.get("author") or []:
            given = (author.get("given") or "").strip()
            family = (author.get("family") or "").strip()
            full = f"{given} {family}".strip()
            if full:
                authors.append(full)

        categories: list[str] = item.get("subject") or []
        primary_category = categories[0] if categories else ""

        published = _parse_date_parts(
            (item.get("published") or {}).get("date-parts") or []
        )
        # Crossref does not expose an "updated" field; mirror published
        updated = published

        abs_url = (item.get("URL") or "").strip()
        # Crossref does not provide direct PDF links
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch paper records from Crossref API (or fall back to local snapshot).

    Strategy:
    - OFFLINE / default: if ``settings.refresh_source`` is False and the raw
      snapshot already exists, parse that file instead of hitting the network.
    - ONLINE: call Crossref Works API with retry logic for 429 / 503 responses.

    Saves two artefacts:
    - ``settings.paths.raw_api_response``  – the raw Crossref JSON response
    - ``settings.paths.raw_records_json``  – serialised list of PaperRecord dicts
    """
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    # ------------------------------------------------------------------
    # OFFLINE MODE: use the local snapshot when refresh is not requested
    # ------------------------------------------------------------------
    if not settings.refresh_source and raw_response_path.exists():
        print(f"[crossref] OFFLINE: loading snapshot from {raw_response_path}")
        payload = json.loads(raw_response_path.read_text(encoding="utf-8"))
        records = parse_crossref_payload(payload)
        # Persist (or re-persist) the parsed records
        ensure_parent(raw_records_path)
        write_json(raw_records_path, [asdict(r) for r in records])
        print(f"[crossref] Parsed {len(records)} records from snapshot.")
        return records

    # ------------------------------------------------------------------
    # ONLINE MODE: call the Crossref Works endpoint
    # ------------------------------------------------------------------
    url = "https://api.crossref.org/works"
    params: dict = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,URL",
    }

    print(f"[crossref] ONLINE: querying {url} (rows={settings.max_results}) …")
    response = None
    for attempt in range(1, 4):  # up to 3 attempts
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                break
            if response.status_code in (429, 503):
                wait = 5 * attempt
                print(f"[crossref] HTTP {response.status_code} – retrying in {wait}s (attempt {attempt}/3)")
                time.sleep(wait)
            else:
                response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[crossref] Request error on attempt {attempt}: {exc}")
            if attempt == 3:
                raise

    # If all retries resulted in rate-limiting, fall back to snapshot
    if response is None or response.status_code != 200:
        if raw_response_path.exists():
            print("[crossref] All retries failed – falling back to local snapshot.")
            payload = json.loads(raw_response_path.read_text(encoding="utf-8"))
        else:
            raise RuntimeError(
                "Crossref API unavailable and no local snapshot found. "
                "Check your network or add data/raw/crossref_response.json."
            )
    else:
        payload = response.json()
        # Persist raw response for lineage / offline reuse
        ensure_parent(raw_response_path)
        raw_response_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        print(f"[crossref] Raw response saved to {raw_response_path}")

    records = parse_crossref_payload(payload)
    ensure_parent(raw_records_path)
    write_json(raw_records_path, [asdict(r) for r in records])
    print(f"[crossref] {len(records)} records saved to {raw_records_path}")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a previously serialised list of PaperRecord dicts from a JSON file.

    Args:
        path: Path to the JSON file (e.g. ``data/raw/crossref_records.json``).

    Returns:
        A list of ``PaperRecord`` instances reconstructed from the file.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in data]
