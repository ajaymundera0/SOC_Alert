-- =============================================================================
-- Cost Model Queries
-- =============================================================================
-- NOTE: All cost figures are MODELLED ESTIMATES based on configurable
-- assumptions. The dataset does not contain actual triage duration or salary.

-- Set assumptions as DuckDB variables (override in config.yaml)
SET VARIABLE triage_minutes = 20;
SET VARIABLE hourly_cost = 55.0;
SET VARIABLE working_days = 250;

-- Overall FP cost estimate
SELECT
    SUM(is_fp)                                              AS total_fp_alerts,
    ROUND(SUM(is_fp) * getvariable('triage_minutes') / 60.0, 1)
                                                            AS estimated_fp_hours,
    ROUND(SUM(is_fp) * getvariable('triage_minutes') / 60.0 * getvariable('hourly_cost'), 2)
                                                            AS estimated_fp_cost,
    DATEDIFF('day', MIN(alert_timestamp), MAX(alert_timestamp)) + 1
                                                            AS observation_days,
    ROUND(
        SUM(is_fp) * getvariable('triage_minutes') / 60.0
        / (DATEDIFF('day', MIN(alert_timestamp), MAX(alert_timestamp)) + 1),
    2)                                                      AS avg_daily_fp_hours
FROM fact_alerts;

-- Per-rule FP cost breakdown
SELECT
    detection_rule,
    fp_count,
    tp_count,
    precision,
    ROUND(fp_count * getvariable('triage_minutes') / 60.0, 1)
                                        AS estimated_fp_hours,
    ROUND(fp_count * getvariable('triage_minutes') / 60.0 * getvariable('hourly_cost'), 2)
                                        AS estimated_fp_cost,
    fp_volume_share
FROM dim_rule_performance
ORDER BY fp_count DESC;

-- Scenario: what if we reduce alerts from a specific rule by 30%?
-- Replace 'Brute-Force-Login' and 0.30 with target rule and reduction.
SELECT
    detection_rule,
    alert_volume                                            AS current_alerts,
    CAST(alert_volume * 0.30 AS INTEGER)                    AS alerts_removed,
    CAST(fp_count * 0.30 AS INTEGER)                        AS est_fp_removed,
    CAST(tp_count * 0.30 AS INTEGER)                        AS est_tp_affected,
    ROUND(fp_count * 0.30 * getvariable('triage_minutes') / 60.0, 1)
                                                            AS est_hours_saved,
    ROUND(fp_count * 0.30 * getvariable('triage_minutes') / 60.0 * getvariable('hourly_cost'), 2)
                                                            AS est_cost_saved
FROM dim_rule_performance
WHERE detection_rule = 'Brute-Force-Login';
