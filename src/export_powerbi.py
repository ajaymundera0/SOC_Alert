"""Export DuckDB tables to CSV for Power BI consumption."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
from src.config import load_config


def export_tables(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    db_path = cfg["paths"]["database"]

    out_dir = Path(cfg["paths"]["visualizations_dir"]).parent / "powerbi" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(db_path, read_only=True)

    tables = [
        "fact_alerts",
        "dim_rule_performance",
        "agg_hourly",
        "agg_entity_type",
        "agg_mitre",
        "agg_daily",
    ]

    for table in tables:
        out_path = out_dir / f"{table}.csv"
        con.execute(f"COPY {table} TO '{out_path.as_posix()}' (HEADER, DELIMITER ',')")
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  Exported {table}: {rows:,} rows -> {out_path}")

    con.close()
    print(f"\nAll tables exported to {out_dir}")


if __name__ == "__main__":
    export_tables()
