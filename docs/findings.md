# Findings

> These findings are derived from the **Microsoft GUIDE dataset**
> (9.47M alert records, 7,813 detection rules, 209-day observation period).
> All cost figures are MODELLED ESTIMATES based on configurable assumptions.

## Overall Triage Performance

| Metric | Value |
|--------|-------|
| Total alerts | 9,465,497 |
| True Positives (TP) | 3,322,713 (35.1%) |
| Benign Positives (BP) | 4,110,817 (43.4%) |
| False Positives (FP) | 2,031,967 (21.5%) |
| Overall precision | 62.05% |
| FP rate | 21.47% |
| Observation period | 209 days |

Benign Positives are the largest category (43.4%), meaning nearly half of all
triaged alerts were real but non-threatening activity. Over one in five alerts
(21.5%) was a false positive.

Recall is not calculated because the dataset records triaged alerts only, not
all actual incidents that occurred during the observation period.

## Detection Rule Performance

- **7,813 distinct detection rules** identified in the dataset.
- Detection rules are anonymised as numeric IDs in the GUIDE dataset.

### Pareto Analysis

| Threshold | Rules Required | % of Total Rules |
|-----------|---------------|-----------------|
| ~52% of FP volume | 10 rules | 0.13% |
| ~80% of FP volume | 41 rules | 0.52% |
| ~90% of FP volume | 86 rules | 1.10% |

**Key insight**: Just 10 of 7,813 rules (0.13%) generated over half of all
false positives. 86 rules (1.1%) accounted for 90% of FP volume. This extreme
concentration means targeted tuning of a very small subset of rules could
substantially reduce analyst workload.

### Worst Precision vs Largest Burden

Multiple rules with 1,000+ alerts had 100% FP rates (zero true positives).
However, the single highest-volume rule (Rule 0) generated 300,942 FP alerts
with a precision of 76.9%. Despite its reasonable precision, Rule 0 produced
more false positives than any other rule because of its massive volume
(1.33M total alerts).

This illustrates the key distinction: **worst precision != largest operational
burden**. Volume-weighted FP burden is the operationally meaningful metric.

## Confidence Intervals

Wilson 95% confidence intervals were computed for all 7,813 rules. Rules below
the 30-alert minimum volume threshold have extremely wide intervals and are
flagged rather than ranked.

## Temporal Patterns

### Weekday vs Weekend

| Period | Alerts | Precision |
|--------|--------|-----------|
| Weekday | 7,753,006 (81.9%) | 60.12% |
| Weekend | 1,712,491 (18.1%) | 70.13% |

Weekend alerts have significantly higher precision (70.1% vs 60.1%). This
could indicate that weekend alerts are more likely to be genuine (lower
background business-activity noise) or that scheduled scanning generates
more benign/false-positive alerts on weekdays.

### Hour of Day

Chi-square test confirms a statistically significant association between
analyst grade and hour of day, but Cramer's V = 0.056 indicates a
**negligible practical effect**. Time-of-day alone is not a strong predictor
of alert quality.

## Entity Analysis

| Entity Type | Volume | Precision | FP Burden Share |
|-------------|--------|-----------|-----------------|
| IP | 2,181,194 | 68.24% | 23.2% |
| User | 1,886,088 | 68.26% | 18.0% |
| MailMessage | 1,173,154 | 39.65% | 13.0% |
| Machine | 697,646 | 25.56% | 11.6% |
| File | 688,402 | 42.46% | 6.7% |
| Url | 682,578 | 63.10% | 4.8% |
| CloudLogonRequest | 638,565 | 83.80% | 5.0% |
| Mailbox | 479,768 | 59.20% | 4.9% |

**Machine** entities have the lowest precision among high-volume types (25.6%)
and account for 11.6% of FP burden despite being only 7.4% of total volume.

**RegistryKey** and **RegistryValue** entities have extremely low precision
(3.8% and 8.6%) but relatively small volume.

**CloudLogonRequest** has the highest precision (83.8%) among major entity
types.

## MITRE ATT&CK Technique Analysis

| Technique | Volume | Precision | FP Burden |
|-----------|--------|-----------|-----------|
| T1078;T1078.004 (Valid Accounts) | 1,354,179 | 76.61% | 15.2% |
| T1566.002 (Spearphishing Link) | 813,679 | 69.42% | 6.3% |
| T1566 (Phishing) | 656,293 | 45.84% | 8.3% |
| T1133 (External Remote Services) | 145,579 | 0.00% | 6.2% |
| T1566.001 (Spearphishing Attachment) | 136,888 | 83.98% | 0.4% |

**T1133 (External Remote Services)** has zero true positives across 145,579
alerts — every alert was either FP or BP. This is a strong candidate for
rule review.

**T1110 combined variants (Brute Force)** show high precision (96.44% for the
three-technique combination), suggesting brute-force detections are
well-calibrated.

**T1566 (Phishing)** without subtype has 45.8% precision — notably lower than
T1566.001 (Attachment, 84.0%) and T1566.002 (Link, 69.4%). The generic
phishing rule may benefit from refinement.

## Statistical Tests

| Test | Chi-square | df | p-value | Cramer's V | Interpretation |
|------|-----------|-----|---------|------------|----------------|
| Grade x Hour of Day | 59,331 | 46 | < 0.0001 | 0.056 | Significant but negligible effect |
| Grade x Entity Type | 1,790,913 | 52 | < 0.0001 | 0.308 | Significant, medium effect |
| Grade x MITRE Technique | 2,403,285 | 2,038 | < 0.0001 | 0.546 | Significant, large effect |
| Grade x Detection Rule | 9,297,892 | 11,452 | < 0.0001 | 0.701 | Significant, large effect |

All four tests remained significant after Benjamini-Hochberg correction.

**Interpretation**: With 9.4M rows, all tests are statistically significant.
The meaningful findings are in the effect sizes:

- **Detection rule** has the strongest association with analyst grade (V=0.70,
  large) — unsurprising since rules are designed to detect specific patterns.
- **MITRE technique** has a large effect (V=0.55) — certain technique
  categories are inherently noisier than others.
- **Entity type** has a medium effect (V=0.31) — entity type matters but less
  than rule or technique.
- **Hour of day** has a negligible effect (V=0.06) — time of day alone
  explains almost nothing about alert quality.

## Cost Model (MODELLED ESTIMATES)

| Metric | Value |
|--------|-------|
| Total FP alerts | 2,031,967 |
| Estimated FP triage hours | 677,322 hours (over 211 days) |
| Average daily FP triage | 3,210 hours/day |
| Estimated annual FP triage | 802,515 hours/year |
| Estimated annual FP cost | $44,138,304/year |

**Assumptions**: 20 min/alert triage, $55/hr analyst cost, 250 working
days/year. These are MODELLED ESTIMATES based on configurable assumptions.
The dataset spans 6,100+ organisations, so the total represents aggregate
burden across all organisations, not a single SOC.

## Recommendations

1. **Review rules with 100% FP rate and material volume**: Multiple rules
   with 1,000+ alerts produced zero true positives. These should be reviewed
   for possible disablement or significant threshold adjustment.

2. **Prioritise tuning of high-volume, moderate-precision rules**: Rule 0
   alone generated 300K+ false positives. Even a modest precision improvement
   (e.g., 77% to 85%) would eliminate tens of thousands of FP alerts.

3. **Investigate T1133 (External Remote Services) detections**: 145,579
   alerts with zero true positives across all organisations. This rule or
   set of rules appears systematically miscalibrated.

4. **Focus Machine/RegistryKey entity tuning**: Machine entities (25.6%
   precision) and RegistryKey entities (3.8% precision) are
   disproportionately noisy relative to their volume.

5. **Distinguish generic from specific phishing rules**: T1566 (generic)
   has 46% precision while T1566.001 (attachment) achieves 84%. Migrating
   generic phishing detections to more specific rules could improve
   signal-to-noise.

6. **Monitor weekend vs weekday precision differential**: Weekend precision
   (70.1%) is 10 percentage points higher than weekday (60.1%). Investigate
   whether weekday noise comes from scheduled scans or business-hour
   activity patterns.

7. **Establish minimum-volume thresholds** before comparing rule precision
   across rules with vastly different alert volumes.

> All recommendations are analytical observations from the dataset. In a
> production environment, validate against operational context, consult
> detection engineering, and assess potential coverage gaps before acting
> on any rule change.
