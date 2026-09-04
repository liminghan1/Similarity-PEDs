"""Phase 11: the 8 pre-specified sensitivity analyses (research/analysis_plan.md Sec. 7 /
project brief Sec. 24), each re-running the one fully-computable primary-analysis result from
Phase 9 -- structure-only distance vs. safety distance (Mantel-style permutation test) -- under a
single varied condition, holding everything else fixed, to check whether the null/negative finding
(rho=-0.293, p_one_sided=0.956 on the full 10-compound cohort) is stable.

Every sensitivity is reported, including the ones that turn out not to be computable with current
data -- a sensitivity that cannot be run is itself a reportable fact, not something to skip
silently. The "all-FAERS background" variant of Sensitivity 6 was not computable in an earlier
pass (this project only ingests cohort-relevant FAERS reports, not the full database), but is now
computable via analysis/full_faers_background.py, which gets the equivalent aggregate counts
through live openFDA count-only queries instead of a full re-ingestion -- see that module's
docstring. Run `uv run python -m analysis.full_faers_background` before this script to produce
`artifacts/matrices/full_faers_background_matrix.csv`; if that file is missing, Sensitivity 6's
all-FAERS variant reports itself not computable with a pointer to that command, rather than
silently falling back to a stale or synthetic result.

Usage:
    uv run python -m analysis.sensitivity
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import DataStructs
from scipy.spatial.distance import cosine as cosine_distance
from scipy.stats import spearmanr

from analysis.matrix_association import (
    DegenerateMatrixError,
    find_largest_complete_subset,
    mantel_test,
)
from analysis.phenotype_matrix import (
    MIN_CELL_REPORTS,
    MIN_COMPOUND_REPORTS,
    build_safety_phenotype_matrix,
    compute_signal_table,
    load_ae_category_map,
)
from analysis.similarity_analysis import (
    _correlation_distance_matrix,
    build_safety_distance_matrix,
    build_structure_distance_matrix,
)
from backend.app.analytics.chemistry import compute_morgan_fingerprint
from backend.app.db.session import SessionLocal
from backend.app.models import Compound, FaersDrug, FaersReaction, FaersReport, ReportClassification

ARTIFACTS_DIR = Path("artifacts/matrices")


def load_drug_membership(db) -> pd.DataFrame:
    """report_id, compound_id, formulation_id, mapping_method, use_classification -- one row per
    matched cohort drug entry, carrying the metadata needed to build every filtered variant below
    without re-querying the database per sensitivity."""
    rows = (
        db.query(
            FaersDrug.report_id,
            FaersDrug.normalized_compound_id,
            FaersDrug.formulation_id,
            FaersDrug.mapping_method,
            ReportClassification.use_classification,
        )
        .join(FaersReport, FaersReport.id == FaersDrug.report_id)
        .outerjoin(ReportClassification, ReportClassification.report_id == FaersDrug.report_id)
        .filter(FaersDrug.normalized_compound_id.isnot(None), FaersReport.is_deduplicated_latest.is_(True))
        .all()
    )
    df = pd.DataFrame(
        rows, columns=["report_id", "compound_id", "formulation_id", "mapping_method", "use_classification"]
    )
    df["mapping_method"] = df["mapping_method"].apply(lambda m: m.value if hasattr(m, "value") else m)
    df["use_classification"] = df["use_classification"].apply(lambda c: c.value if hasattr(c, "value") else c)
    return df


def load_report_category_membership(db, category_map: dict[str, set[str]]) -> pd.DataFrame:
    rows = db.query(FaersReaction.report_id, FaersReaction.meddra_term).all()
    pairs = set()
    for report_id, term in rows:
        for category in category_map.get(term.strip().lower(), ()):
            pairs.add((report_id, category))
    return pd.DataFrame(sorted(pairs), columns=["report_id", "category"])


def filter_report_compound(drug_membership: pd.DataFrame, **filters) -> pd.DataFrame:
    """Filters `drug_membership` (load_drug_membership's output) down to (report_id,
    compound_id) pairs matching every column=value constraint in `filters`, e.g.
    `filter_report_compound(df, formulation_id=None)` for "parent-only" (Sensitivity 2) or
    `filter_report_compound(df, mapping_method=["exact_alias", "curated_match"])` for
    high-confidence-only (Sensitivity 3).

    `value=None` matches missing values via `.isna()`, NOT `== None` -- pandas' `==` against
    `None` returns all-False even for genuinely missing (NaN/None) cells, which silently
    produced zero rows for Sensitivity 2 until this was pulled out of an inline closure and
    tested directly (backend/tests/test_sensitivity.py).
    """
    df = drug_membership
    for col, val in filters.items():
        if val is None:
            df = df[df[col].isna()]
        elif isinstance(val, (list, tuple, set)):
            df = df[df[col].isin(val)]
        else:
            df = df[df[col] == val]
    return df[["report_id", "compound_id"]].drop_duplicates()


def load_top_individual_terms(db, n: int = 20) -> pd.DataFrame:
    """report_id, category -- here "category" is an individual MedDRA term (case-normalized),
    restricted to the n most frequent terms overall, for Sensitivity 4."""
    rows = db.query(FaersReaction.report_id, FaersReaction.meddra_term).all()
    terms = pd.DataFrame(rows, columns=["report_id", "term"])
    terms["term"] = terms["term"].str.strip().str.lower()
    top_terms = terms["term"].value_counts().head(n).index.tolist()
    filtered = terms[terms["term"].isin(top_terms)].drop_duplicates()
    return filtered.rename(columns={"term": "category"})


def run_h2_test(
    report_compound: pd.DataFrame,
    report_category: pd.DataFrame,
    compound_names: dict[int, str],
    categories: list[str],
    structure_dist: pd.DataFrame,
    *,
    min_cell_reports: int = MIN_CELL_REPORTS,
    min_compound_reports: int = MIN_COMPOUND_REPORTS,
    min_shared_features: int = 3,
) -> dict:
    """Rebuilds the safety phenotype matrix from the given (possibly filtered) report membership
    and reruns the H2 (structure-only vs. safety) Mantel test against the given structure distance
    matrix. Returns a result dict, never raising -- degenerate cases are reported, not crashed on."""
    if report_compound.empty:
        return {"computable": False, "reason": "no reports remain after filtering"}

    signal_table = compute_signal_table(
        report_compound, report_category, compound_names, categories,
        min_cell_reports=min_cell_reports, min_compound_reports=min_compound_reports,
    )
    safety_matrix = build_safety_phenotype_matrix(signal_table)
    n_compounds_eligible = int((signal_table.groupby("canonical_name")["compound_meets_minimum"].first()).sum())

    safety_dist = _correlation_distance_matrix(safety_matrix, min_shared_features=min_shared_features)

    common = sorted(set(structure_dist.index) & set(safety_dist.index))
    if len(common) < 4:
        return {"computable": False, "reason": f"only {len(common)} compounds in common", "n_compounds_eligible": n_compounds_eligible}

    subset = find_largest_complete_subset(safety_dist.loc[common, common], min_objects=4)
    if not subset:
        return {"computable": False, "reason": "no >=4-compound complete subset in the safety distance matrix", "n_compounds_eligible": n_compounds_eligible}

    try:
        result = mantel_test(structure_dist.loc[subset, subset], safety_dist.loc[subset, subset])
    except DegenerateMatrixError as exc:
        return {"computable": False, "reason": str(exc), "n_compounds_eligible": n_compounds_eligible}

    return {
        "computable": True,
        "n_compounds_eligible": n_compounds_eligible,
        "n_objects_tested": result.n_objects,
        "objects_tested": list(result.labels),
        "statistic_spearman_rho": result.statistic,
        "p_value_one_sided": result.p_value_one_sided,
        "p_value_two_sided": result.p_value_two_sided,
    }


# --------------------------------------------------------------------------------------
# Alternate similarity metrics (Sensitivity 5)
# --------------------------------------------------------------------------------------

def build_alternate_fingerprint_distance_matrix(db) -> pd.DataFrame:
    """Dice coefficient distance, the documented alternate to the primary Tanimoto metric."""
    compounds = db.query(Compound).filter(Compound.smiles.isnot(None)).order_by(Compound.canonical_name).all()
    labels = [c.canonical_name for c in compounds]
    fps = {c.canonical_name: compute_morgan_fingerprint(c.smiles) for c in compounds}
    matrix = pd.DataFrame(np.zeros((len(labels), len(labels))), index=labels, columns=labels)
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            d = 1.0 - DataStructs.DiceSimilarity(fps[a], fps[b])
            matrix.loc[a, b] = d
            matrix.loc[b, a] = d
    return matrix


def build_alternate_descriptor_distance_matrix(molecular_matrix: pd.DataFrame) -> pd.DataFrame:
    """Cosine distance, the documented alternate to the primary Euclidean metric."""
    numeric = molecular_matrix.select_dtypes(include="number")
    numeric = numeric.loc[:, numeric.std() > 0]
    z = (numeric - numeric.mean()) / numeric.std()
    labels = z.index.tolist()
    matrix = pd.DataFrame(np.zeros((len(labels), len(labels))), index=labels, columns=labels)
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            d = float(cosine_distance(z.loc[a].values, z.loc[b].values))
            matrix.loc[a, b] = d
            matrix.loc[b, a] = d
    return matrix


def _spearman_distance_matrix(wide_matrix: pd.DataFrame, *, min_shared_features: int = 3) -> pd.DataFrame:
    labels = wide_matrix.index.tolist()
    matrix = pd.DataFrame(np.nan, index=labels, columns=labels)
    for label in labels:
        matrix.loc[label, label] = 0.0
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            row_a, row_b = wide_matrix.loc[a], wide_matrix.loc[b]
            shared = row_a.notna() & row_b.notna()
            if shared.sum() < min_shared_features:
                continue
            rho = spearmanr(row_a[shared].astype(float), row_b[shared].astype(float)).statistic
            if pd.isna(rho):
                continue
            d = 1.0 - rho
            matrix.loc[a, b] = d
            matrix.loc[b, a] = d
    return matrix


def run() -> None:
    db = SessionLocal()
    try:
        drug_membership = load_drug_membership(db)
        category_map = load_ae_category_map()
        report_category = load_report_category_membership(db, category_map)
        individual_terms = load_top_individual_terms(db)
        compound_names = {c.id: c.canonical_name for c in db.query(Compound).all()}
        molecular_matrix = pd.read_csv(ARTIFACTS_DIR / "molecular_descriptor_matrix.csv", index_col=0)
        fingerprint_dist_alt = build_alternate_fingerprint_distance_matrix(db)
    finally:
        db.close()

    categories = sorted({c for cats in category_map.values() for c in cats})
    structure_dist = pd.read_csv(ARTIFACTS_DIR / "structure_distance_matrix.csv", index_col=0)
    descriptor_dist_alt = build_alternate_descriptor_distance_matrix(molecular_matrix)
    structure_dist_alt = build_structure_distance_matrix(fingerprint_dist_alt, descriptor_dist_alt)

    base_report_compound = drug_membership[["report_id", "compound_id"]].drop_duplicates()

    results = {}

    # Sensitivity 1: alternate minimum-report thresholds (+/-50%)
    results["1_lower_thresholds"] = run_h2_test(
        base_report_compound, report_category, compound_names, categories, structure_dist,
        min_compound_reports=10, min_cell_reports=2,
    )
    results["1_higher_thresholds"] = run_h2_test(
        base_report_compound, report_category, compound_names, categories, structure_dist,
        min_compound_reports=30, min_cell_reports=5,
    )

    # Sensitivity 2: exact parent only (formulation_id IS NULL) vs. parent+esters (primary, base)
    parent_only = filter_report_compound(drug_membership, formulation_id=None)
    results["2_parent_only"] = run_h2_test(
        parent_only, report_category, compound_names, categories, structure_dist
    )

    # Sensitivity 3: exclude uncertain/low-confidence drug-name mapping
    high_confidence = filter_report_compound(drug_membership, mapping_method=["exact_alias", "curated_match"])
    results["3_high_confidence_mapping_only"] = run_h2_test(
        high_confidence, report_category, compound_names, categories, structure_dist
    )

    # Sensitivity 4: individual MedDRA terms (top 20) instead of research-defined categories
    top_term_list = sorted(individual_terms["category"].unique())
    results["4_individual_terms"] = run_h2_test(
        base_report_compound, individual_terms, compound_names, top_term_list, structure_dist
    )

    # Sensitivity 5: alternate similarity metrics (Dice+cosine structure; Spearman safety)
    signal_table_primary = compute_signal_table(base_report_compound, report_category, compound_names, categories)
    safety_matrix_primary = build_safety_phenotype_matrix(signal_table_primary)
    safety_dist_spearman = _spearman_distance_matrix(safety_matrix_primary)
    common_5 = sorted(set(structure_dist_alt.index) & set(safety_dist_spearman.index))
    subset_5 = find_largest_complete_subset(safety_dist_spearman.loc[common_5, common_5], min_objects=4) if len(common_5) >= 4 else []
    if subset_5:
        try:
            r5 = mantel_test(structure_dist_alt.loc[subset_5, subset_5], safety_dist_spearman.loc[subset_5, subset_5])
            results["5_alternate_metrics"] = {
                "computable": True, "n_objects_tested": r5.n_objects, "objects_tested": list(r5.labels),
                "statistic_spearman_rho": r5.statistic, "p_value_one_sided": r5.p_value_one_sided,
                "p_value_two_sided": r5.p_value_two_sided,
                "note": "structure=Dice(fingerprint)+cosine(descriptors); safety=Spearman correlation distance",
            }
        except DegenerateMatrixError as exc:
            results["5_alternate_metrics"] = {"computable": False, "reason": str(exc)}
    else:
        results["5_alternate_metrics"] = {"computable": False, "reason": "no >=4-compound complete subset under alternate metrics"}

    # Sensitivity 6: alternate safety phenotype definition (standardized report proportion;
    # serious-proportion vector) using the existing cohort-relative background.
    proportion_rows = []
    for _, row in signal_table_primary.iterrows():
        proportion_rows.append({
            "canonical_name": row["canonical_name"], "category": row["category"],
            "value": (row["a"] / row["total_compound_reports"]) if row["total_compound_reports"] else np.nan,
        })
    proportion_df = pd.DataFrame(proportion_rows)
    z = proportion_df.copy()
    z["value"] = z.groupby("category")["value"].transform(lambda s: (s - s.mean()) / s.std() if s.std() > 0 else np.nan)
    proportion_matrix = z.pivot(index="canonical_name", columns="category", values="value")
    proportion_dist = _correlation_distance_matrix(proportion_matrix)
    common_6 = sorted(set(structure_dist.index) & set(proportion_dist.index))
    subset_6 = find_largest_complete_subset(proportion_dist.loc[common_6, common_6], min_objects=4) if len(common_6) >= 4 else []
    if subset_6:
        try:
            r6 = mantel_test(structure_dist.loc[subset_6, subset_6], proportion_dist.loc[subset_6, subset_6])
            results["6_standardized_proportion_phenotype"] = {
                "computable": True, "n_objects_tested": r6.n_objects, "objects_tested": list(r6.labels),
                "statistic_spearman_rho": r6.statistic, "p_value_one_sided": r6.p_value_one_sided,
                "p_value_two_sided": r6.p_value_two_sided,
            }
        except DegenerateMatrixError as exc:
            results["6_standardized_proportion_phenotype"] = {"computable": False, "reason": str(exc)}
    else:
        results["6_standardized_proportion_phenotype"] = {"computable": False, "reason": "no >=4-compound complete subset"}
    full_faers_matrix_path = ARTIFACTS_DIR / "full_faers_background_matrix.csv"
    if full_faers_matrix_path.exists():
        full_faers_matrix = pd.read_csv(full_faers_matrix_path, index_col=0)
        full_faers_dist = build_safety_distance_matrix(full_faers_matrix)
        common_6b = sorted(set(structure_dist.index) & set(full_faers_dist.index))
        subset_6b = (
            find_largest_complete_subset(full_faers_dist.loc[common_6b, common_6b], min_objects=4)
            if len(common_6b) >= 4
            else []
        )
        if subset_6b:
            try:
                r6b = mantel_test(
                    structure_dist.loc[subset_6b, subset_6b], full_faers_dist.loc[subset_6b, subset_6b]
                )
                results["6_all_faers_background"] = {
                    "computable": True,
                    "n_objects_tested": r6b.n_objects,
                    "objects_tested": list(r6b.labels),
                    "statistic_spearman_rho": r6b.statistic,
                    "p_value_one_sided": r6b.p_value_one_sided,
                    "p_value_two_sided": r6b.p_value_two_sided,
                    "note": (
                        "Safety background = entire FAERS database (live openFDA count queries via "
                        "analysis/full_faers_background.py), not just the other 9 cohort compounds. "
                        "See that module's counts artifact for the raw a/b/c/d per cell."
                    ),
                }
            except DegenerateMatrixError as exc:
                results["6_all_faers_background"] = {"computable": False, "reason": str(exc)}
        else:
            results["6_all_faers_background"] = {
                "computable": False,
                "reason": "no >=4-compound complete subset shared between structure and all-FAERS-background safety distance",
            }
    else:
        results["6_all_faers_background"] = {
            "computable": False,
            "reason": (
                "artifacts/matrices/full_faers_background_matrix.csv not found -- run "
                "`uv run python -m analysis.full_faers_background` first (live openFDA count "
                "queries; not part of this script's own, fully-offline computation)."
            ),
        }

    # Sensitivity 7 / 8: therapeutic-only / misuse-only report subsets
    therapeutic_only = filter_report_compound(drug_membership, use_classification="therapeutic")
    results["7_therapeutic_only"] = run_h2_test(
        therapeutic_only, report_category, compound_names, categories, structure_dist
    )
    misuse_only = filter_report_compound(drug_membership, use_classification="misuse")
    results["8_misuse_only"] = run_h2_test(
        misuse_only, report_category, compound_names, categories, structure_dist
    )

    with (ARTIFACTS_DIR / "sensitivity_results.json").open("w") as f:
        json.dump(results, f, indent=2, default=str)

    print("Sensitivity analysis summary (all re-run the H2 structure-only vs. safety Mantel test):\n")
    for name, r in results.items():
        if r.get("computable"):
            print(
                f"  {name}: n={r['n_objects_tested']} rho={r['statistic_spearman_rho']:.3f} "
                f"p_one_sided={r['p_value_one_sided']:.3f}"
            )
        else:
            print(f"  {name}: NOT COMPUTABLE ({r['reason']})")
    print(f"\nWrote {ARTIFACTS_DIR / 'sensitivity_results.json'}")


if __name__ == "__main__":
    run()
