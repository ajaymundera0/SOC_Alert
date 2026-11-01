"""Statistical analysis — confidence intervals, chi-square tests, FDR correction."""

import math
from dataclasses import dataclass

import duckdb
import numpy as np
from scipy import stats

from src.config import load_config, get_analysis_params


# ── Wilson Confidence Interval ───────────────────────────────────────────────

@dataclass
class WilsonCI:
    proportion: float
    lower: float
    upper: float
    n: int
    successes: int


def wilson_confidence_interval(successes: int, n: int, confidence: float = 0.95) -> WilsonCI:
    """
    Wilson score interval for a binomial proportion.

    Preferred over normal approximation because:
    - Valid for proportions near 0 or 1
    - Valid for small sample sizes
    - Always produces intervals within [0, 1]
    - Does not require np > 5 assumption
    """
    if n == 0:
        return WilsonCI(proportion=0.0, lower=0.0, upper=0.0, n=0, successes=0)

    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = successes / n
    denominator = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denominator
    margin = (z / denominator) * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))

    return WilsonCI(
        proportion=round(p_hat, 6),
        lower=round(max(0.0, centre - margin), 6),
        upper=round(min(1.0, centre + margin), 6),
        n=n,
        successes=successes,
    )


def compute_rule_precision_ci(db_path: str, confidence: float = 0.95) -> list[dict]:
    """Compute Wilson CI for precision for every detection rule."""
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT detection_rule, tp_count, fp_count, alert_volume
        FROM dim_rule_performance
        ORDER BY alert_volume DESC
    """).fetchall()
    con.close()

    results = []
    for rule, tp, fp, vol in rows:
        n = tp + fp
        ci = wilson_confidence_interval(tp, n, confidence)
        results.append({
            "detection_rule": rule,
            "tp_count": tp,
            "fp_count": fp,
            "alert_volume": vol,
            "n_tp_fp": n,
            "precision": ci.proportion,
            "ci_lower": ci.lower,
            "ci_upper": ci.upper,
        })
    return results


# ── Chi-Square Tests ─────────────────────────────────────────────────────────

@dataclass
class ChiSquareResult:
    test_name: str
    h0: str
    h1: str
    chi2: float
    dof: int
    p_value: float
    cramers_v: float
    significant: bool
    alpha: float


def chi_square_test(
    contingency_table: np.ndarray,
    test_name: str,
    h0: str,
    h1: str,
    alpha: float = 0.05,
) -> ChiSquareResult:
    """Run chi-square test of independence with Cramér's V effect size."""
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency_table)

    n = contingency_table.sum()
    k = min(contingency_table.shape) - 1
    cramers_v = math.sqrt(chi2 / (n * k)) if n * k > 0 else 0.0

    return ChiSquareResult(
        test_name=test_name,
        h0=h0,
        h1=h1,
        chi2=round(chi2, 4),
        dof=dof,
        p_value=p_value,
        cramers_v=round(cramers_v, 4),
        significant=p_value < alpha,
        alpha=alpha,
    )


def _build_contingency(db_path: str, group_col: str, min_count: int = 5) -> np.ndarray | None:
    """Build a contingency table of analyst_grade × group_col from the fact table."""
    con = duckdb.connect(db_path, read_only=True)

    groups = con.execute(f"""
        SELECT CAST({group_col} AS VARCHAR) AS grp, analyst_grade, COUNT(*) AS cnt
        FROM fact_alerts
        WHERE {group_col} IS NOT NULL AND CAST({group_col} AS VARCHAR) != 'unknown'
        GROUP BY CAST({group_col} AS VARCHAR), analyst_grade
    """).fetchall()
    con.close()

    if not groups:
        return None

    group_labels = sorted(set(r[0] for r in groups))
    grade_labels = sorted(set(r[1] for r in groups))

    group_idx = {g: i for i, g in enumerate(group_labels)}
    grade_idx = {g: i for i, g in enumerate(grade_labels)}

    table = np.zeros((len(group_labels), len(grade_labels)), dtype=int)
    for grp, grade, cnt in groups:
        table[group_idx[grp], grade_idx[grade]] = cnt

    row_sums = table.sum(axis=1)
    mask = row_sums >= min_count
    if mask.sum() < 2:
        return None
    return table[mask]


def run_chi_square_tests(db_path: str, alpha: float = 0.05) -> list[ChiSquareResult]:
    """Run all planned chi-square tests."""
    tests_config = [
        {
            "group_col": "alert_hour",
            "test_name": "Grade × Hour of Day",
            "h0": "Analyst grade is independent of hour of day.",
            "h1": "Analyst grade is associated with hour of day.",
        },
        {
            "group_col": "entity_type",
            "test_name": "Grade × Entity Type",
            "h0": "Analyst grade is independent of entity type.",
            "h1": "Analyst grade is associated with entity type.",
        },
        {
            "group_col": "mitre_technique",
            "test_name": "Grade × MITRE Technique",
            "h0": "Analyst grade is independent of MITRE ATT&CK technique.",
            "h1": "Analyst grade is associated with MITRE ATT&CK technique.",
        },
        {
            "group_col": "detection_rule",
            "test_name": "Grade × Detection Rule",
            "h0": "Analyst grade is independent of detection rule.",
            "h1": "Analyst grade is associated with detection rule.",
        },
    ]

    results = []
    for tc in tests_config:
        ct = _build_contingency(db_path, tc["group_col"])
        if ct is None:
            print(f"  Skipping {tc['test_name']}: insufficient data")
            continue

        result = chi_square_test(
            contingency_table=ct,
            test_name=tc["test_name"],
            h0=tc["h0"],
            h1=tc["h1"],
            alpha=alpha,
        )
        results.append(result)
    return results


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[dict]:
    """
    Apply Benjamini-Hochberg FDR correction.

    When testing many hypotheses simultaneously (e.g., comparing precision
    across dozens of detection rules), the chance of at least one false
    positive grows. BH controls the expected proportion of false discoveries
    among rejected hypotheses, which is more appropriate than Bonferroni
    when we expect some true effects.
    """
    m = len(p_values)
    if m == 0:
        return []

    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    results = [None] * m

    for rank, (orig_idx, p) in enumerate(indexed, 1):
        bh_threshold = (rank / m) * alpha
        results[orig_idx] = {
            "original_index": orig_idx,
            "p_value": p,
            "rank": rank,
            "bh_threshold": round(bh_threshold, 6),
            "significant_after_correction": p <= bh_threshold,
        }
    return results


# ── Overall Triage Metrics ───────────────────────────────────────────────────

def compute_overall_metrics(db_path: str) -> dict:
    """Compute top-level triage performance metrics."""
    con = duckdb.connect(db_path, read_only=True)
    row = con.execute("""
        SELECT
            COUNT(*)                AS total_alerts,
            SUM(is_tp)              AS total_tp,
            SUM(is_bp)              AS total_bp,
            SUM(is_fp)              AS total_fp,
            MIN(alert_timestamp)    AS first_alert,
            MAX(alert_timestamp)    AS last_alert
        FROM fact_alerts
    """).fetchone()
    con.close()

    total, tp, bp, fp = row[0], row[1], row[2], row[3]
    first_alert, last_alert = row[4], row[5]

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    fp_rate = fp / total if total > 0 else None
    tp_rate = tp / total if total > 0 else None
    bp_rate = bp / total if total > 0 else None

    return {
        "total_alerts": total,
        "total_tp": tp,
        "total_bp": bp,
        "total_fp": fp,
        "precision": round(precision, 4) if precision else None,
        "fp_rate": round(fp_rate, 4) if fp_rate else None,
        "tp_rate": round(tp_rate, 4) if tp_rate else None,
        "bp_rate": round(bp_rate, 4) if bp_rate else None,
        "first_alert": str(first_alert),
        "last_alert": str(last_alert),
        "observation_days": (last_alert - first_alert).days if first_alert and last_alert else None,
    }


# ── Pareto Analysis ─────────────────────────────────────────────────────────

def compute_pareto(db_path: str) -> list[dict]:
    """Compute cumulative FP distribution across detection rules (descending FP)."""
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT
            detection_rule,
            fp_count,
            tp_count,
            alert_volume,
            SUM(fp_count) OVER (ORDER BY fp_count DESC) AS cum_fp,
            SUM(tp_count) OVER (ORDER BY fp_count DESC) AS cum_tp,
            SUM(alert_volume) OVER (ORDER BY fp_count DESC) AS cum_volume
        FROM dim_rule_performance
        ORDER BY fp_count DESC
    """).fetchall()
    con.close()

    total_fp = sum(r[1] for r in rows)
    total_tp = sum(r[2] for r in rows)
    total_vol = sum(r[3] for r in rows)

    results = []
    for rule, fp, tp, vol, cum_fp, cum_tp, cum_vol in rows:
        results.append({
            "detection_rule": rule,
            "fp_count": fp,
            "tp_count": tp,
            "alert_volume": vol,
            "cum_fp_pct": round(cum_fp / total_fp * 100, 2) if total_fp > 0 else 0,
            "cum_tp_pct": round(cum_tp / total_tp * 100, 2) if total_tp > 0 else 0,
            "cum_volume_pct": round(cum_vol / total_vol * 100, 2) if total_vol > 0 else 0,
        })
    return results


if __name__ == "__main__":
    cfg = load_config()
    db_path = cfg["paths"]["database"]

    print("=== Overall Metrics ===")
    metrics = compute_overall_metrics(db_path)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    print("\n=== Chi-Square Tests ===")
    chi_results = run_chi_square_tests(db_path, alpha=get_analysis_params(cfg)["alpha"])
    for r in chi_results:
        sig = "SIGNIFICANT" if r.significant else "not significant"
        print(f"  {r.test_name}: χ²={r.chi2}, p={r.p_value:.4e}, V={r.cramers_v} [{sig}]")

    print("\n=== Pareto (top 5 FP generators) ===")
    pareto = compute_pareto(db_path)
    for p in pareto[:5]:
        print(f"  {p['detection_rule']}: FP={p['fp_count']}, cumFP={p['cum_fp_pct']}%")
