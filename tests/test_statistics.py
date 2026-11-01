"""Tests for statistical analysis functions."""

import math
import numpy as np
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.statistics import wilson_confidence_interval, chi_square_test, benjamini_hochberg


class TestWilsonCI:
    def test_perfect_precision(self):
        ci = wilson_confidence_interval(100, 100, 0.95)
        assert ci.proportion == 1.0
        assert ci.upper == 1.0
        assert ci.lower > 0.95

    def test_zero_precision(self):
        ci = wilson_confidence_interval(0, 100, 0.95)
        assert ci.proportion == 0.0
        assert ci.lower == 0.0
        assert ci.upper < 0.05

    def test_mid_proportion(self):
        ci = wilson_confidence_interval(50, 100, 0.95)
        assert 0.39 < ci.lower < 0.50
        assert 0.50 < ci.upper < 0.61
        assert ci.proportion == 0.5

    def test_small_sample(self):
        ci = wilson_confidence_interval(1, 3, 0.95)
        assert 0.0 <= ci.lower
        assert ci.upper <= 1.0
        assert ci.lower < ci.proportion < ci.upper

    def test_empty_sample(self):
        ci = wilson_confidence_interval(0, 0, 0.95)
        assert ci.proportion == 0.0
        assert ci.n == 0

    def test_bounds_within_zero_one(self):
        for s in range(0, 21):
            ci = wilson_confidence_interval(s, 20, 0.95)
            assert 0.0 <= ci.lower <= ci.upper <= 1.0

    def test_wider_interval_with_smaller_sample(self):
        ci_small = wilson_confidence_interval(5, 10, 0.95)
        ci_large = wilson_confidence_interval(50, 100, 0.95)
        width_small = ci_small.upper - ci_small.lower
        width_large = ci_large.upper - ci_large.lower
        assert width_small > width_large


class TestChiSquare:
    def test_independent(self):
        table = np.array([[50, 50], [50, 50]])
        result = chi_square_test(table, "test", "H0", "H1", alpha=0.05)
        assert result.chi2 == 0.0
        assert result.p_value == 1.0
        assert not result.significant

    def test_dependent(self):
        table = np.array([[100, 0], [0, 100]])
        result = chi_square_test(table, "test", "H0", "H1", alpha=0.05)
        assert result.chi2 > 0
        assert result.p_value < 0.05
        assert result.significant
        assert result.cramers_v > 0.9

    def test_effect_size_range(self):
        table = np.array([[60, 40], [40, 60]])
        result = chi_square_test(table, "test", "H0", "H1")
        assert 0.0 <= result.cramers_v <= 1.0


class TestBenjaminiHochberg:
    def test_all_significant(self):
        p_values = [0.001, 0.002, 0.003]
        results = benjamini_hochberg(p_values, alpha=0.05)
        assert all(r["significant_after_correction"] for r in results)

    def test_none_significant(self):
        p_values = [0.5, 0.6, 0.7]
        results = benjamini_hochberg(p_values, alpha=0.05)
        assert not any(r["significant_after_correction"] for r in results)

    def test_mixed(self):
        p_values = [0.001, 0.04, 0.5]
        results = benjamini_hochberg(p_values, alpha=0.05)
        assert results[0]["significant_after_correction"]
        assert not results[2]["significant_after_correction"]

    def test_empty(self):
        assert benjamini_hochberg([], 0.05) == []

    def test_preserves_order(self):
        p_values = [0.03, 0.01, 0.05]
        results = benjamini_hochberg(p_values, alpha=0.05)
        assert len(results) == 3
        assert results[0]["p_value"] == 0.03
        assert results[1]["p_value"] == 0.01
