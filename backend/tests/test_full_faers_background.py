"""Tests for analysis/full_faers_background.py's pure (network-free) functions: the reaction-term
reverse mapping and the 2x2-table arithmetic that turns raw openFDA counts into a signal table.
Live network calls (fetch_full_faers_counts) are exercised manually, not in the test suite --
matches the project-wide pattern of testing pure combinatorial logic with fixtures/hand-verified
numbers rather than hitting live external APIs in the test suite.
"""

from __future__ import annotations

import pytest

from analysis.full_faers_background import _terms_by_category, build_signal_table


class TestTermsByCategory:
    def test_reverses_term_to_categories_mapping(self):
        category_map = {"hypertension": {"cardiovascular"}, "acne": {"dermatologic"}}
        result = _terms_by_category(category_map)
        assert result == {"cardiovascular": ["hypertension"], "dermatologic": ["acne"]}

    def test_term_belonging_to_multiple_categories_appears_in_both(self):
        category_map = {"polycythaemia": {"thrombotic", "hematologic"}}
        result = _terms_by_category(category_map)
        assert result["thrombotic"] == ["polycythaemia"]
        assert result["hematologic"] == ["polycythaemia"]


class TestBuildSignalTable:
    def test_2x2_arithmetic_matches_hand_calculation(self):
        # total=1000, N_D(testosterone)=100, N_E(cardiovascular)=200, a=20
        # b = 100-20=80, c=200-20=180, d=1000-100-200+20=720
        counts = {
            "total": 1000,
            "n_d": {"testosterone": 100},
            "n_e": {"cardiovascular": 200},
            "a": {"testosterone": {"cardiovascular": 20}},
        }
        table = build_signal_table(counts)
        row = table.iloc[0]
        assert row["a"] == 20
        assert row["b"] == 80
        assert row["c"] == 180
        assert row["d"] == 720
        assert row["a"] + row["b"] + row["c"] + row["d"] == 1000

    def test_ror_greater_than_one_when_event_overrepresented(self):
        # This compound's event rate (20/100=20%) is far higher than the background's (180/900=20%
        # ... make it clearly higher for an unambiguous OR>1 case).
        counts = {
            "total": 1000,
            "n_d": {"drugA": 100},
            "n_e": {"eventX": 200},
            "a": {"drugA": {"eventX": 50}},
        }
        table = build_signal_table(counts)
        row = table.iloc[0]
        assert row["ror"] > 1
        assert row["log_ror"] > 0

    def test_sparse_and_minimum_flags_set_from_thresholds(self):
        counts = {
            "total": 10_000_000,
            "n_d": {"rareDrug": 5},
            "n_e": {"eventX": 1000},
            "a": {"rareDrug": {"eventX": 1}},
        }
        table = build_signal_table(counts)
        row = table.iloc[0]
        assert row["sparse_cell"]  # a=1 < MIN_CELL_REPORTS=3
        assert not row["compound_meets_minimum"]  # N_D=5 < MIN_COMPOUND_REPORTS=20

    def test_multiple_compounds_and_categories_each_get_a_row(self):
        counts = {
            "total": 1000,
            "n_d": {"drugA": 100, "drugB": 50},
            "n_e": {"eventX": 200, "eventY": 30},
            "a": {
                "drugA": {"eventX": 20, "eventY": 5},
                "drugB": {"eventX": 10, "eventY": 2},
            },
        }
        table = build_signal_table(counts)
        assert len(table) == 4
        assert set(table["canonical_name"]) == {"drugA", "drugB"}
        assert set(table["category"]) == {"eventX", "eventY"}
