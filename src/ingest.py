"""Data ingestion - reads raw GUIDE CSV from Kaggle or generates synthetic demo data."""

import random
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import load_config, get_column_map, get_grade_map

# -- GUIDE Ingestion (Kaggle CSV) ---------------------------------------------

def ingest_guide(cfg: dict) -> pa.Table:
    """
    Read Microsoft GUIDE dataset from Kaggle CSV files.

    The GUIDE dataset is available at:
      https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction

    Files: GUIDE_train.csv (~2.4 GB, ~9.4M rows) and optionally GUIDE_test.csv (~1.1 GB).
    The test file does not contain IncidentGrade labels, so only the train file
    is used for triage analysis.
    """
    raw_dir = Path(cfg["paths"]["raw_data_dir"])
    guide_files = cfg["dataset"]["guide_files"]
    train_file = raw_dir / guide_files["train"]

    if not train_file.exists():
        raise FileNotFoundError(
            f"GUIDE train file not found at {train_file}. "
            "Download from https://www.kaggle.com/datasets/Microsoft/"
            "microsoft-security-incident-prediction and place "
            f"{guide_files['train']} in data/raw/."
        )

    col_map = get_column_map(cfg)
    grade_map = get_grade_map(cfg)

    grade_col = col_map["analyst_grade"]
    grade_values = list(grade_map.keys())
    grade_filter = ", ".join(f"'{v}'" for v in grade_values)

    con = duckdb.connect()

    mitre_col = col_map.get("mitre_technique", "MitreTechniques")
    alert_title_col = col_map.get("alert_title", "AlertTitle")
    severity_col = col_map.get("severity", "SuspicionLevel")
    category_col = col_map.get("category", "Category")
    entity_type_col = col_map.get("entity_type", "EntityType")
    entity_id_col = col_map.get("entity_id", "DeviceId")
    detection_rule_col = col_map.get("detection_rule", "DetectorId")
    alert_id_col = col_map["alert_id"]
    timestamp_col = col_map["timestamp"]

    query = f"""
        SELECT
            COALESCE(CAST("{alert_id_col}" AS VARCHAR), 'alert_' || ROW_NUMBER() OVER ())
                AS alert_id,
            CAST("{timestamp_col}" AS VARCHAR) AS timestamp,
            COALESCE(NULLIF(CAST("{detection_rule_col}" AS VARCHAR), ''), 'unknown')
                AS detection_rule,
            COALESCE(NULLIF(CAST("{entity_id_col}" AS VARCHAR), ''), 'unknown')
                AS entity_id,
            COALESCE(NULLIF(CAST("{entity_type_col}" AS VARCHAR), ''), 'unknown')
                AS entity_type,
            CAST("{grade_col}" AS VARCHAR) AS analyst_grade_raw,
            COALESCE(NULLIF(CAST("{mitre_col}" AS VARCHAR), ''), 'unknown')
                AS mitre_technique,
            COALESCE(NULLIF(CAST("{alert_title_col}" AS VARCHAR), ''), 'untitled')
                AS alert_title,
            COALESCE(NULLIF(CAST("{severity_col}" AS VARCHAR), ''), 'unknown')
                AS severity,
            COALESCE(NULLIF(CAST("{category_col}" AS VARCHAR), ''), 'unknown')
                AS category
        FROM read_csv_auto('{train_file.as_posix()}', sample_size=100000)
        WHERE "{grade_col}" IN ({grade_filter})
          AND "{grade_col}" IS NOT NULL
    """

    print(f"  Reading GUIDE dataset from {train_file} ...")
    df = con.execute(query).fetchall()
    columns = [
        "alert_id", "timestamp", "detection_rule", "entity_id",
        "entity_type", "analyst_grade_raw", "mitre_technique",
        "alert_title", "severity", "category",
    ]

    records: list[dict] = []
    for row in df:
        raw_grade = row[5]
        grade = grade_map.get(raw_grade)
        if grade is None:
            continue
        records.append({
            "alert_id": row[0],
            "timestamp": row[1],
            "detection_rule": row[2],
            "entity_id": row[3],
            "entity_type": row[4],
            "analyst_grade": grade,
            "mitre_technique": row[6],
            "alert_title": row[7],
            "severity": row[8],
            "category": row[9],
        })

    con.close()
    print(f"Ingested {len(records):,} valid alert records from GUIDE dataset")
    return _records_to_table(records)


def ingest_guide_fast(cfg: dict) -> Path:
    """
    Fast-path ingestion using DuckDB's CSV reader directly to Parquet.
    Avoids loading all rows into Python memory. Use for the full ~9M row dataset.
    """
    raw_dir = Path(cfg["paths"]["raw_data_dir"])
    guide_files = cfg["dataset"]["guide_files"]
    train_file = raw_dir / guide_files["train"]
    proc_dir = Path(cfg["paths"]["processed_data_dir"])
    proc_dir.mkdir(parents=True, exist_ok=True)
    out_path = proc_dir / "alerts_raw.parquet"

    col_map = get_column_map(cfg)
    grade_map = get_grade_map(cfg)
    grade_col = col_map["analyst_grade"]
    grade_values = list(grade_map.keys())
    grade_filter = ", ".join(f"'{v}'" for v in grade_values)

    mitre_col = col_map.get("mitre_technique", "MitreTechniques")
    alert_title_col = col_map.get("alert_title", "AlertTitle")
    severity_col = col_map.get("severity", "SuspicionLevel")
    category_col = col_map.get("category", "Category")
    entity_type_col = col_map.get("entity_type", "EntityType")
    entity_id_col = col_map.get("entity_id", "DeviceId")
    detection_rule_col = col_map.get("detection_rule", "DetectorId")
    alert_id_col = col_map["alert_id"]
    timestamp_col = col_map["timestamp"]

    grade_case_parts = []
    for raw_val, normalised in grade_map.items():
        grade_case_parts.append(f"WHEN '{raw_val}' THEN '{normalised}'")
    grade_case = " ".join(grade_case_parts)

    con = duckdb.connect()
    print(f"  Reading GUIDE dataset from {train_file} (fast path) ...")

    con.execute(f"""
        COPY (
            SELECT
                COALESCE(CAST("{alert_id_col}" AS VARCHAR), 'unknown') AS alert_id,
                CAST("{timestamp_col}" AS VARCHAR) AS timestamp,
                COALESCE(NULLIF(CAST("{detection_rule_col}" AS VARCHAR), ''), 'unknown')
                    AS detection_rule,
                COALESCE(NULLIF(CAST("{entity_id_col}" AS VARCHAR), ''), 'unknown')
                    AS entity_id,
                COALESCE(NULLIF(CAST("{entity_type_col}" AS VARCHAR), ''), 'unknown')
                    AS entity_type,
                CASE CAST("{grade_col}" AS VARCHAR) {grade_case} ELSE NULL END
                    AS analyst_grade,
                COALESCE(NULLIF(CAST("{mitre_col}" AS VARCHAR), ''), 'unknown')
                    AS mitre_technique,
                COALESCE(NULLIF(CAST("{alert_title_col}" AS VARCHAR), ''), 'untitled')
                    AS alert_title,
                COALESCE(NULLIF(CAST("{severity_col}" AS VARCHAR), ''), 'unknown')
                    AS severity,
                COALESCE(NULLIF(CAST("{category_col}" AS VARCHAR), ''), 'unknown')
                    AS category
            FROM read_csv_auto('{train_file.as_posix()}', sample_size=100000)
            WHERE "{grade_col}" IN ({grade_filter})
              AND "{grade_col}" IS NOT NULL
        ) TO '{out_path.as_posix()}' (FORMAT PARQUET, COMPRESSION SNAPPY)
    """)

    row_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_path.as_posix()}')"
    ).fetchone()[0]

    con.close()
    print(f"Ingested {row_count:,} rows from GUIDE dataset -> {out_path}")
    return out_path


# -- Synthetic Data ------------------------------------------------------------

SYNTHETIC_RULES = [
    "Brute-Force-Login", "Impossible-Travel", "Malware-Detected",
    "Suspicious-PowerShell", "Phishing-Email-Clicked", "Anomalous-Token-Use",
    "Port-Scan-Detected", "Data-Exfiltration-Attempt", "Privilege-Escalation",
    "Suspicious-DNS-Query", "Lateral-Movement-Detected", "Credential-Dumping",
    "Ransomware-Behavior", "Suspicious-File-Download", "MFA-Bypass-Attempt",
    "Unusual-Cloud-API-Call", "Tor-Exit-Node-Connection", "Scheduled-Task-Created",
    "Registry-Modification", "Service-Installation",
]

SYNTHETIC_ENTITY_TYPES = ["Device", "User", "IP", "Mailbox", "CloudApp"]

SYNTHETIC_MITRE = [
    "T1110", "T1078", "T1566", "T1059.001", "T1486",
    "T1053", "T1021", "T1003", "T1071", "T1048",
    "T1055", "T1547", "T1036", "T1105", "T1027",
]

SYNTHETIC_SEVERITIES = ["Low", "Medium", "High", "Informational"]


def generate_synthetic(cfg: dict) -> pa.Table:
    """Generate a clearly labelled synthetic demo dataset."""
    ds_cfg = cfg["dataset"]
    n = ds_cfg.get("synthetic_rows", 100_000)
    seed = ds_cfg.get("synthetic_seed", 42)
    rng = random.Random(seed)

    rule_weights = _zipf_weights(len(SYNTHETIC_RULES), rng)
    rule_fp_rates = {r: rng.uniform(0.05, 0.85) for r in SYNTHETIC_RULES}
    rule_bp_rates = {r: rng.uniform(0.05, 0.30) for r in SYNTHETIC_RULES}

    base_ts = datetime(2023, 1, 1)
    span_days = 365

    records: list[dict] = []
    for i in range(n):
        rule = rng.choices(SYNTHETIC_RULES, weights=rule_weights, k=1)[0]

        roll = rng.random()
        fp_rate = rule_fp_rates[rule]
        bp_rate = rule_bp_rates[rule]
        if roll < fp_rate:
            grade = "FP"
        elif roll < fp_rate + bp_rate:
            grade = "BP"
        else:
            grade = "TP"

        ts = base_ts + timedelta(
            days=rng.randint(0, span_days - 1),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )

        records.append({
            "alert_id": f"SYNTH-{i:08d}",
            "timestamp": ts.isoformat(),
            "detection_rule": rule,
            "entity_id": f"entity-{rng.randint(1, 500)}",
            "entity_type": rng.choice(SYNTHETIC_ENTITY_TYPES),
            "analyst_grade": grade,
            "mitre_technique": rng.choice(SYNTHETIC_MITRE),
            "alert_title": f"[SYNTHETIC] {rule} alert",
            "severity": rng.choice(SYNTHETIC_SEVERITIES),
            "category": rule.split("-")[0],
        })

    print(f"Generated {n:,} synthetic alert records (seed={seed})")
    return _records_to_table(records)


def _zipf_weights(n: int, rng: random.Random) -> list[float]:
    """Approximate Zipf-like distribution to simulate realistic skew."""
    base = [1.0 / (i + 1) ** 0.8 for i in range(n)]
    rng.shuffle(base)
    return base


# -- Shared --------------------------------------------------------------------

def _records_to_table(records: list[dict]) -> pa.Table:
    schema = pa.schema([
        ("alert_id", pa.string()),
        ("timestamp", pa.string()),
        ("detection_rule", pa.string()),
        ("entity_id", pa.string()),
        ("entity_type", pa.string()),
        ("analyst_grade", pa.string()),
        ("mitre_technique", pa.string()),
        ("alert_title", pa.string()),
        ("severity", pa.string()),
        ("category", pa.string()),
    ])
    return pa.Table.from_pylist(records, schema=schema)


def save_parquet(table: pa.Table, cfg: dict, filename: str = "alerts_raw.parquet") -> Path:
    out_dir = Path(cfg["paths"]["processed_data_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    pq.write_table(table, out_path, compression="snappy")
    print(f"Saved {table.num_rows:,} rows to {out_path}")
    return out_path


def run_ingestion(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    source = cfg["dataset"]["source"]

    if source == "guide":
        raw_dir = Path(cfg["paths"]["raw_data_dir"])
        train_file = raw_dir / cfg["dataset"]["guide_files"]["train"]
        if train_file.exists():
            return ingest_guide_fast(cfg)
        else:
            print(
                f"GUIDE dataset not found at {train_file}. "
                "Falling back to synthetic demo data.\n"
                "Download from: https://www.kaggle.com/datasets/Microsoft/"
                "microsoft-security-incident-prediction"
            )
            table = generate_synthetic(cfg)
    else:
        table = generate_synthetic(cfg)

    return save_parquet(table, cfg)


if __name__ == "__main__":
    run_ingestion()
