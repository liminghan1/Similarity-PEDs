"""Phase 10 (EXPLORATORY, H4): does a compound's molecular phenotype predict its safety-phenotype
logROR, category by category? (project brief Sec. 21).

H4 as originally specified concerns "receptor/pharmacological features" -- infeasible here for the
same reason documented in research/analysis_plan.md's 2026-08-28 deviation entry (Phase 9): only
3/10 compounds have any receptor measurement. This module substitutes the fully-populated
molecular descriptor matrix as the predictor set instead, which is the only complete phenotype
representation available across all 10 compounds. This substitution is analogous to Phase 9's
structure-only pivot and is documented here rather than silently assumed.

Given n=10 compounds and up to 9 descriptor features, this is labeled EXPLORATORY, not SECONDARY
(project brief Sec. 40) -- Sec. 21 itself warns "avoid overparameterized regression... do not
overfit," and n=10 is genuinely inadequate for confirmatory multivariate inference regardless of
which penalization scheme is used. Results are hypothesis-generating only.

Model: Ridge regression (sklearn), leave-one-out cross-validated R^2 as the fit statistic (the
only internal-validation scheme that makes sense at n=10), with a permutation test (shuffle the
response 999 times, refit, compare) for whether the observed LOOCV R^2 exceeds chance -- per
Sec. 21's explicit call for permutation-based significance testing rather than trusting a raw R^2.

Usage:
    uv run python -m analysis.multivariate_association
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut, cross_val_predict

ARTIFACTS_DIR = Path("artifacts/matrices")
N_PERMUTATIONS = 999
SEED = 42
RIDGE_ALPHA = 1.0


def _prepare_predictors(molecular_matrix: pd.DataFrame) -> pd.DataFrame:
    numeric = molecular_matrix.select_dtypes(include="number")
    numeric = numeric.loc[:, numeric.std() > 0]  # drop zero-variance columns (see Phase 9)
    return (numeric - numeric.mean()) / numeric.std()


def loocv_r2(X: np.ndarray, y: np.ndarray, *, alpha: float = RIDGE_ALPHA) -> float:
    """Leave-one-out cross-validated R^2 for Ridge regression."""
    predictions = cross_val_predict(Ridge(alpha=alpha), X, y, cv=LeaveOneOut())
    ss_res = np.sum((y - predictions) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def permutation_test_r2(
    X: np.ndarray, y: np.ndarray, *, n_permutations: int = N_PERMUTATIONS, seed: int = SEED, alpha: float = RIDGE_ALPHA
) -> dict:
    observed = loocv_r2(X, y, alpha=alpha)
    rng = np.random.default_rng(seed)
    permuted = np.empty(n_permutations)
    for i in range(n_permutations):
        y_perm = rng.permutation(y)
        permuted[i] = loocv_r2(X, y_perm, alpha=alpha)
    p_value = (1 + np.sum(permuted >= observed)) / (1 + n_permutations)
    return {"observed_loocv_r2": float(observed), "p_value": float(p_value), "n_permutations": n_permutations}


def run() -> None:
    molecular_matrix = pd.read_csv(ARTIFACTS_DIR / "molecular_descriptor_matrix.csv", index_col=0)
    safety_matrix = pd.read_csv(ARTIFACTS_DIR / "safety_phenotype_matrix_logror.csv", index_col=0)

    predictors = _prepare_predictors(molecular_matrix)
    common = predictors.index.intersection(safety_matrix.index)
    predictors = predictors.loc[common]

    results = []
    for category in safety_matrix.columns:
        y_full = safety_matrix.loc[common, category]
        usable = y_full.notna()
        if usable.sum() < 5:  # need at least a few compounds for LOOCV to mean anything
            results.append({"category": category, "n": int(usable.sum()), "skipped_reason": "fewer than 5 compounds with a defined logROR value"})
            continue
        X = predictors.loc[usable].values
        y = y_full[usable].values.astype(float)
        stat = permutation_test_r2(X, y)
        results.append({"category": category, "n": int(usable.sum()), **stat})

    output = {
        "label": "EXPLORATORY (H4, adapted to molecular descriptors -- receptor data infeasible, see docstring)",
        "predictor_features": predictors.columns.tolist(),
        "model": f"Ridge(alpha={RIDGE_ALPHA}), leave-one-out CV, {N_PERMUTATIONS}-permutation test on LOOCV R^2",
        "results": results,
    }
    with (ARTIFACTS_DIR / "multivariate_association_results.json").open("w") as f:
        json.dump(output, f, indent=2)

    print(f"Predictors ({len(predictors.columns)}): {predictors.columns.tolist()}")
    for r in results:
        if "skipped_reason" in r:
            print(f"  {r['category']}: SKIPPED ({r['skipped_reason']})")
        else:
            print(f"  {r['category']} (n={r['n']}): LOOCV R^2={r['observed_loocv_r2']:.3f}, permutation p={r['p_value']:.4f}")
    print(f"\nWrote {ARTIFACTS_DIR / 'multivariate_association_results.json'}")


if __name__ == "__main__":
    run()
