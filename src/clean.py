"""Data cleaning and normalisation — reads raw Parquet, writes cleaned Parquet."""

from pathlib import Path

import duckdb

from src.config import load_config


def clean_alerts(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    proc_dir = Path(cfg["paths"]["processed_data_dir"])
    raw_path = proc_dir / "alerts_raw.parquet"
    clean_path = proc_dir / "alerts_clean.parquet"

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw parquet not found at {raw_path}. Run ingest first.")

    con = duckdb.connect()

    con.execute(f"""
        COPY (
            SELECT
                alert_id,
                -- Parse and normalise timestamp
                TRY_CAST(timestamp AS TIMESTAMP) AS alert_timestamp,
                COALESCE(NULLIF(detection_rule, ''), 'unknown') AS detection_rule,
                COALESCE(NULLIF(entity_id, ''), 'unknown') AS entity_id,
                COALESCE(NULLIF(entity_type, ''), 'unknown') AS entity_type,
                analyst_grade,
                COALESCE(NULLIF(mitre_technique, ''), 'unknown') AS mitre_technique,
                COALESCE(NULLIF(alert_title, ''), 'untitled') AS alert_title,
                COALESCE(NULLIF(severity, ''), 'unknown') AS severity,
                COALESCE(NULLIF(category, ''), 'unknown') AS category,

                -- Derived time dimensions
                EXTRACT(YEAR FROM TRY_CAST(timestamp AS TIMESTAMP))  AS alert_year,
                EXTRACT(MONTH FROM TRY_CAST(timestamp AS TIMESTAMP)) AS alert_month,
                EXTRACT(DOW FROM TRY_CAST(timestamp AS TIMESTAMP))   AS alert_dow,
                EXTRACT(HOUR FROM TRY_CAST(timestamp AS TIMESTAMP))  AS alert_hour,
                CASE
                    WHEN EXTRACT(DOW FROM TRY_CAST(timestamp AS TIMESTAMP)) IN (0, 6)
                    THEN 'weekend' ELSE 'weekday'
                END AS day_type,

                -- Binary grade flags for fast aggregation
                CASE WHEN analyst_grade = 'TP' THEN 1 ELSE 0 END AS is_tp,
                CASE WHEN analyst_grade = 'BP' THEN 1 ELSE 0 END AS is_bp,
                CASE WHEN analyst_grade = 'FP' THEN 1 ELSE 0 END AS is_fp

            FROM read_parquet('{raw_path.as_posix()}')
            WHERE
                alert_id IS NOT NULL
                AND analyst_grade IN ('TP', 'BP', 'FP')
                AND TRY_CAST(timestamp AS TIMESTAMP) IS NOT NULL
            ORDER BY alert_timestamp
        ) TO '{clean_path.as_posix()}' (FORMAT PARQUET, COMPRESSION SNAPPY)
    """)

    row_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{clean_path.as_posix()}')"
    ).fetchone()[0]

    con.close()
    print(f"Cleaned dataset: {row_count:,} rows -> {clean_path}")
    return clean_path


if __name__ == "__main__":
    clean_alerts()
