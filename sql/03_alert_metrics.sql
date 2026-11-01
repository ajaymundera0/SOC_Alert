-- =============================================================================
-- Overall Triage Performance Metrics
-- =============================================================================

-- Summary statistics
SELECT
    COUNT(*)                                                    AS total_alerts,
    SUM(is_tp)                                                  AS total_tp,
    SUM(is_bp)                                                  AS total_bp,
    SUM(is_fp)                                                  AS total_fp,
    ROUND(SUM(is_tp)::DOUBLE / NULLIF(SUM(is_tp) + SUM(is_fp), 0), 4)
                                                                AS precision,
    ROUND(SUM(is_fp)::DOUBLE / COUNT(*), 4)                     AS fp_rate,
    ROUND(SUM(is_tp)::DOUBLE / COUNT(*), 4)                     AS tp_rate,
    ROUND(SUM(is_bp)::DOUBLE / COUNT(*), 4)                     AS bp_rate,
    MIN(alert_timestamp)                                        AS first_alert,
    MAX(alert_timestamp)                                        AS last_alert,
    DATEDIFF('day', MIN(alert_timestamp), MAX(alert_timestamp)) AS observation_days
FROM fact_alerts;

-- Daily alert volume trend
SELECT
    CAST(alert_timestamp AS DATE) AS alert_date,
    COUNT(*)                      AS alert_volume,
    SUM(is_tp)                    AS tp_count,
    SUM(is_bp)                    AS bp_count,
    SUM(is_fp)                    AS fp_count,
    ROUND(SUM(is_tp)::DOUBLE / NULLIF(SUM(is_tp) + SUM(is_fp), 0), 4)
                                  AS daily_precision
FROM fact_alerts
GROUP BY CAST(alert_timestamp AS DATE)
ORDER BY alert_date;

-- Grade distribution
SELECT
    analyst_grade,
    COUNT(*)                                    AS count,
    ROUND(COUNT(*)::DOUBLE / SUM(COUNT(*)) OVER (), 4) AS share
FROM fact_alerts
GROUP BY analyst_grade
ORDER BY count DESC;
