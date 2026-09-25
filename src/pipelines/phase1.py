from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Baseline Pipeline — end-to-end run (Phase 1 / CP3).

    Execution steps:
    1.  Load settings from .env.
    2.  Fetch or load raw records (offline fallback to snapshot).
    3.  Clean and normalise data; save clean CSV + JSON artefacts.
    4.  Build ChromaDB 'papers-baseline' vector index.
    5.  Generate (or reload) the 10-question benchmark test set.
    6.  Run RAG evaluation: Hit Rate, Token F1, LLM Judge.
    7.  Run Great Expectations quality checks + Freshness SLA.
    8.  Write Markdown phase-1 report.
    """
    s = load_settings()
    run_date = now_utc()

    print("=" * 60)
    print("Phase 1 — Baseline Pipeline")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Fetch / load raw records
    # ------------------------------------------------------------------
    print("\n[1/7] Fetching source records …")
    records = fetch_source_records(s)
    print(f"      -> {len(records)} records loaded.")

    # ------------------------------------------------------------------
    # Step 2: Clean data
    # ------------------------------------------------------------------
    print("\n[2/7] Cleaning and normalising data …")
    df = build_clean_dataframe(records, run_date)
    print(f"      -> {len(df)} clean rows after deduplication.")

    # Persist clean artefacts
    write_csv(df, s.paths.clean_csv)
    df.to_json(str(s.paths.clean_json), orient="records", indent=2, force_ascii=True)
    print(f"      -> Saved: {s.paths.clean_csv}")
    print(f"      -> Saved: {s.paths.clean_json}")

    # ------------------------------------------------------------------
    # Step 3: Build ChromaDB vector index (baseline collection)
    # ------------------------------------------------------------------
    print("\n[3/7] Building ChromaDB vector index (papers-baseline) …")
    index = LocalEmbeddingIndex.build(df, s, s.paths.embeddings_json)
    print(f"      -> Collection '{s.baseline_collection_name}' ready.")

    # ------------------------------------------------------------------
    # Step 4: Build benchmark test set
    # ------------------------------------------------------------------
    print("\n[4/7] Generating evaluation test set …")
    if s.refresh_test_set or not s.paths.eval_testset.exists():
        build_test_set(df, s.paths.eval_testset)
    else:
        print("      -> Reusing existing test set (set REFRESH_TEST_SET=1 to regenerate).")

    # ------------------------------------------------------------------
    # Step 5: Evaluate baseline RAG pipeline
    # ------------------------------------------------------------------
    print("\n[5/7] Evaluating baseline pipeline …")
    bundle = evaluate_pipeline(
        s,
        index,
        s.paths.eval_testset,
        s.paths.baseline_metrics,
        s.paths.baseline_answers,
    )
    print(f"      -> Hit Rate  : {bundle.summary['retrieval_hit_rate']:.2%}")
    print(f"      -> Token F1  : {bundle.summary['mean_token_f1']:.4f}")
    print(f"      -> Judge Acc : {bundle.summary['judge_accuracy']:.2%}")

    # ------------------------------------------------------------------
    # Step 6: Data Quality checks (Great Expectations 1.x) + Freshness SLA
    # ------------------------------------------------------------------
    print("\n[6/7] Running data quality & freshness checks …")
    quality = run_data_quality_checks(df, s, "baseline")
    freshness = build_freshness_report(df, s, s.paths.freshness_report)

    # ------------------------------------------------------------------
    # Step 7: Write Markdown report
    # ------------------------------------------------------------------
    print("\n[7/7] Generating Phase 1 Markdown report …")
    source_summary = {
        "source":   s.source_api,
        "query":    s.source_query,
        "records":  len(df),
        "run_date": str(run_date.date()),
    }
    generate_phase1_report(
        s.paths.baseline_report,
        source_summary,
        bundle.summary,
        quality,
        freshness,
    )
    print(f"      -> Report: {s.paths.baseline_report}")

    print("\n" + "=" * 60)
    print("Phase 1 Pipeline HOÀN THÀNH!")
    print(f"  Hit Rate : {bundle.summary['retrieval_hit_rate']:.2%}")
    print(f"  Token F1 : {bundle.summary['mean_token_f1']:.4f}")
    print(f"  GX Pass  : {quality.get('success', False)}")
    print(f"  is_fresh : {freshness.get('is_fresh', False)}")
    print("=" * 60)
