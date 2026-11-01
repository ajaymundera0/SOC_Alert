-- =============================================================================
-- Data Cleaning — applied during ingestion via DuckDB
-- =============================================================================
-- This SQL documents the cleaning logic used by src/clean.py.
-- It can also be run standalone against a raw Parquet file.

COPY (
    SELECT
        alert_id,
        TRY_CAST(timestamp AS TIMESTAMP)                    AS alert_timestamp,
        COALESCE(NULLIF(detection_rule, ''), 'unknown')     AS detection_rule,
        COALESCE(NULLIF(entity_id, ''), 'unknown')          AS entity_id,
        COALESCE(NULLIF(entity_type, ''), 'unknown')        AS entity_type,
        analyst_grade,
        COALESCE(NULLIF(mitre_technique, ''), 'unknown')    AS mitre_technique,
        COALESCE(NULLIF(alert_title, ''), 'untitled')       AS alert_title,
        COALESCE(NULLIF(severity, ''), 'unknown')           AS severity,
        COALESCE(NULLIF(category, ''), 'unknown')           AS category,

        EXTRACT(YEAR  FROM TRY_CAST(timestamp AS TIMESTAMP)) AS alert_year,
        EXTRACT(MONTH FROM TRY_CAST(timestamp AS TIMESTAMP)) AS alert_month,
        EXTRACT(DOW   FROM TRY_CAST(timestamp AS TIMESTAMP)) AS alert_dow,
        EXTRACT(HOUR  FROM TRY_CAST(timestamp AS TIMESTAMP)) AS alert_hour,
        CASE WHEN EXTRACT(DOW FROM TRY_CAST(timestamp AS TIMESTAMP)) IN (0, 6)
             THEN 'weekend' ELSE 'weekday' END               AS day_type,

        CASE WHEN analyst_grade = 'TP' THEN 1 ELSE 0 END     AS is_tp,
        CASE WHEN analyst_grade = 'BP' THEN 1 ELSE 0 END     AS is_bp,
        CASE WHEN analyst_grade = 'FP' THEN 1 ELSE 0 END     AS is_fp

    FROM read_parquet('data/processed/alerts_raw.parquet')
    WHERE
        alert_id IS NOT NULL
        AND analyst_grade IN ('TP', 'BP', 'FP')
        AND TRY_CAST(timestamp AS TIMESTAMP) IS NOT NULL
    ORDER BY alert_timestamp
) TO 'data/processed/alerts_clean.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);
