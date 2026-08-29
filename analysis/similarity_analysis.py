"""Phase 9: pairwise similarity/distance matrices from the Phase 8 phenotype matrices
(research/analysis_plan.md Sec. 2-3).

Distance matrices produced (all n_compounds x n_compounds, symmetric, zero diagonal):
- `fingerprint_distance`   -- 1 - Tanimoto(Morgan fp), fully defined for all pairs (Sec. 3).
- `descriptor_distance`    -- Euclidean distance on z-scored molecular descriptors, fully defined.
- `structure_distance`     -- SECONDARY (H2) representation: mean of min-max-normalized
                              fingerprint_distance and descriptor_distance. Fully defined for all
                              10 cohort compounds -- this is the only fully-computable full-cohort
                              molecular representation given current receptor data coverage (see
                              research/analysis_plan.md Deviations, 2026-08-28).
- `receptor_distance`      -- 1 - Pearson r on shared non-null pActivity columns
                              (pairwise-complete, MIN_SHARED_RECEPTOR_FEATURES minimum -- see
                              below). With current data, only compound pairs sharing >=3 receptor
                              columns get a defined value; empirically, in the current cohort,
                              ZERO pairs meet this bar (the one pair with any overlap,
                              testosterone-oxandrolone, shares exactly 2 columns, for which a
                              Pearson r is mathematically always +/-1 and therefore not
                              meaningful -- excluded deliberately, not by accident).
- `combined_distance`      -- PRIMARY (nominal) representation: mean of min-max-normalized
                              structure_distance and receptor_distance, defined only where both
                              are defined. Given the above, this matrix has no defined pairs with
                              current data -- see research/analysis_plan.md Deviations.
- `safety_distance`        -- 1 - Pearson r on shared non-null logROR categories from the wide
                              safety phenotype matrix, same MIN_SHARED_RECEPTOR_FEATURES-style
                              minimum applied for consistency.

A minimum-shared-features threshold for a Pearson-correlation-based distance to be considered
defined at all (rather than a mathematically degenerate n=2 correlation, which is always exactly
+-1 and carries no information) was not spelled out in research/analysis_plan.md's original text
and is filled in here, before any matrix-association test has been run or inspected -- MIN_SHARED_
RECEPTOR_FEATURES = 3, the smallest number of paired observations for which a Pearson correlation
is not trivially deterministic.

Usage:
    uv run python -m analysis.similarity_analysis
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.analytics.chemistry import tanimoto_similarity
from backend.app.db.session import SessionLocal
from backend.app.models import Compound

MIN_SHARED_RECEPTOR_FEATURES = 3
ARTIFACTS_DIR = Path("artifacts/matrices")


def _empty_square(labels: list[str]) -> pd.DataFrame:
    return pd.DataFrame(np.zeros((len(labels), len(labels))), index=labels, columns=labels)


def _minmax_normalize(matrix: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalize the off-diagonal (upper-triangle) values to [0, 1], applied symmetrically.
    NaNs pass through unchanged."""
    labels = matrix.index.tolist()
    values = [matrix.loc[a, b] for a, b in combinations(labels, 2) if pd.notna(matrix.loc[a, b])]
    if not values:
        return matrix.copy()
    lo, hi = min(values), max(values)
    span = hi - lo
    normalized = matrix.copy()
    for a, b in combinations(labels, 2):
        v = matrix.loc[a, b]
        if pd.isna(v):
            continue
        scaled = 0.5 if span == 0 else (v - lo) / span
        normalized.loc[a, b] = scaled
        normalized.loc[b, a] = scaled
    return normalized


def build_fingerprint_distance_matrix(db) -> pd.DataFrame:
    compounds = db.query(Compound).filter(Compound.smiles.isnot(None)).order_by(Compound.canonical_name).all()
    labels = [c.canonical_name for c in compounds]
    smiles = {c.canonical_name: c.smiles for c in compounds}
    matrix = _empty_square(labels)
    for a, b in combinations(labels, 2):
        d = 1.0 - tanimoto_similarity(smiles[a], smiles[b])
        matrix.loc[a, b] = d
        matrix.loc[b, a] = d
    return matrix


def build_descriptor_distance_matrix(molecular_matrix: pd.DataFrame) -> pd.DataFrame:
    """Euclidean distance on z-scored descriptors (research/analysis_plan.md Sec. 3). z-scoring
    uses sample standard deviation (pandas default, ddof=1).

    Columns with zero variance across the cohort are dropped before z-scoring, not silently left
    in: a constant column's z-score is 0/0 = NaN for every compound, which would otherwise poison
    every pairwise Euclidean distance (found empirically -- with the real 10-compound cohort,
    `rotatable_bonds` is 0 for all 10 compounds, since this cohort's steroid scaffolds have no
    rotatable bonds at all). A zero-variance column carries no discriminative information among
    the compounds being compared, so dropping it loses nothing.
    """
    numeric = molecular_matrix.select_dtypes(include="number")
    zero_variance_columns = numeric.columns[numeric.std() == 0].tolist()
    if zero_variance_columns:
        print(f"build_descriptor_distance_matrix: dropping zero-variance columns {zero_variance_columns}")
        numeric = numeric.drop(columns=zero_variance_columns)
    z = (numeric - numeric.mean()) / numeric.std()
    labels = z.index.tolist()
    matrix = _empty_square(labels)
    for a, b in combinations(labels, 2):
        d = float(np.linalg.norm(z.loc[a] - z.loc[b]))
        matrix.loc[a, b] = d
        matrix.loc[b, a] = d
    return matrix


def build_structure_distance_matrix(fingerprint_dist: pd.DataFrame, descriptor_dist: pd.DataFrame) -> pd.DataFrame:
    fp_norm = _minmax_normalize(fingerprint_dist)
    desc_norm = _minmax_normalize(descriptor_dist)
    return (fp_norm + desc_norm) / 2.0


def _correlation_distance_matrix(
    wide_matrix: pd.DataFrame, *, min_shared_features: int = MIN_SHARED_RECEPTOR_FEATURES
) -> pd.DataFrame:
    """1 - Pearson r on shared non-null columns between each pair of rows, pairwise-complete.
    A pair's distance is NaN (not zero, not imputed) if fewer than `min_shared_features` columns
    are non-null for BOTH rows."""
    labels = wide_matrix.index.tolist()
    matrix = pd.DataFrame(np.nan, index=labels, columns=labels)
    for label in labels:
        matrix.loc[label, label] = 0.0
    for a, b in combinations(labels, 2):
        row_a, row_b = wide_matrix.loc[a], wide_matrix.loc[b]
        shared = row_a.notna() & row_b.notna()
        if shared.sum() < min_shared_features:
            continue
        r = np.corrcoef(row_a[shared].astype(float), row_b[shared].astype(float))[0, 1]
        if np.isnan(r):
            continue
        d = 1.0 - r
        matrix.loc[a, b] = d
        matrix.loc[b, a] = d
    return matrix


def build_receptor_distance_matrix(receptor_matrix: pd.DataFrame) -> pd.DataFrame:
    return _correlation_distance_matrix(receptor_matrix)


def build_safety_distance_matrix(safety_matrix: pd.DataFrame) -> pd.DataFrame:
    return _correlation_distance_matrix(safety_matrix)


def build_combined_distance_matrix(structure_dist: pd.DataFrame, receptor_dist: pd.DataFrame) -> pd.DataFrame:
    """PRIMARY (nominal) representation: mean of min-max-normalized structure + receptor
    distance, defined ONLY where both components are defined -- never falls back to structure-only
    for a pair with missing receptor data (research/analysis_plan.md Deviations, 2026-08-28)."""
    structure_norm = _minmax_normalize(structure_dist)
    receptor_norm = _minmax_normalize(receptor_dist)
    labels = structure_dist.index.tolist()
    matrix = pd.DataFrame(np.nan, index=labels, columns=labels)
    for label in labels:
        matrix.loc[label, label] = 0.0
    for a, b in combinations(labels, 2):
        r_val = receptor_norm.loc[a, b]
        if pd.isna(r_val):
            continue
        d = (structure_norm.loc[a, b] + r_val) / 2.0
        matrix.loc[a, b] = d
        matrix.loc[b, a] = d
    return matrix


def n_defined_pairs(matrix: pd.DataFrame) -> int:
    labels = matrix.index.tolist()
    return sum(1 for a, b in combinations(labels, 2) if pd.notna(matrix.loc[a, b]))


def run() -> None:
    molecular_matrix = pd.read_csv(ARTIFACTS_DIR / "molecular_descriptor_matrix.csv", index_col=0)
    receptor_matrix = pd.read_csv(ARTIFACTS_DIR / "receptor_phenotype_matrix_primary.csv", index_col=0)
    safety_matrix = pd.read_csv(ARTIFACTS_DIR / "safety_phenotype_matrix_logror.csv", index_col=0)

    db = SessionLocal()
    try:
        fingerprint_dist = build_fingerprint_distance_matrix(db)
    finally:
        db.close()

    descriptor_dist = build_descriptor_distance_matrix(molecular_matrix)
    structure_dist = build_structure_distance_matrix(fingerprint_dist, descriptor_dist)
    receptor_dist = build_receptor_distance_matrix(receptor_matrix)
    combined_dist = build_combined_distance_matrix(structure_dist, receptor_dist)
    safety_dist = build_safety_distance_matrix(safety_matrix)

    for name, matrix in [
        ("fingerprint_distance", fingerprint_dist),
        ("descriptor_distance", descriptor_dist),
        ("structure_distance", structure_dist),
        ("receptor_distance", receptor_dist),
        ("combined_distance", combined_dist),
        ("safety_distance", safety_dist),
    ]:
        matrix.to_csv(ARTIFACTS_DIR / f"{name}_matrix.csv")
        total_pairs = len(matrix) * (len(matrix) - 1) // 2
        print(f"{name}: {matrix.shape}, {n_defined_pairs(matrix)}/{total_pairs} pairs defined")


if __name__ == "__main__":
    run()
