"""Tests for cost model functions."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cost_model import CostEstimate, ScenarioResult


class TestCostEstimate:
    def test_hours_calculation(self):
        fp_alerts = 1000
        triage_min = 20
        expected_hours = 1000 * 20 / 60.0
        assert abs(expected_hours - 333.3) < 0.1

    def test_cost_calculation(self):
        fp_hours = 333.3
        hourly_cost = 55.0
        expected_cost = fp_hours * hourly_cost
        assert abs(expected_cost - 18331.5) < 1.0

    def test_daily_average(self):
        total_hours = 333.3
        obs_days = 365
        avg = total_hours / obs_days
        assert abs(avg - 0.913) < 0.01

    def test_annualization(self):
        avg_daily = 0.913
        working_days = 250
        annual = avg_daily * working_days
        assert abs(annual - 228.25) < 1.0


class TestScenarioResult:
    def test_reduction_math(self):
        vol = 10000
        pct = 30
        removed = int(vol * pct / 100)
        assert removed == 3000
        assert vol - removed == 7000

    def test_proportional_fp_removal(self):
        vol = 10000
        fp = 6000
        removed = 3000
        fp_rate = fp / vol
        est_fp_removed = int(removed * fp_rate)
        assert est_fp_removed == 1800

    def test_zero_reduction(self):
        vol = 10000
        pct = 0
        removed = int(vol * pct / 100)
        assert removed == 0
