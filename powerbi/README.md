# Power BI Dashboard — SOC Alert Triage Analytics

## Overview

A three-page dashboard for analysing SOC triage efficiency, detection-rule
performance, and analyst fatigue cost.

---

## Data Connection

**Source**: DuckDB database at `data/processed/alerts.duckdb`

Power BI does not have a native DuckDB connector. Use one of:

1. **Parquet files** (recommended): connect to `data/processed/alerts_clean.parquet`
   via the Parquet connector, then import `dim_rule_performance`, `agg_hourly`,
   `agg_entity_type`, `agg_mitre`, and `agg_daily` by exporting them from DuckDB
   as CSV/Parquet using `src/export_powerbi.py` (see below).
2. **ODBC**: install the DuckDB ODBC driver and use a generic ODBC source.
3. **CSV export**: run `src/export_powerbi.py` to export all tables as CSV.

### Export Script

```bash
py -3.13 src/export_powerbi.py
```

This generates files in `powerbi/data/`:
- `fact_alerts.csv`
- `dim_rule_performance.csv`
- `agg_hourly.csv`
- `agg_entity_type.csv`
- `agg_mitre.csv`
- `agg_daily.csv`

---

## Required Tables

| Table | Grain | Key |
|-------|-------|-----|
| fact_alerts | One row per alert | alert_id |
| dim_rule_performance | One row per detection rule | detection_rule |
| agg_hourly | Hour × Day of Week | (alert_hour, alert_dow) |
| agg_entity_type | One row per entity type | entity_type |
| agg_mitre | One row per MITRE technique | mitre_technique |
| agg_daily | One row per date | alert_date |

## Relationships

```
fact_alerts.detection_rule  →  dim_rule_performance.detection_rule  (many-to-one)
fact_alerts.entity_type     →  agg_entity_type.entity_type          (many-to-one)
fact_alerts.mitre_technique →  agg_mitre.mitre_technique            (many-to-one)
```

---

## DAX Measures

```dax
// Core metrics
Total Alerts = COUNTROWS(fact_alerts)

Total TP = SUM(fact_alerts[is_tp])

Total FP = SUM(fact_alerts[is_fp])

Total BP = SUM(fact_alerts[is_bp])

Precision = DIVIDE([Total TP], [Total TP] + [Total FP], BLANK())

FP Rate = DIVIDE([Total FP], [Total Alerts], BLANK())

TP Rate = DIVIDE([Total TP], [Total Alerts], BLANK())

// Cost model (MODELLED ESTIMATES)
Triage Minutes Per Alert = 20

Analyst Hourly Cost = 55

Estimated FP Hours =
    DIVIDE([Total FP] * [Triage Minutes Per Alert], 60, 0)

Estimated FP Cost =
    [Estimated FP Hours] * [Analyst Hourly Cost]

// For scenario simulator — use a What-If parameter
Alert Reduction % = SELECTEDVALUE('Reduction Parameter'[Reduction %], 0)

Estimated Hours Saved =
    [Estimated FP Hours] * [Alert Reduction %] / 100

Estimated Cost Saved =
    [Estimated Hours Saved] * [Analyst Hourly Cost]

Estimated TP Affected =
    [Total TP] * [Alert Reduction %] / 100
```

### What-If Parameters

Create a **What-If Parameter** named `Reduction Parameter`:
- **Name**: Reduction %
- **Data type**: Whole Number
- **Minimum**: 0
- **Maximum**: 50
- **Increment**: 5
- **Default**: 10

This creates a slicer the user drags to simulate alert-volume reductions.

---

## Page 1 — SOC Triage Overview

### Layout

| Position | Visual | Data |
|----------|--------|------|
| Top row | Card: Total Alerts | [Total Alerts] |
| Top row | Card: Precision | [Precision] (format %) |
| Top row | Card: FP Rate | [FP Rate] (format %) |
| Top row | Card: TP Count | [Total TP] |
| Top row | Card: FP Count | [Total FP] |
| Top row | Card: Est. Analyst Hours | [Estimated FP Hours] |
| Middle left | Line chart: Alert Volume Trend | X: agg_daily[alert_date], Y: alert_volume, tp_count, fp_count |
| Middle right | Donut chart: Grade Distribution | Values: [Total TP], [Total BP], [Total FP] |
| Bottom | Bar chart: Top 10 FP-Generating Rules | X: detection_rule, Y: fp_count (Top N filter = 10) |

### Formatting
- Cards: large font (28pt), grey subtitle, bold value
- Colours: TP = #2E86AB, BP = #A3B86C, FP = #E84855
- Background: #F5F5F5

---

## Page 2 — Detection Rule Performance

### Layout

| Position | Visual | Data |
|----------|--------|------|
| Top | Table/Matrix: Rule Scorecard | detection_rule, alert_volume, tp_count, fp_count, precision, fp_rate |
| Middle left | Clustered bar: Precision by Rule | X: detection_rule, Y: precision (sorted ascending, Top N = 15) |
| Middle right | Stacked bar: TP/BP/FP by Rule | X: detection_rule, Y: tp_count, bp_count, fp_count (Top N = 15) |
| Bottom | 100% stacked bar: Pareto | X: detection_rule, Y: cumulative_fp_pct |

### Slicers
- Date range (alert_timestamp)
- Entity type (entity_type)
- MITRE technique (mitre_technique)
- Severity

### Conditional formatting
- Precision column: colour scale green (high) → red (low)
- FP count: data bars

---

## Page 3 — Triage Cost & Scenario Simulator

### Layout

| Position | Visual | Data |
|----------|--------|------|
| Top row | Card: Estimated FP Hours | [Estimated FP Hours] |
| Top row | Card: Estimated Cost | [Estimated FP Cost] (format $) |
| Top row | Card: Hours Saved | [Estimated Hours Saved] |
| Top row | Card: Cost Saved | [Estimated Cost Saved] |
| Left | What-If slicer | Reduction % slider |
| Middle | Clustered bar: Top Rules by FP Hours | X: detection_rule, Y: estimated_fp_hours |
| Right | Multi-line chart: Scenario | X: Reduction %, Y1: Hours Saved, Y2: TP Affected |
| Bottom | Table: Rule-level scenario impact | detection_rule, fp_count, est_hours, est_tp_affected |

### Notes
- All cost visuals must include a text box: "MODELLED ESTIMATES — see Assumptions"
- Include a link/bookmark to the Assumptions documentation

---

## Colour Palette

| Element | Hex | Use |
|---------|-----|-----|
| True Positive | #2E86AB | TP bars, lines |
| Benign Positive | #A3B86C | BP bars |
| False Positive | #E84855 | FP bars, alerts |
| Accent | #F9A03F | Highlights, thresholds |
| Background | #F5F5F5 | Page background |
| Text | #333333 | Titles, labels |
| Grid | #E0E0E0 | Axes, gridlines |

---

## Build Instructions

1. Open Power BI Desktop.
2. Get Data → Text/CSV → select files from `powerbi/data/`.
3. Transform Data → verify column types.
4. Create relationships as documented above.
5. Create DAX measures.
6. Create the What-If parameter.
7. Build each page following the layout tables.
8. Apply conditional formatting.
9. Add text boxes for assumptions notes.
10. Publish to Power BI Service (optional).
