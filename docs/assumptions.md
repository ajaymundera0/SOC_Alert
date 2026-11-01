# Assumptions

All assumptions are configurable in `config.yaml`.

## Cost Model Assumptions

| Parameter | Default Value | Rationale |
|-----------|---------------|-----------|
| `average_triage_minutes_per_alert` | 20 min | Industry estimates range from 10–30 minutes per alert for initial triage. 20 minutes is a mid-range estimate covering alert review, context gathering, and disposition. |
| `analyst_hourly_cost` | $55/hr | Approximate fully loaded cost (salary + benefits + overhead) for a mid-level SOC analyst in the US market. Adjust for local rates. |
| `working_days_per_year` | 250 | Standard figure (365 − weekends − ~10 holidays). SOCs often operate 24/7 but analyst scheduling varies. |
| `working_hours_per_day` | 8 | Standard shift length. Many SOCs use 12-hour shifts — adjust accordingly. |

## Annualisation

Annual projections are only calculated when the observation period exceeds
30 days. The projection formula:

```
annualised_hours = avg_daily_fp_hours × working_days_per_year
```

This assumes the observed daily rate is representative of the full year.
Seasonal variation, campaigns, or infrastructure changes may invalidate this.

## Scenario Simulator

The simulator assumes **uniform reduction** across all analyst grades.
Reducing alerts by X% removes X% of TP, BP, and FP proportionally.

In reality, well-targeted rule tuning would reduce FP disproportionately
while preserving TP. The simulator therefore **overestimates** TP impact
and **underestimates** capacity recovered.

## Analysis Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `min_volume_threshold` | 30 | Minimum alert count (TP + FP) before a rule is included in precision ranking. Prevents overinterpretation of small samples. |
| `alpha` | 0.05 | Significance level for hypothesis tests. |
| `confidence_level` | 0.95 | Confidence level for Wilson intervals. |

## How to Validate These Assumptions

In a real SOC engagement:

1. **Triage time**: sample actual analyst triage duration from SOAR/ticketing
   timestamps (alert-created → alert-closed). Compare the 20-minute assumption
   against the observed median.
2. **Analyst cost**: obtain from HR/finance. Fully loaded cost = salary ×
   1.3–1.5 for benefits and overhead.
3. **Working calendar**: confirm shift schedule (8h vs 12h, weekday vs 24/7).
4. **Grade accuracy**: audit a random sample of analyst verdicts to assess
   inter-rater reliability.
