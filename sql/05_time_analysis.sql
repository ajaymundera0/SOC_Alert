-- =============================================================================
-- Time-of-Day and Day-of-Week Analysis
-- =============================================================================

-- Hourly aggregation
SELECT
    alert_hour,
    SUM(alert_volume) AS total_volume,
    SUM(tp_count)     AS total_tp,
    SUM(fp_count)     AS total_fp,
    SUM(bp_count)     AS total_bp,
    ROUND(SUM(tp_count)::DOUBLE / NULLIF(SUM(tp_count) + SUM(fp_count), 0), 4)
                      AS hourly_precision,
    ROUND(SUM(fp_count)::DOUBLE / SUM(alert_volume), 4)
                      AS hourly_fp_rate
FROM agg_hourly
GROUP BY alert_hour
ORDER BY alert_hour;

-- Day-of-week aggregation
SELECT
    alert_dow,
    CASE alert_dow
        WHEN 0 THEN 'Sunday'   WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'  WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END AS day_name,
    SUM(alert_volume) AS total_volume,
    SUM(tp_count)     AS total_tp,
    SUM(fp_count)     AS total_fp,
    ROUND(SUM(tp_count)::DOUBLE / NULLIF(SUM(tp_count) + SUM(fp_count), 0), 4)
                      AS daily_precision
FROM agg_hourly
GROUP BY alert_dow
ORDER BY alert_dow;

-- Weekday vs weekend comparison
SELECT
    day_type,
    SUM(alert_volume) AS total_volume,
    SUM(tp_count)     AS total_tp,
    SUM(fp_count)     AS total_fp,
    ROUND(SUM(tp_count)::DOUBLE / NULLIF(SUM(tp_count) + SUM(fp_count), 0), 4)
                      AS precision,
    ROUND(SUM(fp_count)::DOUBLE / SUM(alert_volume), 4)
                      AS fp_rate
FROM agg_hourly
GROUP BY day_type;

-- Hour × Day-of-Week heatmap data
SELECT
    alert_dow,
    alert_hour,
    SUM(alert_volume) AS volume,
    SUM(fp_count)     AS fp_count,
    ROUND(SUM(fp_count)::DOUBLE / NULLIF(SUM(alert_volume), 0), 4) AS fp_rate
FROM agg_hourly
GROUP BY alert_dow, alert_hour
ORDER BY alert_dow, alert_hour;
