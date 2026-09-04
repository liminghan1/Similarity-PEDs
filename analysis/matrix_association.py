"""Phase 9: the central matrix-association test (project brief Sec. 18, research/analysis_plan.md
Sec. 4) -- a Mantel-style permutation test between two pairwise distance matrices.

Test statistic: Spearman correlation between the upper-triangle entries of two aligned distance
matrices (chosen over Pearson because distances are not assumed linearly related, and because the
small compound count makes rank-based association more robust to outlying pairs -- pre-specified
in research/analysis_plan.md Sec. 4).

Permutation procedure: randomly permute compound labels on one matrix, holding the other fixed;
recompute the statistic; repeat N times (default 9,999, per the pre-specified plan); empirical
p-value = (1 + #{permuted >= observed}) / (1 + N) for the one-sided-positive test H1 predicts,
also reporting the two-sided version.

This module deliberately requires its two input matrices to already be NaN-free for the object
set being tested -- `find_largest_complete_subset` (below) is the separate, explicit policy for
reducing a matrix with missing pairs down to a fully-defined subset before calling `mantel_test`.
Keeping that policy out of `mantel_test` itself keeps the test's own logic simple and matches
research/analysis_plan.md's "pairwise-complete, never impute" rule: the "which objects survive"
decision is made once, explicitly, not implicitly inside the permutation loop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

DEFAULT_N_PERMUTATIONS = 9999
DEFAULT_SEED = 42
DEFAULT_N_BOOTSTRAP = 1999


class DegenerateMatrixError(Exception):
    """Raised when a matrix-association test is requested on too few objects (or too sparse a
    matrix) to be meaningful. Never silently returns a p-value for a degenerate test."""


@dataclass(frozen=True)
class MantelResult:
    statistic: float
    p_value_one_sided: float
    p_value_two_sided: float
    n_permutations: int
    n_objects: int
    labels: tuple[str, ...]
    bootstrap_ci_low: float | None = None
    bootstrap_ci_high: float | None = None


def _upper_triangle(matrix: pd.DataFrame, labels: list[str]) -> np.ndarray:
    return np.array([matrix.loc[a, b] for a, b in combinations(labels, 2)])


def find_largest_complete_subset(matrix: pd.DataFrame, *, min_objects: int = 4) -> list[str]:
    """Greedily drops the object with the most missing pairwise entries until the remaining
    submatrix has no NaNs, or fewer than `min_objects` remain (in which case an empty list is
    returned -- the caller must treat this as "not computable," not silently proceed)."""
    remaining = matrix.index.tolist()
    while remaining:
        sub = matrix.loc[remaining, remaining]
        if not sub.isna().any().any():
            return remaining if len(remaining) >= min_objects else []
        na_counts = sub.isna().sum(axis=1)
        worst = na_counts.sort_values(ascending=False)
        # Deterministic tie-break: drop the alphabetically-last among the worst-tied objects.
        max_na = worst.iloc[0]
        candidates = sorted(worst[worst == max_na].index.tolist())
        remaining = [x for x in remaining if x != candidates[-1]]
    return []


def mantel_test(
    dist_a: pd.DataFrame,
    dist_b: pd.DataFrame,
    *,
    n_permutations: int = DEFAULT_N_PERMUTATIONS,
    seed: int = DEFAULT_SEED,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    min_objects: int = 4,
) -> MantelResult:
    labels = sorted(set(dist_a.index) & set(dist_b.index))
    if len(labels) < min_objects:
        raise DegenerateMatrixError(
            f"Only {len(labels)} objects are common to both matrices (minimum {min_objects}); "
            "cannot run a meaningful permutation test."
        )
    a = dist_a.loc[labels, labels]
    b = dist_b.loc[labels, labels]
    if a.isna().any().any() or b.isna().any().any():
        raise DegenerateMatrixError(
            "Input matrices contain NaN cells for the requested object set -- call "
            "find_largest_complete_subset() first and pass its result's labels, or accept that "
            "this test is not computable for the current object set."
        )

    rng = np.random.default_rng(seed)
    vec_a = _upper_triangle(a, labels)
    vec_b = _upper_triangle(b, labels)
    observed = spearmanr(vec_a, vec_b).statistic

    n = len(labels)
    permuted_stats = np.empty(n_permutations)
    for i in range(n_permutations):
        perm = rng.permutation(n)
        permuted_labels = [labels[j] for j in perm]
        b_perm = b.loc[permuted_labels, permuted_labels]
        vec_b_perm = _upper_triangle(b_perm, permuted_labels)
        permuted_stats[i] = spearmanr(vec_a, vec_b_perm).statistic

    p_one_sided = (1 + np.sum(permuted_stats >= observed)) / (1 + n_permutations)
    p_two_sided = (1 + np.sum(np.abs(permuted_stats) >= abs(observed))) / (1 + n_permutations)

    boot_rng = np.random.default_rng(seed + 1)
    n_pairs = len(vec_a)
    bootstrap_stats = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = boot_rng.integers(0, n_pairs, size=n_pairs)
        bootstrap_stats[i] = spearmanr(vec_a[idx], vec_b[idx]).statistic
    ci_low, ci_high = np.nanpercentile(bootstrap_stats, [2.5, 97.5])

    return MantelResult(
        statistic=float(observed),
        p_value_one_sided=float(p_one_sided),
        p_value_two_sided=float(p_two_sided),
        n_permutations=n_permutations,
        n_objects=n,
        labels=tuple(labels),
        bootstrap_ci_low=float(ci_low),
        bootstrap_ci_high=float(ci_high),
    )


# --------------------------------------------------------------------------------------
# Orchestration: run every pre-specified matrix-association test against the real distance
# matrices built by analysis/similarity_analysis.py, labeled PRIMARY/SECONDARY/EXPLORATORY
# per research/hypotheses.md's hypothesis-to-analysis mapping (project brief Sec. 40).
# --------------------------------------------------------------------------------------

ARTIFACTS_DIR = Path("artifacts/matrices")

# Labels/descriptions match research/hypotheses.md as of its 2026-09-04 amendment (Amendment log):
# H1 is receptor pharmacology alone (not combined) -- the mapping table previously named the
# combined matrix as H1's primary test, which never matched H1's own statement/operational
# definition text. H2 was split into H2a (structure-only, this project's main computable secondary
# result) and H2b (the original structure-vs-combined comparison). No test result changed by this
# relabeling: the receptor-only and combined tests were already both NOT COMPUTABLE for the same
# receptor-sparsity reason regardless of which one carried the "PRIMARY" label.
TESTS = [
    ("PRIMARY", "H1: receptor-only distance vs. safety distance", "receptor_distance", "safety_distance"),
    ("SECONDARY", "H2a: structure-only distance vs. safety distance", "structure_distance", "safety_distance"),
    ("SECONDARY", "H2b: combined (structure+receptor) distance vs. safety distance", "combined_distance", "safety_distance"),
]


def _run_one(dist_a: pd.DataFrame, dist_b: pd.DataFrame) -> dict:
    subset = find_largest_complete_subset(dist_a, min_objects=4)
    if not subset:
        return {"computable": False, "reason": "fewer than 4 objects have complete pairwise data in the first matrix"}
    # dist_b (safety) is expected to be much more complete than dist_a in current data, but this
    # is not assumed -- re-check completeness on dist_b restricted to the same subset too.
    sub_b = dist_b.reindex(index=subset, columns=subset)
    if sub_b.isna().any().any():
        subset = find_largest_complete_subset(dist_b.loc[subset, subset], min_objects=4)
        if not subset:
            return {"computable": False, "reason": "second matrix has no complete >=4-object subset in common with the first"}
    try:
        result = mantel_test(dist_a.loc[subset, subset], dist_b.loc[subset, subset])
    except DegenerateMatrixError as exc:
        return {"computable": False, "reason": str(exc)}
    return {
        "computable": True,
        "statistic_spearman_rho": result.statistic,
        "p_value_one_sided": result.p_value_one_sided,
        "p_value_two_sided": result.p_value_two_sided,
        "n_permutations": result.n_permutations,
        "n_objects": result.n_objects,
        "objects": list(result.labels),
        "bootstrap_ci_low": result.bootstrap_ci_low,
        "bootstrap_ci_high": result.bootstrap_ci_high,
    }


def run() -> None:
    matrices = {
        name: pd.read_csv(ARTIFACTS_DIR / f"{name}_matrix.csv", index_col=0)
        for name in ("structure_distance", "receptor_distance", "combined_distance", "safety_distance")
    }

    results = []
    for label, description, key_a, key_b in TESTS:
        outcome = _run_one(matrices[key_a], matrices[key_b])
        results.append({"label": label, "description": description, **outcome})
        print(f"\n[{label}] {description}")
        if outcome["computable"]:
            print(
                f"  n_objects={outcome['n_objects']} rho={outcome['statistic_spearman_rho']:.4f} "
                f"p_one_sided={outcome['p_value_one_sided']:.4f} p_two_sided={outcome['p_value_two_sided']:.4f} "
                f"bootstrap_95ci=[{outcome['bootstrap_ci_low']:.4f}, {outcome['bootstrap_ci_high']:.4f}]"
            )
            print(f"  objects: {outcome['objects']}")
        else:
            print(f"  NOT COMPUTABLE: {outcome['reason']}")

    with (ARTIFACTS_DIR / "matrix_association_results.json").open("w") as f:
        json.dump({"n_permutations": DEFAULT_N_PERMUTATIONS, "seed": DEFAULT_SEED, "results": results}, f, indent=2)
    print(f"\nWrote {ARTIFACTS_DIR / 'matrix_association_results.json'}")


if __name__ == "__main__":
    run()
