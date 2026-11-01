"""DuckDB-based transformations — builds analytical tables from cleaned Parquet."""

from pathlib import Path

import duckdb

from src.config import load_config


def build_database(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    proc_dir = Path(cfg["paths"]["processed_data_dir"])
    clean_path = proc_dir / "alerts_clean.parquet"
    db_path = cfg["paths"]["database"]

    if not clean_path.exists():
        raise FileNotFoundError(f"Cleaned parquet not found at {clean_path}. Run clean first.")

    con = duckdb.connect(db_path)

    # ── Fact table ───────────────────────────────────────────────────────
    con.execute(f"""
        CREATE OR REPLACE TABLE fact_alerts AS
        SELECT * FROM read_parquet('{clean_path.as_posix()}')
    """)

    # ── Detection-rule performance ───────────────────────────────────────
    con.execute("""
        CREATE OR REPLACE TABLE dim_rule_performance AS
        SELECT
            detection_rule,
            COUNT(*)                        AS alert_volume,
            SUM(is_tp)                      AS tp_count,
            SUM(is_bp)                      AS bp_count,
            SUM(is_fp)                      AS fp_count,

            -- Precision = TP / (TP + FP)
            CASE WHEN (SUM(is_tp) + SUM(is_fp)) > 0
                 THEN ROUND(SUM(is_tp)::DOUBLE / (SUM(is_tp) + SUM(is_fp)), 4)
                 ELSE NULL END              AS precision,

            -- FP rate = FP / total
            ROUND(SUM(is_fp)::DOUBLE / COUNT(*), 4)
                                            AS fp_rate,

            -- TP rate = TP / total
            ROUND(SUM(is_tp)::DOUBLE / COUNT(*), 4)
                                            AS tp_rate,

            -- Share of total alert volume
            ROUND(COUNT(*)::DOUBLE / (SELECT COUNT(*) FROM fact_alerts), 6)
                                            AS volume_share,

            -- Share of total FP volume
            CASE WHEN (SELECT SUM(is_fp) FROM fact_alerts) > 0
                 THEN ROUND(SUM(is_fp)::DOUBLE / (SELECT SUM(is_fp) FROM fact_alerts), 6)
                 ELSE 0 END                 AS fp_volume_share,

            -- Share of confirmed incidents (TP share)
            CASE WHEN (SELECT SUM(is_tp) FROM fact_alerts) > 0
                 THEN ROUND(SUM(is_tp)::DOUBLE / (SELECT SUM(is_tp) FROM fact_alerts), 6)
                 ELSE 0 END                 AS tp_volume_share

        FROM fact_alerts
        GROUP BY detection_rule
        ORDER BY fp_count DESC
    """)

    # ── Hourly aggregation ───────────────────────────────────────────────
    con.execute("""
        CREATE OR REPLACE TABLE agg_hourly AS
        SELECT
            alert_hour,
            alert_dow,
            day_type,
            COUNT(*)       AS alert_volume,
            SUM(is_tp)     AS tp_count,
            SUM(is_bp)     AS bp_count,
            SUM(is_fp)     AS fp_count,
            CASE WHEN (SUM(is_tp) + SUM(is_fp)) > 0
                 THEN ROUND(SUM(is_tp)::DOUBLE / (SUM(is_tp) + SUM(is_fp)), 4)
                 ELSE NULL END AS precision,
            ROUND(SUM(is_fp)::DOUBLE / COUNT(*), 4) AS fp_rate
        FROM fact_alerts
        GROUP BY alert_hour, alert_dow, day_type
        ORDER BY alert_dow, alert_hour
    """)

    # ── Entity-type aggregation ──────────────────────────────────────────
    con.execute("""
        CREATE OR REPLACE TABLE agg_entity_type AS
        SELECT
            entity_type,
            COUNT(*)       AS alert_volume,
            SUM(is_tp)     AS tp_count,
            SUM(is_bp)     AS bp_count,
            SUM(is_fp)     AS fp_count,
            CASE WHEN (SUM(is_tp) + SUM(is_fp)) > 0
                 THEN ROUND(SUM(is_tp)::DOUBLE / (SUM(is_tp) + SUM(is_fp)), 4)
                 ELSE NULL END AS precision,
            ROUND(SUM(is_fp)::DOUBLE / COUNT(*), 4) AS fp_rate,
            ROUND(SUM(is_fp)::DOUBLE / NULLIF((SELECT SUM(is_fp) FROM fact_alerts), 0), 6)
                                            AS fp_burden_share
        FROM fact_alerts
        GROUP BY entity_type
        ORDER BY fp_count DESC
    """)

    # ── MITRE technique aggregation ──────────────────────────────────────
    con.execute("""
        CREATE OR REPLACE TABLE agg_mitre AS
        SELECT
            mitre_technique,
            COUNT(*)       AS alert_volume,
            SUM(is_tp)     AS tp_count,
            SUM(is_bp)     AS bp_count,
            SUM(is_fp)     AS fp_count,
            CASE WHEN (SUM(is_tp) + SUM(is_fp)) > 0
                 THEN ROUND(SUM(is_tp)::DOUBLE / (SUM(is_tp) + SUM(is_fp)), 4)
                 ELSE NULL END AS precision,
            ROUND(SUM(is_fp)::DOUBLE / COUNT(*), 4) AS fp_rate,
            ROUND(SUM(is_fp)::DOUBLE / NULLIF((SELECT SUM(is_fp) FROM fact_alerts), 0), 6)
                                            AS fp_burden_share
        FROM fact_alerts
        GROUP BY mitre_technique
        ORDER BY fp_count DESC
    """)

    # ── Daily time series ────────────────────────────────────────────────
    con.execute("""
        CREATE OR REPLACE TABLE agg_daily AS
        SELECT
            CAST(alert_timestamp AS DATE) AS alert_date,
            COUNT(*)       AS alert_volume,
            SUM(is_tp)     AS tp_count,
            SUM(is_bp)     AS bp_count,
            SUM(is_fp)     AS fp_count,
            CASE WHEN (SUM(is_tp) + SUM(is_fp)) > 0
                 THEN ROUND(SUM(is_tp)::DOUBLE / (SUM(is_tp) + SUM(is_fp)), 4)
                 ELSE NULL END AS precision
        FROM fact_alerts
        GROUP BY CAST(alert_timestamp AS DATE)
        ORDER BY alert_date
    """)

    row_count = con.execute("SELECT COUNT(*) FROM fact_alerts").fetchone()[0]
    rule_count = con.execute("SELECT COUNT(*) FROM dim_rule_performance").fetchone()[0]
    con.close()

    print(f"DuckDB database built at {db_path}")
    print(f"  fact_alerts: {row_count:,} rows")
    print(f"  dim_rule_performance: {rule_count:,} rules")
    return db_path


if __name__ == "__main__":
    build_database()
