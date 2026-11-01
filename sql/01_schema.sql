-- =============================================================================
-- Schema Definition — Security Alert Triage Analytics
-- =============================================================================
-- Primary fact table: one row per triaged security alert.
-- Analyst grade values: TP (True Positive), BP (Benign Positive), FP (False Positive).

CREATE TABLE IF NOT EXISTS fact_alerts (
    alert_id         VARCHAR PRIMARY KEY,
    alert_timestamp  TIMESTAMP NOT NULL,
    detection_rule   VARCHAR NOT NULL,
    entity_id        VARCHAR,
    entity_type      VARCHAR DEFAULT 'unknown',
    analyst_grade    VARCHAR NOT NULL CHECK (analyst_grade IN ('TP', 'BP', 'FP')),
    mitre_technique  VARCHAR DEFAULT 'unknown',
    alert_title      VARCHAR,
    severity         VARCHAR,
    category         VARCHAR,

    -- Derived time dimensions
    alert_year       INTEGER,
    alert_month      INTEGER,
    alert_dow        INTEGER,    -- 0 = Sunday, 6 = Saturday
    alert_hour       INTEGER,
    day_type         VARCHAR,    -- 'weekday' or 'weekend'

    -- Binary grade flags
    is_tp            INTEGER DEFAULT 0,
    is_bp            INTEGER DEFAULT 0,
    is_fp            INTEGER DEFAULT 0
);
