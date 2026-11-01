# Data Directory

## Structure

```
data/
├── raw/          <- Place the downloaded dataset files here
└── processed/    <- Generated Parquet files and DuckDB database
```

## Microsoft GUIDE Dataset

This project is designed for the **Microsoft GUIDE** (Guided Understanding
of Incidents through Data and Evidence) dataset, hosted on Kaggle.

### Download

1. Go to **https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction**
2. Click **Download** (requires a free Kaggle account).
3. Extract the ZIP file.
4. Place **`GUIDE_train.csv`** in this `data/raw/` directory.

Alternatively, using the Kaggle CLI:

```bash
pip install kaggle
kaggle datasets download -d Microsoft/microsoft-security-incident-prediction
# Extract and move GUIDE_train.csv into data/raw/
```

### Expected Files

| File | Size | Description |
|------|------|-------------|
| `GUIDE_train.csv` | ~2.4 GB | ~9.4M rows with analyst triage grades (TP/BP/FP) |
| `GUIDE_test.csv` | ~1.1 GB | ~4M rows **without** triage grades (not used for analysis) |

Only `GUIDE_train.csv` is required. The test file lacks the `IncidentGrade`
column, so it cannot be used for triage performance analysis.

### Key Columns Used

| CSV Column | Internal Name | Description |
|------------|---------------|-------------|
| `AlertId` | `alert_id` | Unique alert identifier |
| `IncidentId` | `incident_id` | Parent incident ID |
| `Timestamp` | `timestamp` | Alert creation timestamp |
| `DetectorId` | `detection_rule` | Identifier for the detection rule/detector |
| `IncidentGrade` | `analyst_grade` | Analyst verdict: TruePositive, BenignPositive, FalsePositive |
| `EntityType` | `entity_type` | Type of entity (Device, User, IP, etc.) |
| `MitreTechniques` | `mitre_technique` | MITRE ATT&CK technique label |
| `AlertTitle` | `alert_title` | Human-readable alert name |
| `Category` | `category` | Alert category |
| `DeviceId` | `entity_id` | Device identifier |
| `SuspicionLevel` | `severity` | Suspicion/severity level |

The full column mapping is configurable in `config.yaml`.

## Synthetic Demo Data

If the GUIDE dataset is unavailable, the pipeline automatically generates a
synthetic demo dataset (100,000 rows) for testing. Synthetic data is clearly
labelled and must not be presented as real analytical findings.

## Processed Output

After running the pipeline, `data/processed/` will contain:

| File | Description |
|------|-------------|
| `alerts_raw.parquet` | Ingested raw data in Parquet format |
| `alerts_clean.parquet` | Cleaned, normalised alert fact table |
| `alerts.duckdb` | DuckDB database with all analytical tables |
