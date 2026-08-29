import numpy as np
import pandas as pd
import pytest

from analysis.matrix_association import (
    DegenerateMatrixError,
    find_largest_complete_subset,
    mantel_test,
)

LABELS = ["A", "B", "C", "D", "E"]


def _symmetric_from_upper(labels, values):
    """values: dict[(i,j)] -> distance, for i<j in labels order."""
    n = len(labels)
    m = pd.DataFrame(np.zeros((n, n)), index=labels, columns=labels)
    for i in range(n):
        for j in range(i + 1, n):
            v = values[(labels[i], labels[j])]
            m.loc[labels[i], labels[j]] = v
            m.loc[labels[j], labels[i]] = v
    return m


@pytest.fixture
def base_distances():
    # Arbitrary but fixed pairwise distances with no ties, so rank correlation is well-defined.
    pairs = [(a, b) for i, a in enumerate(LABELS) for b in LABELS[i + 1:]]
    values = {p: v for p, v in zip(pairs, [1.0, 5.0, 2.0, 8.0, 3.0, 9.0, 4.0, 7.0, 6.0, 10.0])}
    return _symmetric_from_upper(LABELS, values)


class TestMantelTestIdenticalMatrices:
    def test_perfect_positive_correlation_when_matrices_identical(self, base_distances):
        result = mantel_test(base_distances, base_distances, n_permutations=999, seed=1)
        assert result.statistic == pytest.approx(1.0)
        assert result.n_objects == 5

    def test_p_value_is_small_for_perfect_correlation(self, base_distances):
        result = mantel_test(base_distances, base_distances, n_permutations=999, seed=1)
        # Not every permutation can beat a perfect correlation, so this should land in the
        # smallest achievable bucket for this many permutations.
        assert result.p_value_one_sided <= 0.05

    def test_bootstrap_ci_contains_observed_statistic_for_perfect_correlation(self, base_distances):
        result = mantel_test(base_distances, base_distances, n_permutations=999, seed=1, n_bootstrap=499)
        assert result.bootstrap_ci_low <= result.statistic + 1e-9
        assert result.statistic - 1e-9 <= result.bootstrap_ci_high


class TestMantelTestInvertedMatrix:
    def test_perfect_negative_correlation_gives_large_one_sided_p_value(self, base_distances):
        # dist_b's ranks are the exact reverse of dist_a's -> Spearman rho = -1.
        inverted = base_distances.max().max() - base_distances
        for label in LABELS:
            inverted.loc[label, label] = 0.0
        result = mantel_test(base_distances, inverted, n_permutations=999, seed=1)
        assert result.statistic == pytest.approx(-1.0)
        # A one-sided (H1: positive association) test should NOT find this significant.
        assert result.p_value_one_sided > 0.5
        # But the two-sided test should flag the (negative) extremity.
        assert result.p_value_two_sided <= 0.05


class TestMantelTestDegenerateInput:
    def test_too_few_common_objects_raises(self, base_distances):
        small = base_distances.loc[["A", "B", "C"], ["A", "B", "C"]]
        with pytest.raises(DegenerateMatrixError):
            mantel_test(small, small, min_objects=4)

    def test_nan_in_matrix_raises(self, base_distances):
        with_nan = base_distances.copy()
        with_nan.loc["A", "B"] = np.nan
        with_nan.loc["B", "A"] = np.nan
        with pytest.raises(DegenerateMatrixError):
            mantel_test(with_nan, base_distances)

    def test_mismatched_labels_uses_only_common_subset(self, base_distances):
        renamed = base_distances.copy()
        subset = renamed.loc[["A", "B", "C", "D"], ["A", "B", "C", "D"]]
        result = mantel_test(subset, base_distances, n_permutations=99, seed=1)
        assert result.n_objects == 4
        assert set(result.labels) == {"A", "B", "C", "D"}


class TestFindLargestCompleteSubset:
    def test_already_complete_matrix_returns_all_labels(self, base_distances):
        result = find_largest_complete_subset(base_distances, min_objects=4)
        assert set(result) == set(LABELS)

    def test_one_object_fully_missing_is_dropped(self, base_distances):
        with_gaps = base_distances.copy()
        with_gaps.loc["E", :] = np.nan
        with_gaps.loc[:, "E"] = np.nan
        with_gaps.loc["E", "E"] = 0.0
        result = find_largest_complete_subset(with_gaps, min_objects=4)
        assert "E" not in result
        assert set(result) == {"A", "B", "C", "D"}

    def test_returns_empty_when_below_minimum_after_dropping(self, base_distances):
        with_gaps = base_distances.copy()
        with_gaps.loc["E", :] = np.nan
        with_gaps.loc[:, "E"] = np.nan
        with_gaps.loc["D", :] = np.nan
        with_gaps.loc[:, "D"] = np.nan
        with_gaps.loc["D", "D"] = 0.0
        with_gaps.loc["E", "E"] = 0.0
        result = find_largest_complete_subset(with_gaps, min_objects=4)
        # Only A, B, C remain fully defined -- below min_objects=4.
        assert result == []

    def test_single_missing_pair_drops_one_object_deterministically(self, base_distances):
        with_gap = base_distances.copy()
        with_gap.loc["A", "E"] = np.nan
        with_gap.loc["E", "A"] = np.nan
        result = find_largest_complete_subset(with_gap, min_objects=4)
        # Dropping either A or E resolves the single missing pair; only one of them remains.
        assert len(result) == 4
        assert not ({"A", "E"} <= set(result))
