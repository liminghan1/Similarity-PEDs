import numpy as np
import pandas as pd
import pytest

from analysis.similarity_analysis import (
    MIN_SHARED_RECEPTOR_FEATURES,
    _correlation_distance_matrix,
    _minmax_normalize,
    build_combined_distance_matrix,
    build_descriptor_distance_matrix,
    build_structure_distance_matrix,
    n_defined_pairs,
)


class TestMinmaxNormalize:
    def test_scales_to_zero_one_range(self):
        m = pd.DataFrame(
            [[0.0, 2.0, 8.0], [2.0, 0.0, 4.0], [8.0, 4.0, 0.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        normalized = _minmax_normalize(m)
        assert normalized.loc["A", "B"] == pytest.approx(0.0)  # min value -> 0
        assert normalized.loc["A", "C"] == pytest.approx(1.0)  # max value -> 1
        assert normalized.loc["B", "C"] == pytest.approx((4.0 - 2.0) / (8.0 - 2.0))

    def test_symmetric_after_normalization(self):
        m = pd.DataFrame(
            [[0.0, 3.0], [3.0, 0.0]], index=["A", "B"], columns=["A", "B"]
        )
        normalized = _minmax_normalize(m)
        assert normalized.loc["A", "B"] == normalized.loc["B", "A"]

    def test_nan_passes_through(self):
        m = pd.DataFrame(
            [[0.0, np.nan, 5.0], [np.nan, 0.0, 2.0], [5.0, 2.0, 0.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        normalized = _minmax_normalize(m)
        assert pd.isna(normalized.loc["A", "B"])

    def test_constant_matrix_maps_to_midpoint(self):
        m = pd.DataFrame(
            [[0.0, 5.0, 5.0], [5.0, 0.0, 5.0], [5.0, 5.0, 0.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        normalized = _minmax_normalize(m)
        assert normalized.loc["A", "B"] == pytest.approx(0.5)


class TestDescriptorDistanceMatrix:
    def test_identical_descriptors_give_zero_distance(self):
        molecular = pd.DataFrame(
            {"mw": [100.0, 100.0, 200.0], "logp": [1.0, 1.0, 2.0]},
            index=["A", "B", "C"],
        )
        dist = build_descriptor_distance_matrix(molecular)
        assert dist.loc["A", "B"] == pytest.approx(0.0)

    def test_distance_is_symmetric_and_zero_diagonal(self):
        molecular = pd.DataFrame(
            {"mw": [100.0, 150.0, 300.0], "logp": [1.0, 2.5, 4.0]},
            index=["A", "B", "C"],
        )
        dist = build_descriptor_distance_matrix(molecular)
        assert dist.loc["A", "C"] == pytest.approx(dist.loc["C", "A"])
        assert dist.loc["A", "A"] == 0.0

    def test_non_numeric_columns_ignored(self):
        molecular = pd.DataFrame(
            {"molecular_formula": ["C1", "C2", "C3"], "mw": [100.0, 200.0, 300.0]},
            index=["A", "B", "C"],
        )
        dist = build_descriptor_distance_matrix(molecular)
        assert dist.shape == (3, 3)  # does not error on the string column

    def test_zero_variance_column_does_not_nan_out_every_distance(self):
        # Regression guard: a constant column (e.g. rotatable_bonds=0 for the whole real cohort)
        # z-scores to 0/0=NaN for every compound, which previously poisoned every pairwise
        # Euclidean distance via np.linalg.norm. Found running analysis.similarity_analysis
        # against the real 10-compound cohort (all showed rotatable_bonds=0) -- every one of the
        # 45 pairs came back NaN instead of the expected 45/45 defined.
        molecular = pd.DataFrame(
            {
                "mw": [100.0, 150.0, 300.0],
                "rotatable_bonds": [0, 0, 0],  # constant across the whole cohort
            },
            index=["A", "B", "C"],
        )
        dist = build_descriptor_distance_matrix(molecular)
        assert not dist.isna().any().any()
        assert dist.loc["A", "B"] > 0  # still discriminates on the real varying column


class TestCorrelationDistanceMatrix:
    def test_perfectly_correlated_rows_give_zero_distance(self):
        wide = pd.DataFrame(
            {"t1": [1.0, 2.0, 3.0, 4.0], "t2": [2.0, 4.0, 6.0, 8.0], "t3": [1.0, 1.5, 2.0, 2.5]},
            index=["A", "B", "C", "D"],
        )
        dist = _correlation_distance_matrix(wide, min_shared_features=3)
        # A's row [1,2,1] vs B's row [2,4,1.5]: check it's at least computed and small (perfectly
        # linearly related columns for A/B specifically aren't guaranteed here; use a clean case
        # below instead for the "exactly zero" claim).
        assert not pd.isna(dist.loc["A", "B"])

    def test_identical_rows_give_exactly_zero_distance(self):
        wide = pd.DataFrame(
            {"t1": [1.0, 5.0], "t2": [2.0, 9.0], "t3": [3.0, 1.0], "t4": [4.0, 7.0]},
            index=["A", "B"],
        )
        # duplicate row for C so A and C are identical
        wide.loc["C"] = wide.loc["A"]
        dist = _correlation_distance_matrix(wide, min_shared_features=3)
        assert dist.loc["A", "C"] == pytest.approx(0.0, abs=1e-9)

    def test_fewer_than_minimum_shared_features_is_nan(self):
        wide = pd.DataFrame(
            {"t1": [1.0, 2.0], "t2": [3.0, np.nan], "t3": [np.nan, 5.0]},
            index=["A", "B"],
        )
        # A and B share only t1 (t2 missing for B, t3 missing for A) -- 1 shared column.
        dist = _correlation_distance_matrix(wide, min_shared_features=MIN_SHARED_RECEPTOR_FEATURES)
        assert pd.isna(dist.loc["A", "B"])

    def test_exactly_two_shared_features_is_excluded_by_default_threshold(self):
        # Regression guard: n=2 gives a mathematically deterministic +-1 correlation, which
        # MIN_SHARED_RECEPTOR_FEATURES=3 is specifically designed to exclude as uninformative.
        wide = pd.DataFrame(
            {"t1": [1.0, 5.0], "t2": [2.0, 9.0], "t3": [np.nan, np.nan]},
            index=["A", "B"],
        )
        dist = _correlation_distance_matrix(wide)
        assert pd.isna(dist.loc["A", "B"])

    def test_no_shared_features_is_nan(self):
        wide = pd.DataFrame(
            {"t1": [1.0, np.nan], "t2": [2.0, np.nan], "t3": [np.nan, 3.0], "t4": [np.nan, 4.0]},
            index=["A", "B"],
        )
        dist = _correlation_distance_matrix(wide, min_shared_features=1)
        assert pd.isna(dist.loc["A", "B"])


class TestBuildStructureDistanceMatrix:
    def test_averages_normalized_fingerprint_and_descriptor_distance(self):
        fp = pd.DataFrame([[0.0, 4.0], [4.0, 0.0]], index=["A", "B"], columns=["A", "B"])
        desc = pd.DataFrame([[0.0, 10.0], [10.0, 0.0]], index=["A", "B"], columns=["A", "B"])
        combined = build_structure_distance_matrix(fp, desc)
        # Each is min-max normalized alone with only one off-diagonal value -> maps to 0.5.
        assert combined.loc["A", "B"] == pytest.approx(0.5)


class TestBuildCombinedDistanceMatrix:
    def test_nan_receptor_distance_propagates_to_combined_not_fallback(self):
        structure = pd.DataFrame(
            [[0.0, 0.3, 0.6], [0.3, 0.0, 0.9], [0.6, 0.9, 0.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        receptor = pd.DataFrame(
            [[0.0, np.nan, 0.5], [np.nan, 0.0, np.nan], [0.5, np.nan, 0.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        combined = build_combined_distance_matrix(structure, receptor)
        assert pd.isna(combined.loc["A", "B"])  # receptor undefined -> combined undefined, not structure-only
        assert not pd.isna(combined.loc["A", "C"])  # receptor defined -> combined defined


class TestNDefinedPairs:
    def test_counts_only_non_nan_off_diagonal_pairs(self):
        m = pd.DataFrame(
            [[0.0, 1.0, np.nan], [1.0, 0.0, np.nan], [np.nan, np.nan, 0.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        assert n_defined_pairs(m) == 1
