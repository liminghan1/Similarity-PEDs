"""Reproducibility test (Phase 9/15, TODO.md): same data + seed -> same primary result.

Runs the actual H2 matrix-association computation (structure-only distance vs. safety distance,
the one fully computable representation of the pre-specified primary test -- see
`reports/research_report.md`) twice against the real, committed distance-matrix artifacts and
checks the two runs are bit-identical. Also checks the freshly-computed result matches the
persisted `artifacts/matrices/matrix_association_results.json`, so this test breaks loudly if
those artifacts are ever regenerated from different source data without being kept in sync.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from analysis.matrix_association import DEFAULT_SEED, find_largest_complete_subset, mantel_test

ARTIFACTS_DIR = Path("artifacts/matrices")


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(ARTIFACTS_DIR / f"{name}_matrix.csv", index_col=0)


@pytest.fixture(scope="module")
def structure_vs_safety():
    structure = _load("structure_distance")
    safety = _load("safety_distance")
    subset = find_largest_complete_subset(structure, min_objects=4)
    if not subset:
        pytest.skip("structure_distance_matrix.csv has no >=4-object complete subset in this checkout")
    return structure.loc[subset, subset], safety.loc[subset, subset]


class TestSameDataSameSeedGivesSameResult:
    def test_repeated_runs_are_bit_identical(self, structure_vs_safety):
        dist_a, dist_b = structure_vs_safety
        first = mantel_test(dist_a, dist_b, seed=DEFAULT_SEED)
        second = mantel_test(dist_a, dist_b, seed=DEFAULT_SEED)

        assert first.statistic == second.statistic
        assert first.p_value_one_sided == second.p_value_one_sided
        assert first.p_value_two_sided == second.p_value_two_sided
        assert first.bootstrap_ci_low == second.bootstrap_ci_low
        assert first.bootstrap_ci_high == second.bootstrap_ci_high
        assert first.labels == second.labels

    def test_different_seed_can_change_permutation_p_value(self, structure_vs_safety):
        dist_a, dist_b = structure_vs_safety
        default_seed = mantel_test(dist_a, dist_b, seed=DEFAULT_SEED, n_permutations=999, n_bootstrap=199)
        other_seed = mantel_test(dist_a, dist_b, seed=DEFAULT_SEED + 1, n_permutations=999, n_bootstrap=199)

        # The observed statistic depends only on the data, never the seed.
        assert default_seed.statistic == other_seed.statistic
        # The permutation null distribution (and therefore the bootstrap CI) is seed-dependent --
        # confirming the seed is actually wired through, not silently ignored.
        assert default_seed.bootstrap_ci_low != other_seed.bootstrap_ci_low


class TestMatchesPersistedResearchArtifact:
    def test_freshly_computed_result_matches_matrix_association_results_json(self, structure_vs_safety):
        with open(ARTIFACTS_DIR / "matrix_association_results.json") as f:
            persisted = json.load(f)
        h2_structure_only = next(
            r
            for r in persisted["results"]
            if r["label"] == "SECONDARY" and "structure-only" in r["description"]
        )
        if not h2_structure_only["computable"]:
            pytest.skip("H2 structure-only result is not computable in the persisted artifact")

        dist_a, dist_b = structure_vs_safety
        result = mantel_test(dist_a, dist_b, seed=persisted["seed"], n_permutations=persisted["n_permutations"])

        assert result.statistic == pytest.approx(h2_structure_only["statistic_spearman_rho"])
        assert result.p_value_one_sided == pytest.approx(h2_structure_only["p_value_one_sided"])
        assert result.n_objects == h2_structure_only["n_objects"]
