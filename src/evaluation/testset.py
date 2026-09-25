from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import ensure_parent, first_sentence, write_json

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build the deterministic ten-question benchmark required by the lab.

    Each question is tied to a document ID, so retrieval hit rate can be measured
    unchanged across the baseline, corrupted, and repaired collections.
    """
    required_columns = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "published"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Test set cannot be built; missing columns: {', '.join(missing_columns)}")
    if len(df) < 5:
        raise ValueError("Test set requires at least 5 clean documents.")

    sampled = df.sample(n=min(10, len(df)), random_state=42).reset_index(drop=True)
    question_types = [
        "summary", "authors", "date", "categories", "summary",
        "authors", "date", "categories", "summary", "authors",
    ]
    test_items: list[dict[str, Any]] = []

    for index, (_, row) in enumerate(sampled.iterrows(), start=1):
        question_type = question_types[index - 1]
        title = str(row["title"])
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"])
        else:
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(row["categories_joined"])

        test_items.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    output_path = Path(output_path)
    ensure_parent(output_path)
    write_json(output_path, test_items)
    print(f"[CP2] Test set saved: {len(test_items)} questions -> {output_path}")
    return test_items
