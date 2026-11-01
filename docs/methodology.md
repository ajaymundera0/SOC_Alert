# Methodology

## Data Pipeline

1. **Ingestion**: Raw JSONL records are parsed and mapped to a standardised
   schema via configurable column mappings (`config.yaml`).
2. **Cleaning**: Invalid timestamps, null IDs, and unrecognised analyst grades
   are filtered. Missing categorical fields default to `"unknown"`.
3. **Transformation**: Cleaned data is loaded into DuckDB. Analytical
   aggregation tables are built for rules, hourly patterns, entity types,
   MITRE techniques, and daily time series.

## Metric Definitions

| Metric | Formula | Notes |
|--------|---------|-------|
| Precision | TP / (TP + FP) | Excludes Benign Positives from denominator |
| FP Rate | FP / Total Alerts | Proportion of all alerts graded false positive |
| TP Rate | TP / Total Alerts | Proportion of all alerts graded true positive |
| BP Rate | BP / Total Alerts | Proportion graded benign positive |
| Recall | Not calculated | No defensible denominator — the dataset records triaged alerts, not all actual incidents |
| FP Burden | FP count × FP rate | Volume-weighted measure combining frequency and noise rate |

### Why Not Recall?

Recall requires knowing all true incidents (the denominator). This dataset
only records alerts that were generated and triaged. Incidents that were
never detected do not appear. Computing "recall" from this data would
produce a misleadingly precise number.

## Confidence Intervals

**Wilson score intervals** are used instead of normal (Wald) intervals because:

- The normal approximation fails for proportions near 0 or 1.
- It can produce intervals outside [0, 1].
- It requires the sample size assumption np ≥ 5.
- Wilson intervals are valid for all sample sizes and all proportions.

A minimum-volume threshold (configurable, default 30 alerts) is applied before
ranking rules by precision. Rules below this threshold are shown but flagged.

## Hypothesis Testing

Chi-square tests of independence assess whether analyst grade distributions
differ across categories (hour, entity type, MITRE technique, detection rule).

**Benjamini-Hochberg FDR correction** is applied when multiple tests are
performed to control the expected false discovery rate. This is preferred
over Bonferroni because:

- Bonferroni is excessively conservative with many tests.
- BH controls the proportion of false discoveries among rejected hypotheses.
- It has greater statistical power while maintaining appropriate error control.

### Large-Sample Caveat

With datasets containing millions of alerts, chi-square tests will detect
extremely small effects as statistically significant. **Statistical
significance ≠ practical significance.** Cramér's V is reported alongside
p-values to assess effect magnitude.

## Cost Model

The cost model is entirely based on configurable assumptions. The dataset
contains no actual triage duration or salary data.

See `assumptions.md` for all configurable parameters.

## Scenario Simulator

The simulator assumes that alert-volume reductions apply proportionally
across all grades (TP, BP, FP). In practice, targeted tuning would
disproportionately reduce FP while preserving TP — meaning the simulator
provides a **conservative estimate** of TP impact.
