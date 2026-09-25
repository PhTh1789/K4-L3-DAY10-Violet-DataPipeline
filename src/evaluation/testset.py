from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


class TestSet:
    def __init__(self, samples: list[dict[str, Any]]):
        self.samples = samples


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a deterministic five-sample benchmark from the cleaned corpus."""
    if len(df) < 2:
        raise ValueError("At least two documents are required to build the benchmark test set.")

    rows = df.reset_index(drop=True)
    first = rows.iloc[0]
    second = rows.iloc[1]
    third = rows.iloc[2] if len(rows) > 2 else first
    fourth = rows.iloc[3] if len(rows) > 3 else second
    samples = [
        {
            "id": "eval_001",
            "type": "summary",
            "question_type": "summary",
            "question": f"What is the main research summary of the paper '{first['title']}'?",
            "ground_truth": first_sentence(str(first["summary"])),
            "ground_truth_doc_ids": [first["paper_id"]],
        },
        {
            "id": "eval_002",
            "type": "authors",
            "question_type": "authors",
            "question": f"Who authored the study '{second['title']}'?",
            "ground_truth": second["authors_joined"],
            "ground_truth_doc_ids": [second["paper_id"]],
        },
        {
            "id": "eval_003",
            "type": "date",
            "question_type": "date",
            "question": f"When was the paper '{third['title']}' published?",
            "ground_truth": third["published"],
            "ground_truth_doc_ids": [third["paper_id"]],
        },
        {
            "id": "eval_004",
            "type": "category",
            "question_type": "category",
            "question": f"What categories does the paper '{fourth['title']}' belong to?",
            "ground_truth": fourth["categories_joined"],
            "ground_truth_doc_ids": [fourth["paper_id"]],
        },
        {
            "id": "eval_005",
            "type": "multi_hop",
            "question_type": "multi_hop",
            "question": (
                f"Which authors wrote '{first['title']}', and how does its topic relate "
                f"to the categories of '{second['title']}'?"
            ),
            "ground_truth": (
                f"{first['authors_joined']}; {first['categories_joined']}; "
                f"{second['categories_joined']}"
            ),
            "ground_truth_doc_ids": [first["paper_id"], second["paper_id"]],
        },
    ]
    write_json(Path(output_path), samples)
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path) -> TestSet:
    output_path = Path(output_path)
    samples = read_json(output_path) if output_path.exists() else build_test_set(df, output_path)
    return TestSet(samples=samples)
