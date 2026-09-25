from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corruption → Evaluate → Repair → Compare Pipeline (Phase 2 / CP4-CP5).

    Execution steps:
    1.  Load settings and baseline metrics from Phase 1.
    2.  Load clean data from the Phase-1 JSON artefact.
    3.  Apply 6-type synthetic corruption; save corrupted artefacts.
    4.  Build corrupted ChromaDB index; evaluate RAG on corrupted data.
    5.  Run GX quality checks + freshness SLA on corrupted data.
    6.  Idempotent repair: re-fetch raw records → re-clean → save repaired artefacts.
    7.  Build repaired ChromaDB index; evaluate RAG on repaired data.
    8.  Run GX quality checks + freshness SLA on repaired data.
    9.  Generate corruption comparison report (3-state Markdown).
    10. Print 3-column summary table to console.
    """
    s = load_settings()
    run_date = now_utc()

    print("=" * 65)
    print("Phase 2 — Corruption → Evaluate → Repair → Compare")
    print("=" * 65)

    # ------------------------------------------------------------------
    # Step 1: Load baseline metrics  (must have run Phase 1 first)
    # ------------------------------------------------------------------
    print("\n[1/8] Loading baseline metrics …")
    if not s.paths.baseline_metrics.exists():
        raise FileNotFoundError(
            f"Baseline metrics not found at {s.paths.baseline_metrics}. "
            "Please run `python script/run_phase1.py` first."
        )
    baseline_metrics = read_json(s.paths.baseline_metrics)
    print(f"      -> Baseline Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0):.2%}")

    # ------------------------------------------------------------------
    # Step 2: Load clean data from Phase-1 JSON
    # ------------------------------------------------------------------
    print("\n[2/8] Loading clean dataset …")
    if not s.paths.clean_json.exists():
        raise FileNotFoundError(
            f"Clean JSON not found at {s.paths.clean_json}. "
            "Please run `python script/run_phase1.py` first."
        )
    df_clean = pd.read_json(str(s.paths.clean_json))
    print(f"      -> {len(df_clean)} clean rows loaded.")

    # ------------------------------------------------------------------
    # Step 3: Apply synthetic data corruption
    # ------------------------------------------------------------------
    print("\n[3/8] Applying synthetic data corruption (6 types) …")
    df_corrupted = corrupt_clean_dataframe(df_clean, s.paths.corruption_log)
    write_csv(df_corrupted, s.paths.corrupted_clean_csv)
    df_corrupted.to_json(
        str(s.paths.corrupted_clean_json), orient="records", indent=2, force_ascii=True
    )
    print(f"      -> Corrupted rows: {len(df_corrupted)} (original: {len(df_clean)})")

    # ------------------------------------------------------------------
    # Step 4: Build corrupted index and evaluate
    # ------------------------------------------------------------------
    print("\n[4/8] Building corrupted ChromaDB index and evaluating …")
    idx_corrupted = LocalEmbeddingIndex.build(df_corrupted, s, s.paths.corrupted_embeddings_json)
    bundle_corrupted = evaluate_pipeline(
        s,
        idx_corrupted,
        s.paths.eval_testset,
        s.paths.corrupted_metrics,
        s.paths.corrupted_answers,
    )
    print(f"      -> Corrupted Hit Rate: {bundle_corrupted.summary['retrieval_hit_rate']:.2%}")
    print(f"      -> Corrupted Token F1: {bundle_corrupted.summary['mean_token_f1']:.4f}")

    # ------------------------------------------------------------------
    # Step 5: GX quality checks + freshness on corrupted data
    # ------------------------------------------------------------------
    print("\n[5/8] Running quality checks on corrupted data …")
    quality_corrupted = run_data_quality_checks(df_corrupted, s, "corrupted")
    freshness_corrupted = build_freshness_report(
        df_corrupted, s, s.paths.corrupted_quality_report
    )

    # ------------------------------------------------------------------
    # Step 6: Idempotent repair — re-fetch raw → re-clean
    # ------------------------------------------------------------------
    print("\n[6/8] Idempotent Repair: re-loading raw records and re-cleaning …")
    records_repaired = fetch_source_records(s)   # reads from snapshot (offline)
    df_repaired = build_clean_dataframe(records_repaired, run_date)
    write_csv(df_repaired, s.paths.repaired_clean_csv)
    df_repaired.to_json(
        str(s.paths.repaired_clean_json), orient="records", indent=2, force_ascii=True
    )
    print(f"      -> Repaired rows: {len(df_repaired)}")

    # ------------------------------------------------------------------
    # Step 7: Build repaired index and evaluate
    # ------------------------------------------------------------------
    print("\n[7/8] Building repaired ChromaDB index and evaluating …")
    idx_repaired = LocalEmbeddingIndex.build(df_repaired, s, s.paths.repaired_embeddings_json)
    bundle_repaired = evaluate_pipeline(
        s,
        idx_repaired,
        s.paths.eval_testset,
        s.paths.repaired_metrics,
        s.paths.repaired_answers,
    )
    print(f"      -> Repaired Hit Rate: {bundle_repaired.summary['retrieval_hit_rate']:.2%}")
    print(f"      -> Repaired Token F1: {bundle_repaired.summary['mean_token_f1']:.4f}")

    # ------------------------------------------------------------------
    # Step 8: GX quality checks + freshness on repaired data
    # ------------------------------------------------------------------
    print("\n[8/8] Running quality checks on repaired data …")
    quality_repaired = run_data_quality_checks(df_repaired, s, "repaired")
    freshness_repaired = build_freshness_report(df_repaired, s, s.paths.freshness_report)

    # ------------------------------------------------------------------
    # Step 9: Generate Markdown comparison report
    # ------------------------------------------------------------------
    generate_corruption_report(
        s.paths.comparison_report,
        baseline_metrics,
        bundle_corrupted.summary,
        bundle_repaired.summary,
        quality_corrupted,
        quality_repaired,
        freshness_corrupted,
        freshness_repaired,
    )
    print(f"\n[Report] Comparison report written to {s.paths.comparison_report}")

    # ------------------------------------------------------------------
    # Step 10: Print 3-column summary table
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("=== SO SÁNH 3 TRẠNG THÁI (BASELINE vs CORRUPTED vs REPAIRED) ===")
    print("=" * 65)
    header = f"{'Metric':<28} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}"
    print(header)
    print("-" * 65)
    for key, label in [
        ("retrieval_hit_rate", "Hit Rate"),
        ("mean_token_f1",      "Token F1"),
        ("judge_accuracy",     "Judge Acc"),
        ("mean_judge_score",   "Judge Score"),
    ]:
        b = baseline_metrics.get(key, 0)
        c = bundle_corrupted.summary.get(key, 0)
        r = bundle_repaired.summary.get(key, 0)
        print(f"{label:<28} {b:>10.4f} {c:>10.4f} {r:>10.4f}")
    print("-" * 65)
    gx_b = "PASS"
    gx_c = "PASS" if quality_corrupted.get("success") else "FAIL"
    gx_r = "PASS" if quality_repaired.get("success") else "FAIL"
    fr_b = "Fresh"
    fr_c = "Fresh" if freshness_corrupted.get("is_fresh") else "Stale"
    fr_r = "Fresh" if freshness_repaired.get("is_fresh") else "Stale"
    print(f"{'GX Quality Gate':<28} {gx_b:>10} {gx_c:>10} {gx_r:>10}")
    print(f"{'Freshness SLA':<28} {fr_b:>10} {fr_c:>10} {fr_r:>10}")
    print("=" * 65)
    print("Phase 2 Corruption Flow HOÀN THÀNH!")
