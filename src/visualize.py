"""Publication-quality Matplotlib visualisations — no Seaborn."""

from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from src.config import load_config
from src.statistics import compute_rule_precision_ci, compute_pareto

# ── Style ────────────────────────────────────────────────────────────────────

COLORS = {
    "tp": "#2e86ab",
    "bp": "#a3b86c",
    "fp": "#e84855",
    "primary": "#2e86ab",
    "secondary": "#e84855",
    "accent": "#f9a03f",
    "grid": "#e0e0e0",
    "text": "#333333",
    "bg": "#ffffff",
}


def _apply_style(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["grid"])
    ax.spines["bottom"].set_color(COLORS["grid"])
    ax.tick_params(colors=COLORS["text"], labelsize=9)
    ax.yaxis.grid(True, color=COLORS["grid"], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Chart 1: Precision by Rule with Wilson CI ────────────────────────────────

def chart_precision_ci(db_path: str, out_dir: Path, min_vol: int = 30) -> None:
    data = compute_rule_precision_ci(db_path)
    data = [d for d in data if d["n_tp_fp"] >= min_vol]
    data.sort(key=lambda x: x["precision"])

    if not data:
        print("  Skipping precision CI chart — no rules meet minimum volume threshold")
        return

    top_n = min(25, len(data))
    data = data[:top_n]

    rules = [d["detection_rule"][:30] for d in data]
    precisions = [d["precision"] for d in data]
    ci_lower = [d["precision"] - d["ci_lower"] for d in data]
    ci_upper = [d["ci_upper"] - d["precision"] for d in data]

    fig, ax = plt.subplots(figsize=(12, max(6, top_n * 0.35)))
    _apply_style(ax)

    y_pos = np.arange(len(rules))
    bars = ax.barh(y_pos, precisions, height=0.6, color=COLORS["primary"], alpha=0.85)
    ax.errorbar(
        precisions, y_pos, xerr=[ci_lower, ci_upper],
        fmt="none", ecolor=COLORS["text"], elinewidth=1.2, capsize=3,
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(rules, fontsize=8)
    ax.set_xlabel("Precision (TP / [TP + FP])", fontsize=10)
    ax.set_title("Detection Rule Precision with 95% Wilson Confidence Intervals", fontsize=12, pad=12)
    ax.set_xlim(0, 1.05)
    ax.axvline(x=0.5, color=COLORS["accent"], linestyle="--", alpha=0.6, linewidth=1)

    fig.text(
        0.99, 0.01,
        f"Rules with ≥{min_vol} alerts (TP+FP). Wilson score intervals.",
        ha="right", fontsize=7, color="#888888",
    )

    _save(fig, out_dir / "01_precision_by_rule_wilson_ci.png")


# ── Chart 2: Pareto Chart ───────────────────────────────────────────────────

def chart_pareto(db_path: str, out_dir: Path) -> None:
    data = compute_pareto(db_path)
    if not data:
        return

    top_n = min(20, len(data))
    subset = data[:top_n]

    rules = [d["detection_rule"][:25] for d in subset]
    fp_counts = [d["fp_count"] for d in subset]
    cum_pcts = [d["cum_fp_pct"] for d in subset]

    fig, ax1 = plt.subplots(figsize=(14, 6))
    _apply_style(ax1)

    x_pos = np.arange(len(rules))
    ax1.bar(x_pos, fp_counts, color=COLORS["fp"], alpha=0.85, label="FP Count")
    ax1.set_ylabel("False Positive Count", fontsize=10, color=COLORS["fp"])
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(rules, rotation=45, ha="right", fontsize=8)

    ax2 = ax1.twinx()
    ax2.plot(x_pos, cum_pcts, color=COLORS["primary"], marker="o", markersize=4,
             linewidth=2, label="Cumulative FP %")
    ax2.set_ylabel("Cumulative FP %", fontsize=10, color=COLORS["primary"])
    ax2.set_ylim(0, 105)
    ax2.axhline(y=80, color=COLORS["accent"], linestyle="--", alpha=0.6, linewidth=1)
    ax2.spines["top"].set_visible(False)

    ax1.set_title("Pareto Analysis — Detection Rules by False Positive Volume", fontsize=12, pad=12)
    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.92), fontsize=9)

    _save(fig, out_dir / "02_pareto_fp_rules.png")


# ── Chart 3: Heatmap — Alert Volume by Hour × Day of Week ───────────────────

def chart_heatmap(db_path: str, out_dir: Path) -> None:
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT alert_dow, alert_hour, SUM(alert_volume) AS vol
        FROM agg_hourly
        GROUP BY alert_dow, alert_hour
    """).fetchall()
    con.close()

    grid = np.zeros((7, 24))
    for dow, hour, vol in rows:
        if 0 <= dow <= 6 and 0 <= hour <= 23:
            grid[int(dow), int(hour)] = vol

    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    hour_labels = [f"{h:02d}" for h in range(24)]

    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(grid, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    ax.set_yticks(range(7))
    ax.set_yticklabels(day_labels, fontsize=9)
    ax.set_xticks(range(24))
    ax.set_xticklabels(hour_labels, fontsize=8)
    ax.set_xlabel("Hour of Day (UTC)", fontsize=10)
    ax.set_ylabel("Day of Week", fontsize=10)
    ax.set_title("Alert Volume — Hour × Day of Week", fontsize=12, pad=12)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Alert Count", fontsize=9)

    _save(fig, out_dir / "03_alert_volume_heatmap.png")


# ── Chart 4: TP / FP Distribution by Hour ───────────────────────────────────

def chart_tp_fp_by_hour(db_path: str, out_dir: Path) -> None:
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT alert_hour,
               SUM(tp_count) AS tp,
               SUM(fp_count) AS fp,
               SUM(bp_count) AS bp
        FROM agg_hourly
        GROUP BY alert_hour
        ORDER BY alert_hour
    """).fetchall()
    con.close()

    hours = [r[0] for r in rows]
    tp = [r[1] for r in rows]
    fp = [r[2] for r in rows]
    bp = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(12, 5))
    _apply_style(ax)

    width = 0.25
    x = np.arange(len(hours))
    ax.bar(x - width, tp, width, color=COLORS["tp"], alpha=0.85, label="True Positive")
    ax.bar(x, bp, width, color=COLORS["bp"], alpha=0.85, label="Benign Positive")
    ax.bar(x + width, fp, width, color=COLORS["fp"], alpha=0.85, label="False Positive")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=8)
    ax.set_xlabel("Hour of Day", fontsize=10)
    ax.set_ylabel("Alert Count", fontsize=10)
    ax.set_title("TP / BP / FP Distribution by Hour of Day", fontsize=12, pad=12)
    ax.legend(fontsize=9)

    _save(fig, out_dir / "04_tp_fp_by_hour.png")


# ── Chart 5: Precision by Entity Type ───────────────────────────────────────

def chart_precision_entity(db_path: str, out_dir: Path) -> None:
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT entity_type, precision, alert_volume
        FROM agg_entity_type
        WHERE precision IS NOT NULL
        ORDER BY precision
    """).fetchall()
    con.close()

    if not rows:
        return

    entities = [r[0][:20] for r in rows]
    precisions = [r[1] for r in rows]
    volumes = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=(10, max(4, len(entities) * 0.5)))
    _apply_style(ax)

    y_pos = np.arange(len(entities))
    bars = ax.barh(y_pos, precisions, height=0.6, color=COLORS["primary"], alpha=0.85)

    for i, (p, v) in enumerate(zip(precisions, volumes)):
        ax.text(p + 0.01, i, f"n={v:,}", va="center", fontsize=8, color=COLORS["text"])

    ax.set_yticks(y_pos)
    ax.set_yticklabels(entities, fontsize=9)
    ax.set_xlabel("Precision", fontsize=10)
    ax.set_title("Precision by Entity Type", fontsize=12, pad=12)
    ax.set_xlim(0, 1.15)

    _save(fig, out_dir / "05_precision_by_entity.png")


# ── Chart 6: Precision by MITRE Technique ───────────────────────────────────

def chart_precision_mitre(db_path: str, out_dir: Path) -> None:
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT mitre_technique, precision, alert_volume
        FROM agg_mitre
        WHERE precision IS NOT NULL AND mitre_technique != 'unknown'
        ORDER BY precision
    """).fetchall()
    con.close()

    if not rows:
        return

    top_n = min(20, len(rows))
    rows = rows[:top_n]

    techniques = [r[0][:25] for r in rows]
    precisions = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(10, max(4, top_n * 0.4)))
    _apply_style(ax)

    y_pos = np.arange(len(techniques))
    ax.barh(y_pos, precisions, height=0.6, color=COLORS["accent"], alpha=0.85)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(techniques, fontsize=8)
    ax.set_xlabel("Precision", fontsize=10)
    ax.set_title("Precision by MITRE ATT&CK Technique", fontsize=12, pad=12)
    ax.set_xlim(0, 1.05)

    _save(fig, out_dir / "06_precision_by_mitre.png")


# ── Chart 7: Alert Volume Over Time ─────────────────────────────────────────

def chart_volume_timeline(db_path: str, out_dir: Path) -> None:
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT alert_date, alert_volume, tp_count, fp_count
        FROM agg_daily
        ORDER BY alert_date
    """).fetchall()
    con.close()

    if not rows:
        return

    dates = [r[0] for r in rows]
    volumes = [r[1] for r in rows]
    tp_vals = [r[2] for r in rows]
    fp_vals = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(14, 5))
    _apply_style(ax)

    ax.fill_between(dates, volumes, alpha=0.15, color=COLORS["primary"])
    ax.plot(dates, volumes, color=COLORS["primary"], linewidth=1.2, label="Total Alerts")
    ax.plot(dates, tp_vals, color=COLORS["tp"], linewidth=0.8, alpha=0.7, label="TP")
    ax.plot(dates, fp_vals, color=COLORS["fp"], linewidth=0.8, alpha=0.7, label="FP")

    ax.set_xlabel("Date", fontsize=10)
    ax.set_ylabel("Alert Count", fontsize=10)
    ax.set_title("Daily Alert Volume Over Time", fontsize=12, pad=12)
    ax.legend(fontsize=9)

    fig.autofmt_xdate()
    _save(fig, out_dir / "07_alert_volume_timeline.png")


# ── Chart 8: Cost / Analyst-Hours Scenario Curve ────────────────────────────

def chart_scenario_curve(db_path: str, out_dir: Path, cost_params: dict | None = None) -> None:
    from src.cost_model import simulate_reduction

    results = simulate_reduction(db_path, cost_params=cost_params)
    if not results:
        return

    by_rule: dict[str, list] = {}
    for r in results:
        by_rule.setdefault(r.detection_rule, []).append(r)

    total_hours = sum(r.hours_saved for r in results if r.reduction_pct == 50)
    top_rules = sorted(by_rule.keys(), key=lambda k: by_rule[k][-1].hours_saved, reverse=True)[:5]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    for ax in (ax1, ax2):
        _apply_style(ax)

    for i, rule in enumerate(top_rules):
        scenarios = by_rule[rule]
        pcts = [s.reduction_pct for s in scenarios]
        hours = [s.hours_saved for s in scenarios]
        tp_impact = [s.estimated_tp_affected for s in scenarios]

        color = plt.cm.tab10(i / 10)
        ax1.plot(pcts, hours, marker="o", markersize=4, linewidth=1.8,
                 color=color, label=rule[:25])
        ax2.plot(pcts, tp_impact, marker="s", markersize=4, linewidth=1.8,
                 color=color, label=rule[:25])

    ax1.set_xlabel("Alert Volume Reduction (%)", fontsize=10)
    ax1.set_ylabel("Estimated Analyst Hours Saved", fontsize=10)
    ax1.set_title("Potential Hours Saved by Alert Reduction", fontsize=11, pad=10)
    ax1.legend(fontsize=7, loc="upper left")

    ax2.set_xlabel("Alert Volume Reduction (%)", fontsize=10)
    ax2.set_ylabel("Estimated TP Alerts Affected", fontsize=10)
    ax2.set_title("Estimated True Positive Impact", fontsize=11, pad=10)
    ax2.legend(fontsize=7, loc="upper left")

    fig.suptitle(
        "Triage Scenario Simulator — Top 5 Rules by FP Burden (MODELLED ESTIMATES)",
        fontsize=12, y=1.02,
    )
    fig.tight_layout()
    _save(fig, out_dir / "08_scenario_curve.png")


# ── Run All ──────────────────────────────────────────────────────────────────

def generate_all_charts(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    db_path = cfg["paths"]["database"]
    out_dir = Path(cfg["paths"]["visualizations_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    min_vol = cfg["analysis"]["min_volume_threshold"]

    print("Generating visualisations...")
    chart_precision_ci(db_path, out_dir, min_vol=min_vol)
    chart_pareto(db_path, out_dir)
    chart_heatmap(db_path, out_dir)
    chart_tp_fp_by_hour(db_path, out_dir)
    chart_precision_entity(db_path, out_dir)
    chart_precision_mitre(db_path, out_dir)
    chart_volume_timeline(db_path, out_dir)
    chart_scenario_curve(db_path, out_dir, cost_params=cfg.get("cost_model"))
    print("All charts generated.")


if __name__ == "__main__":
    generate_all_charts()
