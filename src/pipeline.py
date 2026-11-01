"""End-to-end pipeline orchestrator - run everything with one command."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config, get_analysis_params, get_cost_params
from src.ingest import run_ingestion
from src.clean import clean_alerts
from src.transform import build_database
from src.statistics import (
    compute_overall_metrics,
    run_chi_square_tests,
    benjamini_hochberg,
    compute_pareto,
)
from src.cost_model import compute_cost_estimate, format_cost_report
from src.visualize import generate_all_charts


def run_pipeline(config_path: Path | None = None) -> None:
    start = time.time()
    cfg = load_config(config_path)
    analysis = get_analysis_params(cfg)

    print("=" * 70)
    print("SECURITY ALERT TRIAGE ANALYTICS - PIPELINE")
    print("=" * 70)

    # ── Stage 1: Ingest ──────────────────────────────────────────────────
    print("\n[1/6] INGESTION")
    raw_path = run_ingestion(cfg)

    # ── Stage 2: Clean ───────────────────────────────────────────────────
    print("\n[2/6] CLEANING & NORMALISATION")
    clean_path = clean_alerts(cfg)

    # ── Stage 3: Transform ───────────────────────────────────────────────
    print("\n[3/6] BUILDING ANALYTICAL DATABASE")
    db_path = build_database(cfg)

    # ── Stage 4: Statistics ──────────────────────────────────────────────
    print("\n[4/6] STATISTICAL ANALYSIS")
    metrics = compute_overall_metrics(db_path)
    print("\n  Overall Triage Performance:")
    print(f"    Total alerts:    {metrics['total_alerts']:>12,}")
    print(f"    True Positives:  {metrics['total_tp']:>12,}")
    print(f"    Benign Positives:{metrics['total_bp']:>12,}")
    print(f"    False Positives: {metrics['total_fp']:>12,}")
    print(f"    Precision:       {metrics['precision']:>12}")
    print(f"    FP Rate:         {metrics['fp_rate']:>12}")
    print(f"    Observation:     {metrics['observation_days']:>12} days")

    chi_results = run_chi_square_tests(db_path, alpha=analysis["alpha"])
    if chi_results:
        print("\n  Chi-Square Tests:")
        p_values = [r.p_value for r in chi_results]
        bh = benjamini_hochberg(p_values, alpha=analysis["alpha"])
        for r, bh_result in zip(chi_results, bh):
            sig_raw = "significant" if r.significant else "not significant"
            sig_bh = "significant" if bh_result["significant_after_correction"] else "not significant"
            print(f"    {r.test_name}:")
            print(f"      chi2={r.chi2}, df={r.dof}, p={r.p_value:.4e}, Cramer's V={r.cramers_v}")
            print(f"      Raw: {sig_raw} | After BH correction: {sig_bh}")

    pareto = compute_pareto(db_path)
    if pareto:
        print("\n  Pareto Analysis (top FP generators):")
        for threshold in [50, 80, 90]:
            rules_at = [p for p in pareto if p["cum_fp_pct"] <= threshold]
            count = len(rules_at) + 1 if rules_at else 1
            actual_pct = pareto[min(count - 1, len(pareto) - 1)]["cum_fp_pct"]
            print(f"    {count} rule(s) account for ~{actual_pct}% of FP volume")

    # ── Stage 5: Cost Model ──────────────────────────────────────────────
    print("\n[5/6] COST MODEL")
    estimate = compute_cost_estimate(db_path, get_cost_params(cfg))
    print(format_cost_report(estimate))

    # ── Stage 6: Visualisations ──────────────────────────────────────────
    print("\n[6/6] GENERATING VISUALISATIONS")
    generate_all_charts(cfg)

    elapsed = time.time() - start
    print(f"\nPipeline completed in {elapsed:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    run_pipeline(config_path)
