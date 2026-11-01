"""Cost model - quantifies analyst fatigue from false-positive triage burden."""

from dataclasses import dataclass

import duckdb

from src.config import load_config, get_cost_params


@dataclass
class CostEstimate:
    """All values are MODELLED ESTIMATES based on configurable assumptions."""
    total_fp_alerts: int
    triage_minutes_per_alert: float
    total_fp_triage_minutes: float
    total_fp_triage_hours: float
    analyst_hourly_cost: float
    estimated_labor_cost: float
    observation_days: int
    avg_daily_fp_hours: float
    annualized_fp_hours: float | None
    annualized_labor_cost: float | None
    working_days_per_year: int
    assumptions_note: str


def compute_cost_estimate(db_path: str, cost_params: dict | None = None) -> CostEstimate:
    """
    Compute analyst-fatigue cost estimates.

    IMPORTANT: These are modelled estimates. The dataset does not contain
    actual analyst triage duration or salary information. All values are
    derived from configurable assumptions in config.yaml.
    """
    cfg = load_config()
    if cost_params is None:
        cost_params = get_cost_params(cfg)

    triage_min = cost_params["average_triage_minutes_per_alert"]
    hourly_cost = cost_params["analyst_hourly_cost"]
    working_days = cost_params["working_days_per_year"]

    con = duckdb.connect(db_path, read_only=True)
    row = con.execute("""
        SELECT
            SUM(is_fp) AS total_fp,
            DATEDIFF('day', MIN(alert_timestamp), MAX(alert_timestamp)) + 1 AS obs_days
        FROM fact_alerts
    """).fetchone()
    con.close()

    total_fp = row[0] or 0
    obs_days = row[1] or 1

    total_minutes = total_fp * triage_min
    total_hours = total_minutes / 60.0
    total_cost = total_hours * hourly_cost
    avg_daily = total_hours / obs_days

    can_annualize = obs_days >= 30
    annualized_hours = avg_daily * working_days if can_annualize else None
    annualized_cost = annualized_hours * hourly_cost if annualized_hours else None

    return CostEstimate(
        total_fp_alerts=total_fp,
        triage_minutes_per_alert=triage_min,
        total_fp_triage_minutes=round(total_minutes, 1),
        total_fp_triage_hours=round(total_hours, 1),
        analyst_hourly_cost=hourly_cost,
        estimated_labor_cost=round(total_cost, 2),
        observation_days=obs_days,
        avg_daily_fp_hours=round(avg_daily, 2),
        annualized_fp_hours=round(annualized_hours, 1) if annualized_hours else None,
        annualized_labor_cost=round(annualized_cost, 2) if annualized_cost else None,
        working_days_per_year=working_days,
        assumptions_note=(
            f"MODELLED ESTIMATE. Assumes {triage_min} min/alert triage time, "
            f"${hourly_cost}/hr analyst cost, {working_days} working days/year. "
            f"Based on {obs_days} days of observed data."
        ),
    )


def compute_rule_cost_breakdown(db_path: str, cost_params: dict | None = None) -> list[dict]:
    """Compute per-rule FP triage cost estimates."""
    cfg = load_config()
    if cost_params is None:
        cost_params = get_cost_params(cfg)

    triage_min = cost_params["average_triage_minutes_per_alert"]
    hourly_cost = cost_params["analyst_hourly_cost"]

    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT
            detection_rule,
            fp_count,
            tp_count,
            alert_volume,
            precision,
            fp_rate
        FROM dim_rule_performance
        ORDER BY fp_count DESC
    """).fetchall()
    con.close()

    results = []
    for rule, fp, tp, vol, prec, fpr in rows:
        fp_hours = (fp * triage_min) / 60.0
        fp_cost = fp_hours * hourly_cost
        results.append({
            "detection_rule": rule,
            "fp_count": fp,
            "tp_count": tp,
            "alert_volume": vol,
            "precision": prec,
            "fp_rate": fpr,
            "estimated_fp_hours": round(fp_hours, 1),
            "estimated_fp_cost": round(fp_cost, 2),
        })
    return results


# ── Scenario Simulator ──────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    """Result of simulating an alert-volume reduction for a given rule/group."""
    detection_rule: str
    reduction_pct: int
    current_alerts: int
    alerts_removed: int
    remaining_alerts: int
    estimated_fp_removed: int
    estimated_tp_affected: int
    minutes_saved: float
    hours_saved: float
    cost_saved: float
    tp_impact_note: str


def simulate_reduction(
    db_path: str,
    detection_rule: str | None = None,
    reduction_pcts: list[int] | None = None,
    cost_params: dict | None = None,
) -> list[ScenarioResult]:
    """
    Simulate the effect of reducing alert volume by given percentages.

    This is an ANALYTICAL SIMULATION, not an operational recommendation.
    The simulation assumes that reduced alerts follow the same TP/FP
    distribution as the current population - a simplifying assumption
    that may not hold if reduction is targeted.
    """
    cfg = load_config()
    if cost_params is None:
        cost_params = get_cost_params(cfg)
    if reduction_pcts is None:
        reduction_pcts = cfg["simulator"]["reduction_percentages"]

    triage_min = cost_params["average_triage_minutes_per_alert"]
    hourly_cost = cost_params["analyst_hourly_cost"]

    con = duckdb.connect(db_path, read_only=True)
    if detection_rule:
        row = con.execute("""
            SELECT detection_rule, alert_volume, tp_count, fp_count, bp_count, precision
            FROM dim_rule_performance
            WHERE detection_rule = ?
        """, [detection_rule]).fetchone()
        if row is None:
            con.close()
            raise ValueError(f"Detection rule '{detection_rule}' not found")
        rules = [row]
    else:
        rules = con.execute("""
            SELECT detection_rule, alert_volume, tp_count, fp_count, bp_count, precision
            FROM dim_rule_performance
            ORDER BY fp_count DESC
        """).fetchall()
    con.close()

    results = []
    for rule_row in rules:
        rule_name, vol, tp, fp, bp, prec = rule_row
        for pct in reduction_pcts:
            removed = int(vol * pct / 100)
            remaining = vol - removed
            fp_rate = fp / vol if vol > 0 else 0
            tp_rate = tp / vol if vol > 0 else 0

            est_fp_removed = int(removed * fp_rate)
            est_tp_affected = int(removed * tp_rate)

            mins_saved = est_fp_removed * triage_min
            hrs_saved = mins_saved / 60.0
            cost_saved_val = hrs_saved * hourly_cost

            results.append(ScenarioResult(
                detection_rule=rule_name,
                reduction_pct=pct,
                current_alerts=vol,
                alerts_removed=removed,
                remaining_alerts=remaining,
                estimated_fp_removed=est_fp_removed,
                estimated_tp_affected=est_tp_affected,
                minutes_saved=round(mins_saved, 1),
                hours_saved=round(hrs_saved, 1),
                cost_saved=round(cost_saved_val, 2),
                tp_impact_note=(
                    f"Reducing {rule_name} alerts by {pct}% could save ~{hrs_saved:.1f} "
                    f"analyst hours but may affect ~{est_tp_affected} confirmed incidents. "
                    f"(MODELLED ESTIMATE - assumes uniform reduction across grades.)"
                ),
            ))
    return results


def format_cost_report(estimate: CostEstimate) -> str:
    """Format the cost estimate as a readable report."""
    lines = [
        "=" * 70,
        "ANALYST FATIGUE COST MODEL - MODELLED ESTIMATES",
        "=" * 70,
        "",
        f"  Total FP alerts in dataset:       {estimate.total_fp_alerts:>12,}",
        f"  Assumed triage time per alert:     {estimate.triage_minutes_per_alert:>12.0f} min",
        f"  Estimated total FP triage time:    {estimate.total_fp_triage_hours:>12.1f} hours",
        f"  Analyst hourly cost (assumed):     ${estimate.analyst_hourly_cost:>11.2f}",
        f"  Estimated FP labor cost:           ${estimate.estimated_labor_cost:>11,.2f}",
        "",
        f"  Observation period:                {estimate.observation_days:>12,} days",
        f"  Average daily FP triage:           {estimate.avg_daily_fp_hours:>12.2f} hours/day",
        "",
    ]

    if estimate.annualized_fp_hours is not None:
        lines.extend([
            f"  Projected annual FP triage:        {estimate.annualized_fp_hours:>12,.1f} hours/year",
            f"  Projected annual FP cost:          ${estimate.annualized_labor_cost:>11,.2f}/year",
            f"  (Annualised over {estimate.working_days_per_year} working days/year)",
        ])
    else:
        lines.append("  (Annualisation skipped - observation period < 30 days)")

    lines.extend([
        "",
        "  NOTE: " + estimate.assumptions_note,
        "=" * 70,
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    cfg = load_config()
    db = cfg["paths"]["database"]

    estimate = compute_cost_estimate(db)
    print(format_cost_report(estimate))

    print("\nTop 5 rules by estimated FP analyst hours:")
    breakdown = compute_rule_cost_breakdown(db)
    for r in breakdown[:5]:
        print(f"  {r['detection_rule']}: {r['estimated_fp_hours']:.1f} hrs (${r['estimated_fp_cost']:,.2f})")
