"""Integration test — runs the full pipeline on synthetic data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import pyarrow.parquet as pq
import pytest

from src.config import load_config
from src.ingest import generate_synthetic, save_parquet
from src.clean import clean_alerts
from src.transform import build_database
from src.statistics import compute_overall_metrics, compute_pareto


@pytest.fixture(scope="module")
def pipeline_db(tmp_path_factory):
    """Run a mini pipeline on synthetic data and return the DB path."""
    tmp = tmp_path_factory.mktemp("pipeline_test")
    cfg = load_config()
    cfg["paths"]["processed_data_dir"] = str(tmp)
    cfg["paths"]["database"] = str(tmp / "test.duckdb")
    cfg["paths"]["raw_data_dir"] = str(tmp)
    cfg["dataset"]["source"] = "synthetic"
    cfg["dataset"]["synthetic_rows"] = 5000

    table = generate_synthetic(cfg)
    save_parquet(table, cfg)
    clean_alerts(cfg)
    db_path = build_database(cfg)
    return db_path


def test_fact_table_populated(pipeline_db):
    con = duckdb.connect(pipeline_db, read_only=True)
    count = con.execute("SELECT COUNT(*) FROM fact_alerts").fetchone()[0]
    con.close()
    assert count > 0


def test_all_grades_present(pipeline_db):
    con = duckdb.connect(pipeline_db, read_only=True)
    grades = con.execute(
        "SELECT DISTINCT analyst_grade FROM fact_alerts ORDER BY analyst_grade"
    ).fetchall()
    con.close()
    grade_set = {g[0] for g in grades}
    assert grade_set == {"BP", "FP", "TP"}


def test_rule_performance_populated(pipeline_db):
    con = duckdb.connect(pipeline_db, read_only=True)
    count = con.execute("SELECT COUNT(*) FROM dim_rule_performance").fetchone()[0]
    con.close()
    assert count > 0


def test_overall_metrics_complete(pipeline_db):
    metrics = compute_overall_metrics(pipeline_db)
    assert metrics["total_alerts"] > 0
    assert metrics["total_tp"] >= 0
    assert metrics["total_fp"] >= 0
    assert metrics["precision"] is not None
    assert 0.0 <= metrics["precision"] <= 1.0


def test_pareto_sums_to_100(pipeline_db):
    pareto = compute_pareto(pipeline_db)
    assert len(pareto) > 0
    assert abs(pareto[-1]["cum_fp_pct"] - 100.0) < 0.1


def test_timestamps_valid(pipeline_db):
    con = duckdb.connect(pipeline_db, read_only=True)
    nulls = con.execute(
        "SELECT COUNT(*) FROM fact_alerts WHERE alert_timestamp IS NULL"
    ).fetchone()[0]
    con.close()
    assert nulls == 0


def test_binary_flags_consistent(pipeline_db):
    con = duckdb.connect(pipeline_db, read_only=True)
    bad = con.execute("""
        SELECT COUNT(*) FROM fact_alerts
        WHERE (is_tp + is_bp + is_fp) != 1
    """).fetchone()[0]
    con.close()
    assert bad == 0
