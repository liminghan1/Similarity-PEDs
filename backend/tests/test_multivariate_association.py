import numpy as np
import pytest

from analysis.multivariate_association import loocv_r2, permutation_test_r2


class TestLoocvR2:
    def test_perfect_linear_relationship_gives_high_r2(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(20, 1))
        y = 3.0 * X[:, 0]  # noiseless linear relationship
        r2 = loocv_r2(X, y, alpha=0.01)
        assert r2 > 0.9

    def test_unrelated_predictor_gives_low_or_negative_r2(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(20, 1))
        y = rng.normal(size=20)  # independent of X
        r2 = loocv_r2(X, y)
        assert r2 < 0.3


class TestPermutationTestR2:
    def test_strong_signal_gives_small_p_value(self):
        rng = np.random.default_rng(2)
        X = rng.normal(size=(15, 1))
        y = 5.0 * X[:, 0] + rng.normal(scale=0.1, size=15)
        result = permutation_test_r2(X, y, n_permutations=199, seed=2, alpha=0.01)
        assert result["observed_loocv_r2"] > 0.8
        assert result["p_value"] <= 0.05

    def test_pure_noise_gives_large_p_value(self):
        rng = np.random.default_rng(3)
        X = rng.normal(size=(10, 3))
        y = rng.normal(size=10)
        result = permutation_test_r2(X, y, n_permutations=199, seed=3)
        assert result["p_value"] > 0.1

    def test_p_value_is_valid_probability(self):
        rng = np.random.default_rng(4)
        X = rng.normal(size=(10, 2))
        y = rng.normal(size=10)
        result = permutation_test_r2(X, y, n_permutations=99, seed=4)
        assert 0.0 <= result["p_value"] <= 1.0
