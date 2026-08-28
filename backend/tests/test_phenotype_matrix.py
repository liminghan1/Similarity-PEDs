import math

import pandas as pd
import pytest

from analysis.phenotype_matrix import (
    build_safety_phenotype_matrix,
    compute_signal_table,
    load_ae_category_map,
)


class TestComputeSignalTable:
    """Hand-verified a/b/c/d counts for a small synthetic 2-compound, 1-category report set."""

    @pytest.fixture
    def small_report_set(self):
        # R1,R2: compound A with category X. R3: compound A, no X.
        # R4,R5,R6: compound B, no X. R7: compound B with X.
        report_compound = pd.DataFrame(
            {
                "report_id": [1, 2, 3, 4, 5, 6, 7],
                "compound_id": [10, 10, 10, 20, 20, 20, 20],
            }
        )
        report_category = pd.DataFrame({"report_id": [1, 2, 7], "category": ["X", "X", "X"]})
        compound_names = {10: "compoundA", 20: "compoundB"}
        return report_compound, report_category, compound_names

    def test_compound_a_contingency_counts(self, small_report_set):
        report_compound, report_category, compound_names = small_report_set
        table = compute_signal_table(report_compound, report_category, compound_names, ["X"])
        row = table[(table["canonical_name"] == "compoundA") & (table["category"] == "X")].iloc[0]
        assert (row["a"], row["b"], row["c"], row["d"]) == (2, 1, 1, 3)
        assert row["ror"] == pytest.approx(6.0)
        assert row["log_ror"] == pytest.approx(math.log(6.0))

    def test_compound_b_contingency_counts_are_reciprocal(self, small_report_set):
        report_compound, report_category, compound_names = small_report_set
        table = compute_signal_table(report_compound, report_category, compound_names, ["X"])
        row = table[(table["canonical_name"] == "compoundB") & (table["category"] == "X")].iloc[0]
        assert (row["a"], row["b"], row["c"], row["d"]) == (1, 3, 2, 1)
        assert row["ror"] == pytest.approx(1 / 6)

    def test_total_compound_reports_correct(self, small_report_set):
        report_compound, report_category, compound_names = small_report_set
        table = compute_signal_table(report_compound, report_category, compound_names, ["X"])
        a_row = table[table["canonical_name"] == "compoundA"].iloc[0]
        b_row = table[table["canonical_name"] == "compoundB"].iloc[0]
        assert a_row["total_compound_reports"] == 3
        assert b_row["total_compound_reports"] == 4

    def test_small_counts_flagged_sparse_and_below_minimum(self, small_report_set):
        report_compound, report_category, compound_names = small_report_set
        table = compute_signal_table(report_compound, report_category, compound_names, ["X"])
        # a=2 < MIN_CELL_REPORTS(3) for compound A; both compounds have far fewer than
        # MIN_COMPOUND_REPORTS(20) total reports in this tiny synthetic example.
        a_row = table[table["canonical_name"] == "compoundA"].iloc[0]
        assert a_row["sparse_cell"] is True or bool(a_row["sparse_cell"]) is True
        assert bool(a_row["compound_meets_minimum"]) is False

    def test_category_with_zero_reports_handled_without_crash(self):
        report_compound = pd.DataFrame({"report_id": [1, 2], "compound_id": [10, 20]})
        report_category = pd.DataFrame({"report_id": [], "category": []})
        table = compute_signal_table(report_compound, report_category, {10: "A", 20: "B"}, ["Y"])
        row = table[table["canonical_name"] == "A"].iloc[0]
        assert row["a"] == 0
        assert math.isfinite(row["ror"])  # continuity correction must have applied, not crashed


class TestBuildSafetyPhenotypeMatrix:
    def test_eligible_cell_keeps_log_ror_value(self):
        signal_table = pd.DataFrame(
            [
                {
                    "canonical_name": "compoundA", "category": "cardiovascular", "log_ror": 1.23,
                    "sparse_cell": False, "compound_meets_minimum": True,
                },
                {
                    "canonical_name": "compoundB", "category": "cardiovascular", "log_ror": -0.5,
                    "sparse_cell": False, "compound_meets_minimum": True,
                },
            ]
        )
        matrix = build_safety_phenotype_matrix(signal_table)
        assert matrix.loc["compoundA", "cardiovascular"] == pytest.approx(1.23)
        assert matrix.loc["compoundB", "cardiovascular"] == pytest.approx(-0.5)

    def test_sparse_cell_is_nan(self):
        signal_table = pd.DataFrame(
            [
                {
                    "canonical_name": "compoundA", "category": "hepatic", "log_ror": 2.0,
                    "sparse_cell": True, "compound_meets_minimum": True,
                },
            ]
        )
        matrix = build_safety_phenotype_matrix(signal_table)
        assert pd.isna(matrix.loc["compoundA", "hepatic"])

    def test_compound_below_minimum_reports_is_nan_everywhere(self):
        signal_table = pd.DataFrame(
            [
                {
                    "canonical_name": "compoundA", "category": "hepatic", "log_ror": 2.0,
                    "sparse_cell": False, "compound_meets_minimum": False,
                },
            ]
        )
        matrix = build_safety_phenotype_matrix(signal_table)
        assert pd.isna(matrix.loc["compoundA", "hepatic"])

    def test_every_compound_and_category_present_even_if_all_nan(self):
        signal_table = pd.DataFrame(
            [
                {
                    "canonical_name": "compoundA", "category": "hepatic", "log_ror": 2.0,
                    "sparse_cell": True, "compound_meets_minimum": True,
                },
                {
                    "canonical_name": "compoundB", "category": "renal", "log_ror": 1.0,
                    "sparse_cell": False, "compound_meets_minimum": True,
                },
            ]
        )
        matrix = build_safety_phenotype_matrix(signal_table)
        assert set(matrix.index) == {"compoundA", "compoundB"}
        assert set(matrix.columns) == {"hepatic", "renal"}


class TestLoadAeCategoryMap:
    def test_loads_real_csv_and_supports_multi_category_terms(self):
        category_map = load_ae_category_map()
        assert "myocardial infarction" in category_map
        assert "cardiovascular" in category_map["myocardial infarction"]
        # polycythaemia is documented in research/ae_categories.csv as intentionally
        # mapping to both thrombotic and hematologic.
        assert category_map["polycythaemia"] == {"thrombotic", "hematologic"}

    def test_case_normalization_expected_by_caller(self):
        # The map itself is keyed lowercase; matching real ALL-CAPS FAERS terms requires the
        # caller to lowercase first (see _load_report_category_membership).
        category_map = load_ae_category_map()
        assert "JAUNDICE".lower() in category_map
