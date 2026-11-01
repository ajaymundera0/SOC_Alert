-- =============================================================================
-- Detection Rule Performance Analysis
-- =============================================================================

-- Per-rule scorecard
SELECT
    detection_rule,
    alert_volume,
    tp_count,
    bp_count,
    fp_count,
    precision,
    fp_rate,
    tp_rate,
    volume_share,
    fp_volume_share,
    tp_volume_share
FROM dim_rule_performance
ORDER BY fp_count DESC;

-- Ranking A: Raw FP count
SELECT
    ROW_NUMBER() OVER (ORDER BY fp_count DESC) AS rank_by_fp_count,
    detection_rule,
    fp_count,
    alert_volume,
    precision
FROM dim_rule_performance
ORDER BY fp_count DESC;

-- Ranking B: FP rate
SELECT
    ROW_NUMBER() OVER (ORDER BY fp_rate DESC) AS rank_by_fp_rate,
    detection_rule,
    fp_rate,
    fp_count,
    alert_volume
FROM dim_rule_performance
WHERE alert_volume >= 30     -- Minimum volume threshold
ORDER BY fp_rate DESC;

-- Ranking C: Volume-weighted FP burden
-- FP burden = fp_count × fp_rate (rewards high-volume, high-FP-rate rules)
SELECT
    ROW_NUMBER() OVER (ORDER BY fp_count * fp_rate DESC) AS rank_by_burden,
    detection_rule,
    fp_count,
    fp_rate,
    ROUND(fp_count * fp_rate, 2) AS fp_burden_score,
    alert_volume,
    precision
FROM dim_rule_performance
ORDER BY fp_burden_score DESC;

-- Pareto: cumulative FP contribution
SELECT
    detection_rule,
    fp_count,
    tp_count,
    alert_volume,
    SUM(fp_count) OVER (ORDER BY fp_count DESC) AS cumulative_fp,
    ROUND(
        SUM(fp_count) OVER (ORDER BY fp_count DESC)::DOUBLE
        / NULLIF(SUM(fp_count) OVER (), 0) * 100, 2
    ) AS cumulative_fp_pct
FROM dim_rule_performance
ORDER BY fp_count DESC;
