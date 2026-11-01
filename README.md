# Security Alert Triage: Quantifying Analyst Fatigue & False Positive Cost

A data analytics project that examines SOC (Security Operations Centre) alert
triage efficiency by quantifying false-positive burden, detection-rule
performance, analyst workload, and the cost-benefit tradeoff of alert-volume
reduction.

**This is a data analytics / business intelligence project** — not an ML
classifier or a threat-detection engineering tool. It uses SQL, DuckDB,
statistical testing, cost modelling, and Power BI to turn raw triage data
into actionable operational insight.

---

## Business Problem

Security Operations Centres process thousands of alerts daily. A significant
proportion are false positives — alerts that, after analyst investigation,
turn out to be benign. Each false positive consumes analyst time, contributes
to alert fatigue, and diverts attention from genuine threats.

**The core question**: How much analyst capacity is consumed by false positives,
which detection rules are the noisiest, and what is the tradeoff between
reducing alert volume and preserving coverage of real incidents?

### Why This Matters

- Alert fatigue is a leading cause of analyst burnout and missed threats.
- Reducing false-positive volume by even 20% can recover hundreds of analyst
  hours annually.
- Not all noisy rules are equal — some contribute to both FP burden AND
  confirmed-incident detection. Suppressing them without analysis risks
  creating security gaps.

---

## Dataset

**Primary**: [Microsoft GUIDE](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction)
(Guided Understanding of Incidents through Data and Evidence) — a public
dataset of ~9.4 million real-world security alert triage records with
analyst-assigned verdicts (TruePositive, BenignPositive, FalsePositive),
detection-rule identifiers, entity information, MITRE ATT&CK technique
labels, and timestamps. Hosted on Kaggle.

**Fallback**: If GUIDE is unavailable, the pipeline generates a synthetic
demo dataset for testing. Synthetic results are clearly labelled and must
not be presented as real findings.

### Setup

1. Download `GUIDE_train.csv` from [Kaggle](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction) (free account required).
2. Place `GUIDE_train.csv` in `data/raw/`.
3. Run the pipeline (see below).

---

## Architecture

```
security-alert-triage-analytics/
│
├── config.yaml              ← All tuneable parameters
├── requirements.txt
│
├── data/
│   ├── raw/                 ← Place GUIDE dataset here
│   └── processed/           ← Generated Parquet + DuckDB
│
├── sql/                     ← Documented SQL transformations
│   ├── 01_schema.sql
│   ├── 02_cleaning.sql
│   ├── 03_alert_metrics.sql
│   ├── 04_rule_performance.sql
│   ├── 05_time_analysis.sql
│   └── 06_cost_model.sql
│
├── src/                     ← Python pipeline
│   ├── config.py            ← Configuration loader
│   ├── ingest.py            ← Data ingestion (GUIDE / synthetic)
│   ├── clean.py             ← DuckDB-based cleaning
│   ├── transform.py         ← Analytical table construction
│   ├── statistics.py        ← Wilson CI, chi-square, BH correction
│   ├── cost_model.py        ← Analyst fatigue cost model
│   ├── visualize.py         ← Matplotlib chart generation
│   ├── export_powerbi.py    ← Export tables for Power BI
│   └── pipeline.py          ← End-to-end orchestrator
│
├── notebooks/               ← Exploratory analysis
│   ├── 01_data_exploration.ipynb
│   ├── 02_rule_performance.ipynb
│   ├── 03_statistical_testing.ipynb
│   └── 04_cost_model.ipynb
│
├── visualizations/          ← Generated charts
├── powerbi/                 ← Power BI implementation guide
├── tests/                   ← Unit and integration tests
└── docs/                    ← Methodology, assumptions, findings
```

---

## Data Pipeline

```
GUIDE JSONL  →  Ingest  →  Clean  →  DuckDB  →  Analysis  →  Charts
                  ↓                    ↓            ↓
              Parquet             Fact table    Statistical
              (raw)              + aggregates   tests, cost
                                               model, Pareto
```

The pipeline handles millions of rows efficiently using DuckDB and Parquet —
data is never fully loaded into Python memory.

**Run everything with one command:**

```bash
py -3.13 src/pipeline.py
```

---

## Analytical Methodology

### 1. Overall Triage Performance
Total alerts, TP/BP/FP counts and rates, precision, alert volume trends.

### 2. Detection-Rule Performance
Per-rule scorecard with three ranking perspectives:
- **Ranking A**: Raw FP count (which rules produce the most false positives?)
- **Ranking B**: FP rate (which rules have the worst signal-to-noise ratio?)
- **Ranking C**: Volume-weighted FP burden (which rules combine high volume
  with high noise?)

Key insight: "worst precision" ≠ "largest operational burden."

### 3. Confidence Intervals
Wilson score intervals for precision, preferred over normal approximation
because they are valid for proportions near 0/1 and small sample sizes.

### 4. Pareto Analysis
Identifies whether a small number of rules generate a disproportionate share
of false-positive volume.

### 5. Time-of-Day Analysis
Hour × day-of-week heatmap, TP/FP rates by hour, weekday vs weekend patterns.

### 6. Entity and MITRE ATT&CK Analysis
Performance breakdowns by entity type and MITRE technique.

### 7. Statistical Testing
Chi-square tests of independence with Benjamini-Hochberg FDR correction.
Cramér's V for effect size. Large-sample caveats explicitly addressed.

### 8. Cost Model
Configurable analyst-fatigue model. All estimates clearly labelled as
modelled — the dataset contains no actual triage duration or salary data.

### 9. Scenario Simulator
Simulates the impact of reducing alert volume: hours saved vs true-positive
coverage affected. Analytical tool, not an operational recommendation.

---

## Statistical Methods

| Method | Purpose |
|--------|---------|
| Wilson score interval | Confidence intervals for proportions, valid at boundaries |
| Chi-square test of independence | Association between grade and categorical variables |
| Cramér's V | Effect size for chi-square (distinguishes statistical from practical significance) |
| Benjamini-Hochberg correction | False discovery rate control for multiple testing |
| Pareto analysis | Identifying disproportionate FP contributors |

---

## Cost Model Assumptions

All assumptions are configurable in `config.yaml`. See `docs/assumptions.md`.

| Parameter | Default | Source |
|-----------|---------|--------|
| Triage time per alert | 20 min | Industry mid-range estimate |
| Analyst hourly cost | $55/hr | Fully loaded US mid-level SOC analyst |
| Working days/year | 250 | Standard calendar |

---

## Key Findings

*Based on 9.47M real alert records from the Microsoft GUIDE dataset
(7,813 detection rules, 209-day observation period).*

- **62.05% overall precision** — roughly 1 in 5 alerts (21.5%) was a false
  positive; 43.4% were benign positives.
- **10 of 7,813 rules (0.13%) generated over 52% of all false positives.**
  86 rules (1.1%) accounted for 90% of FP volume. Extreme Pareto
  concentration.
- **Multiple rules with 1,000+ alerts had 100% FP rates** — zero true
  positives across all organisations.
- **Machine** and **RegistryKey** entity types had the lowest precision among
  high-volume categories (25.6% and 3.8% respectively).
- **T1133 (External Remote Services)** produced 145K+ alerts with zero
  confirmed incidents.
- **Weekend precision (70.1%) exceeded weekday (60.1%)** by 10 percentage
  points.
- All 4 chi-square tests significant after BH correction; detection rule
  showed the strongest effect (Cramer's V = 0.70).
- **Modelled cost estimate**: ~677K analyst-hours consumed by FP triage over
  211 days (~$37.3M at assumed $55/hr). See `docs/assumptions.md`.

---

## Dashboard

See `powerbi/README.md` for the complete Power BI implementation guide
including table relationships, DAX measures, and page layouts.

**Page 1** — SOC Triage Overview (KPIs, trends, grade distribution)
**Page 2** — Detection Rule Performance (scorecard, Pareto, filters)
**Page 3** — Triage Cost & Scenario Simulator (cost estimates, what-if slider)

---

## Limitations

1. **No recall metric** — the dataset records triaged alerts, not all actual
   incidents. Computing recall would require a denominator that doesn't exist.
2. **Cost estimates are modelled** — no actual triage duration or salary data.
3. **Observational data** — associations do not imply causation.
4. **Statistical significance ≠ practical significance** — with millions of
   rows, tiny effects become statistically significant.
5. **Synthetic data is for testing only** — do not present synthetic results
   as real findings.

---

## How to Reproduce

### Prerequisites
- Python 3.11+
- pip

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd security-alert-triage-analytics

# Install dependencies
py -3.13 -m pip install -r requirements.txt

# Download GUIDE_train.csv from Kaggle and place in data/raw/
# https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction
# (or run with synthetic data for demo)

# Run the full pipeline
py -3.13 src/pipeline.py

# Run tests
py -3.13 -m pytest tests/ -v

# Export tables for Power BI
py -3.13 src/export_powerbi.py
```

---

## Relationship to AEGIS ONE

This project complements **AEGIS ONE**, which handles alert ingestion and
triage operations. Where AEGIS ONE focuses on the operational pipeline
(ingesting, routing, and triaging alerts), this project analyses the
*output* of that process:

- Are detection rules performing well?
- How much analyst time is consumed by false positives?
- Which rules should be prioritised for tuning?
- What is the cost-benefit of reducing alert volume?

Together, they form a complete picture: AEGIS ONE operationalises triage;
this project measures whether the triage process is efficient.

---

## Future Improvements

- Integrate with real SOAR/ticketing data for actual triage duration.
- Add rule-drift monitoring (precision change over time).
- Build an automated rule-health scorecard with alerting thresholds.
- Extend the cost model with shift-scheduling patterns.
- Add analyst-level performance analysis (with appropriate privacy controls).

---

## Interview Talking Points

### 1. Why did you choose this project?
Alert fatigue is one of the largest operational challenges in security
operations. I wanted to demonstrate that data analytics — not just ML —
can quantify the problem and guide decisions. The project shows SQL fluency,
statistical rigour, cost modelling, and dashboard design.

### 2. Why is false-positive volume more useful than just FP rate?
A rule with 90% FP rate but 10 alerts/day creates 9 false positives daily.
A rule with 40% FP rate and 50,000 alerts/day creates 20,000. The second
rule is the bigger operational problem. Volume-weighted FP burden captures
this distinction.

### 3. Why Wilson confidence intervals?
The normal (Wald) approximation for proportions fails near 0 and 1, can
produce intervals outside [0, 1], and requires np ≥ 5. Wilson intervals
are valid for all sample sizes and all proportions, which matters when
some rules have very high or very low precision.

### 4. Why chi-square tests?
To determine whether analyst grade (TP/BP/FP) is statistically associated
with categorical dimensions like hour of day, entity type, or MITRE
technique — without assuming a specific relationship form.

### 5. Why Benjamini-Hochberg correction?
When running multiple hypothesis tests, the family-wise error rate inflates.
BH controls the false discovery rate, which is more appropriate than
Bonferroni when we expect some true effects and want to maintain power.

### 6. Why DuckDB?
DuckDB is an embedded analytical database that processes millions of rows
without a server, integrates natively with Python and Parquet, and supports
full SQL. It's ideal for analytical workloads that would overwhelm pandas
but don't justify a full data warehouse.

### 7. Why Parquet?
Columnar storage with compression. Analytical queries typically touch a
subset of columns; Parquet reads only the columns needed, making it far
more efficient than CSV for large datasets.

### 8. Why no machine learning?
The business question is "how noisy are our detection rules and what does
it cost?" — that's a descriptive/diagnostic analytics problem, not a
prediction problem. Adding ML would obscure the insight and add complexity
without value.

### 9. How did you quantify analyst fatigue?
By modelling FP alerts × assumed triage time per alert. The assumptions
are configurable and clearly labelled. In a real engagement, I'd validate
the triage-time assumption against SOAR timestamps.

### 10. What assumptions went into the cost model?
20 minutes/alert triage time, $55/hr fully loaded analyst cost, 250
working days/year. All configurable. The key point is transparency:
every assumption is documented, and the model shows sensitivity to
changes in these parameters.

### 11. How would you validate cost assumptions in a real SOC?
Sample alert-created → alert-closed timestamps from the ticketing system.
Compare the median against the 20-minute assumption. Obtain analyst cost
from HR/finance. Confirm shift schedule (8h vs 12h, weekday vs 24/7).

### 12. How would you avoid suppressing a valuable detection rule?
The scenario simulator shows the tradeoff: hours saved vs TP alerts affected.
A rule with high FP burden but also high TP contribution should be tuned
(reduce noise), not suppressed (disable entirely). The Pareto analysis
identifies candidates for review, not for deletion.

### 13. What are the dataset limitations?
No recall denominator (can't measure missed incidents). No actual triage
time. Observational data (association ≠ causation). Statistical significance
≠ practical significance with large samples.

### 14. How does this complement AEGIS ONE?
AEGIS ONE operationalises alert ingestion and triage. This project analyses
the efficiency of that process. Together: one builds the pipeline, the other
measures whether the pipeline is working well.

---

## CV Bullets

- Analysed 9.5M SOC triage records from the Microsoft GUIDE dataset using
  DuckDB and Python, quantifying detection-rule precision, false-positive
  burden, and analyst workload across 7,813 rules and 28 entity categories.
- Applied Wilson confidence intervals, chi-square testing, and
  Benjamini-Hochberg correction to identify statistically significant
  differences in triage outcomes across detection rules, entity types,
  and time periods; found 0.13% of rules generated over 52% of FP volume.
- Modelled 800K+ analyst-hours of annualised FP triage capacity using
  configurable cost assumptions and built a Power BI simulator to evaluate
  alert-volume reductions against potential true-positive impact.

---

## License

MIT
