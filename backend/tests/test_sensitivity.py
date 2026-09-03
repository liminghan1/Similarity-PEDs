import numpy as np
import pandas as pd
import pytest

from analysis.sensitivity import (
    _spearman_distance_matrix,
    build_alternate_descriptor_distance_matrix,
    filter_report_compound,
    run_h2_test,
)


class TestSpearmanDistanceMatrix:
    def test_perfectly_monotonic_rows_give_zero_distance(self):
        wide = pd.DataFrame(
            {"c1": [1.0, 10.0], "c2": [2.0, 20.0], "c3": [3.0, 5.0], "c4": [4.0, 40.0]},
            index=["A", "B"],
        )
        # B is a monotonic (not linear) transform of A's ranks except c3 -- construct an exactly
        # rank-preserving case instead for a clean zero-distance assertion.
        wide2 = pd.DataFrame(
            {"c1": [1.0, 100.0], "c2": [2.0, 200.0], "c3": [3.0, 300.0], "c4": [4.0, 400.0]},
            index=["A", "B"],
        )
        dist = _spearman_distance_matrix(wide2, min_shared_features=3)
        assert dist.loc["A", "B"] == pytest.approx(0.0, abs=1e-9)

    def test_fewer_than_minimum_shared_features_is_nan(self):
        wide = pd.DataFrame(
            {"c1": [1.0, 2.0], "c2": [np.nan, 3.0], "c3": [np.nan, 4.0]},
            index=["A", "B"],
        )
        dist = _spearman_distance_matrix(wide, min_shared_features=3)
        assert pd.isna(dist.loc["A", "B"])


class TestBuildAlternateDescriptorDistanceMatrix:
    def test_zero_variance_column_dropped_not_nan(self):
        # mw values chosen so no z-score lands exactly on 0 (see the dedicated zero-vector test
        # below for why that specific case matters for cosine distance).
        molecular = pd.DataFrame(
            {"mw": [80.0, 150.0, 310.0], "rotatable_bonds": [0, 0, 0]},
            index=["A", "B", "C"],
        )
        dist = build_alternate_descriptor_distance_matrix(molecular)
        assert not dist.isna().any().any()

    def test_symmetric_zero_diagonal(self):
        molecular = pd.DataFrame({"mw": [80.0, 150.0, 310.0]}, index=["A", "B", "C"])
        dist = build_alternate_descriptor_distance_matrix(molecular)
        assert dist.loc["A", "B"] == pytest.approx(dist.loc["B", "A"])
        assert dist.loc["A", "A"] == 0.0

    def test_zero_norm_vector_gives_nan_not_a_crash(self):
        # Regression/documentation case: with a single surviving numeric column, a compound
        # whose z-score lands exactly on the cohort mean has a zero-magnitude vector, for which
        # cosine distance is mathematically undefined. scipy returns NaN for this rather than
        # raising, and this function must not either -- found via a test fixture using
        # [100, 200, 300] (B's z-score is exactly 0), not by inspection.
        molecular = pd.DataFrame(
            {"mw": [100.0, 200.0, 300.0], "rotatable_bonds": [0, 0, 0]},
            index=["A", "B", "C"],
        )
        dist = build_alternate_descriptor_distance_matrix(molecular)
        assert pd.isna(dist.loc["A", "B"])  # B has a zero-norm vector -- NaN, not a crash
        assert not pd.isna(dist.loc["A", "C"])  # unaffected pair still computes normally


class TestRunH2Test:
    @pytest.fixture
    def five_compound_setup(self):
        # 5 compounds, each with enough reports to clear a low min_compound_reports threshold,
        # and category presence patterns that vary enough for a Mantel test to run without error.
        compound_names = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
        report_rows = []
        category_rows = []
        report_id = 0
        for cid in compound_names:
            for i in range(10):
                report_id += 1
                report_rows.append({"report_id": report_id, "compound_id": cid})
                if (report_id + cid) % 3 == 0:
                    category_rows.append({"report_id": report_id, "category": "cardiovascular"})
                if (report_id + cid) % 4 == 0:
                    category_rows.append({"report_id": report_id, "category": "hepatic"})
        report_compound = pd.DataFrame(report_rows)
        report_category = pd.DataFrame(category_rows)
        return report_compound, report_category, compound_names

    def test_returns_not_computable_when_too_few_compounds_meet_threshold(self, five_compound_setup):
        report_compound, report_category, compound_names = five_compound_setup
        structure_dist = pd.DataFrame(
            np.random.default_rng(0).random((5, 5)), index=list("ABCDE"), columns=list("ABCDE")
        )
        for label in "ABCDE":
            structure_dist.loc[label, label] = 0.0
        result = run_h2_test(
            report_compound, report_category, compound_names, ["cardiovascular", "hepatic"],
            structure_dist, min_compound_reports=1000,  # impossible threshold -> nothing qualifies
        )
        assert result["computable"] is False

    def test_empty_report_compound_is_not_computable(self):
        result = run_h2_test(
            pd.DataFrame(columns=["report_id", "compound_id"]), pd.DataFrame(columns=["report_id", "category"]),
            {}, [], pd.DataFrame(),
        )
        assert result["computable"] is False
        assert "no reports" in result["reason"]


class TestFilterReportCompound:
    """Regression tests for the real bug found running Sensitivity 2 (parent-only) against live
    data: `col == None` matches nothing in pandas, even for genuinely-missing cells, so
    `filter_report_compound(df, formulation_id=None)` must use `.isna()` internally."""

    @pytest.fixture
    def membership(self):
        return pd.DataFrame(
            {
                "report_id": [1, 2, 3, 4],
                "compound_id": [10, 10, 20, 20],
                "formulation_id": [None, 101, None, 201],
                "mapping_method": ["exact_alias", "curated_match", "fuzzy_high_confidence", "exact_alias"],
                "use_classification": ["therapeutic", "misuse", None, "misuse"],
            }
        )

    def test_none_filter_matches_missing_values(self, membership):
        result = filter_report_compound(membership, formulation_id=None)
        assert set(result["report_id"]) == {1, 3}

    def test_none_filter_is_not_vacuously_empty(self, membership):
        # This is exactly the failure mode found live: the buggy `== None` version returned an
        # empty DataFrame here instead of the 2 rows above.
        result = filter_report_compound(membership, formulation_id=None)
        assert not result.empty

    def test_list_filter_uses_isin(self, membership):
        result = filter_report_compound(membership, mapping_method=["exact_alias", "curated_match"])
        assert set(result["report_id"]) == {1, 2, 4}

    def test_scalar_filter_uses_equality(self, membership):
        result = filter_report_compound(membership, use_classification="misuse")
        assert set(result["report_id"]) == {2, 4}

    def test_combining_multiple_filters(self, membership):
        result = filter_report_compound(membership, formulation_id=None, use_classification="therapeutic")
        assert set(result["report_id"]) == {1}

    def test_result_has_only_report_and_compound_columns_deduplicated(self, membership):
        result = filter_report_compound(membership, compound_id=10)
        assert list(result.columns) == ["report_id", "compound_id"]
        assert len(result) == len(result.drop_duplicates())
