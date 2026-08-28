"""Phase 8: build the molecular, receptor, and safety phenotype matrices from ingested data
(Phases 3-6) and write versioned artifacts to artifacts/matrices/.

Three independent phenotype representations (project brief Sec. 14-15), never merged into one
raw-value table (their units/scales are incommensurable -- combination happens at the
*similarity/distance* level in Phase 9, per research/analysis_plan.md Sec. 2-3):

1. **Molecular descriptor matrix** -- RDKit descriptors per compound (backend/app/analytics/
   chemistry.py), fully populated (every cohort compound has a valid structure).
2. **Receptor phenotype matrix** -- median-aggregated pActivity per compound x (target,
   measurement_type), restricted to ChEMBL confidence_score >= 8 for the PRIMARY matrix
   (research/exclusion_rules.md Sec. 3); a separate all-confidence variant is written for the
   confidence-restricted sensitivity analysis. Missing cells are NaN, never zero or imputed.
3. **Safety phenotype** -- a *long-format signal table* (every compound x research-defined AE
   category, with the full a/b/c/d contingency counts, ROR, logROR, CI, and sparse-cell flag --
   research/analysis_plan.md Sec. 1 requires these fields always travel together, never a bare
   logROR number) and a derived *wide-format logROR matrix* for similarity analysis, with
   sparse cells (a < 3, research/exclusion_rules.md Sec. 4) set to NaN rather than shown as a
   reliable estimate.

Usage:
    uv run python -m analysis.phenotype_matrix
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.analytics.chemistry import compute_descriptors
from backend.app.analytics.signals import compute_ror
from backend.app.db.session import SessionLocal
from backend.app.models import Bioactivity, Compound, FaersDrug, FaersReaction, FaersReport, Target
from pipelines.bindingdb.targets import BINDINGDB_TARGETS
from pipelines.chembl.targets import RECEPTOR_TARGETS

ARTIFACTS_DIR = Path("artifacts/matrices")
AE_CATEGORIES_CSV = Path("research/ae_categories.csv")

MIN_COMPOUND_REPORTS = 20  # research/exclusion_rules.md Sec. 4
MIN_CELL_REPORTS = 3  # research/exclusion_rules.md Sec. 4 ("a" in the 2x2 table)
PRIMARY_CONFIDENCE_THRESHOLD = 8  # research/exclusion_rules.md Sec. 3


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


# --------------------------------------------------------------------------------------
# 1. Molecular descriptor matrix
# --------------------------------------------------------------------------------------

def build_molecular_descriptor_matrix(db) -> pd.DataFrame:
    compounds = db.query(Compound).filter(Compound.smiles.isnot(None)).order_by(Compound.canonical_name).all()
    rows = []
    for c in compounds:
        desc = compute_descriptors(c.smiles)
        rows.append(
            {
                "canonical_name": c.canonical_name,
                "molecular_formula": desc.molecular_formula,
                "molecular_weight": desc.molecular_weight,
                "xlogp": desc.xlogp,
                "tpsa": desc.tpsa,
                "h_bond_donors": desc.h_bond_donors,
                "h_bond_acceptors": desc.h_bond_acceptors,
                "rotatable_bonds": desc.rotatable_bonds,
                "ring_count": desc.ring_count,
                "aromatic_ring_count": desc.aromatic_ring_count,
                "fraction_csp3": desc.fraction_csp3,
            }
        )
    return pd.DataFrame(rows).set_index("canonical_name")


# --------------------------------------------------------------------------------------
# 2. Receptor phenotype matrix
# --------------------------------------------------------------------------------------

def _target_id_to_receptor_short_name(db) -> dict[int, str]:
    lookup = {}
    for r in RECEPTOR_TARGETS:
        lookup[("chembl", r.chembl_target_id)] = r.short_name
    for r in BINDINGDB_TARGETS:
        lookup[("bindingdb", r.uniprot_id)] = r.short_name
    result = {}
    for target in db.query(Target).all():
        short_name = lookup.get((target.source, target.source_target_id))
        if short_name is not None:
            result[target.id] = short_name
    return result


def build_receptor_phenotype_matrix(db, *, min_confidence: int | None = PRIMARY_CONFIDENCE_THRESHOLD) -> pd.DataFrame:
    """rows=canonical_name, columns=f"{receptor}_{measurement_type}" (e.g. "AR_IC50"), values are
    the median p_activity within each (compound, target, measurement_type) group -- pairwise
    complete, never imputed (research/exclusion_rules.md Sec. 3/Sec. 15).

    `min_confidence=None` builds the all-confidence sensitivity variant instead of the primary
    (>=8) matrix.
    """
    target_to_receptor = _target_id_to_receptor_short_name(db)
    compound_names = {c.id: c.canonical_name for c in db.query(Compound).all()}

    query = db.query(Bioactivity).filter(Bioactivity.p_activity.isnot(None))
    records = []
    for b in query.all():
        receptor = target_to_receptor.get(b.target_id)
        if receptor is None:
            continue
        assay_confidence = b.assay.confidence_score
        if min_confidence is not None and (assay_confidence is None or assay_confidence < min_confidence):
            continue
        records.append(
            {
                "canonical_name": compound_names[b.compound_id],
                "column": f"{receptor}_{b.measurement_type.value}",
                "p_activity": float(b.p_activity),
            }
        )

    if not records:
        return pd.DataFrame(index=pd.Index(sorted(compound_names.values()), name="canonical_name"))

    df = pd.DataFrame(records)
    medians = df.groupby(["canonical_name", "column"])["p_activity"].median().unstack("column")
    return medians.reindex(sorted(compound_names.values()))


# --------------------------------------------------------------------------------------
# 3. Safety phenotype: AE category mapping + signal table + wide logROR matrix
# --------------------------------------------------------------------------------------

def load_ae_category_map() -> dict[str, set[str]]:
    """normalized (lowercase) reactionmeddrapt text -> {research-defined categories}. A term can
    map to more than one category (research/ae_categories.csv documents this explicitly, e.g.
    "polycythaemia" -> thrombotic AND hematologic)."""
    category_map: dict[str, set[str]] = {}
    with AE_CATEGORIES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            term = row["representative_reported_term"].strip().lower()
            category_map.setdefault(term, set()).add(row["category"].strip())
    return category_map


def _load_report_compound_membership(db) -> pd.DataFrame:
    """One row per (report_id, compound_id) for every distinct cohort compound present in a
    deduplicated-latest report."""
    rows = (
        db.query(FaersDrug.report_id, FaersDrug.normalized_compound_id)
        .join(FaersReport, FaersReport.id == FaersDrug.report_id)
        .filter(FaersDrug.normalized_compound_id.isnot(None), FaersReport.is_deduplicated_latest.is_(True))
        .distinct()
        .all()
    )
    return pd.DataFrame(rows, columns=["report_id", "compound_id"])


def _load_report_category_membership(db, category_map: dict[str, set[str]]) -> pd.DataFrame:
    """One row per (report_id, category) for every research-defined category represented by at
    least one reaction in that report (case-insensitive exact match against ae_categories.csv --
    see analysis/phenotype_matrix.py module docstring and research/ae_categories.csv for why
    real FAERS data requires case-insensitive matching: the same MedDRA term appears in both
    proper-case and ALL-CAPS forms across different reports)."""
    rows = db.query(FaersReaction.report_id, FaersReaction.meddra_term).all()
    pairs = set()
    for report_id, term in rows:
        for category in category_map.get(term.strip().lower(), ()):
            pairs.add((report_id, category))
    return pd.DataFrame(sorted(pairs), columns=["report_id", "category"])


def compute_signal_table(
    report_compound: pd.DataFrame,
    report_category: pd.DataFrame,
    compound_names: dict[int, str],
    categories: list[str],
) -> pd.DataFrame:
    """Pure combinatorial core of the safety signal table -- given report-level membership
    (which reports mention which cohort compound; which reports have a reaction in which
    category), builds the a/b/c/d contingency table and ROR/CI for every (compound, category)
    pair. Independent of the database so it is unit-testable
    (backend/tests/test_phenotype_matrix.py) with small synthetic report sets where the correct
    a/b/c/d counts can be hand-verified."""
    all_report_ids = set(report_compound["report_id"])

    reports_by_compound: dict[int, set[int]] = {
        cid: set(g["report_id"]) for cid, g in report_compound.groupby("compound_id")
    }
    reports_by_category: dict[str, set[int]] = {
        cat: set(g["report_id"]) for cat, g in report_category.groupby("category")
    }

    rows = []
    for compound_id, compound_reports in reports_by_compound.items():
        compound_name = compound_names[compound_id]
        n_total = len(compound_reports)
        for category in categories:
            category_reports = reports_by_category.get(category, set())
            a = len(compound_reports & category_reports)
            b = n_total - a
            other_reports = all_report_ids - compound_reports
            c = len(other_reports & category_reports)
            d = len(other_reports) - c

            result = compute_ror(a, b, c, d)
            rows.append(
                {
                    "canonical_name": compound_name,
                    "category": category,
                    "a": a, "b": b, "c": c, "d": d,
                    "total_compound_reports": n_total,
                    "ror": result.ror,
                    "log_ror": result.log_ror,
                    "se_log_ror": result.se_log_ror,
                    "ci_low": result.ci_low,
                    "ci_high": result.ci_high,
                    "continuity_correction_applied": result.continuity_correction_applied,
                    "sparse_cell": a < MIN_CELL_REPORTS,
                    "compound_meets_minimum": n_total >= MIN_COMPOUND_REPORTS,
                }
            )
    return pd.DataFrame(rows)


def build_safety_signal_table(db, category_map: dict[str, set[str]]) -> pd.DataFrame:
    compound_names = {c.id: c.canonical_name for c in db.query(Compound).all()}
    report_compound = _load_report_compound_membership(db)
    report_category = _load_report_category_membership(db, category_map)
    categories = sorted({cat for cats in category_map.values() for cat in cats})
    return compute_signal_table(report_compound, report_category, compound_names, categories)


def build_safety_phenotype_matrix(signal_table: pd.DataFrame) -> pd.DataFrame:
    """Wide-format logROR matrix for similarity analysis (Phase 9): sparse cells and compounds
    below the minimum-report threshold are NaN, never a plausible-looking-but-unreliable number."""
    eligible = signal_table[signal_table["compound_meets_minimum"] & ~signal_table["sparse_cell"]]
    matrix = eligible.pivot(index="canonical_name", columns="category", values="log_ror")
    all_names = sorted(signal_table["canonical_name"].unique())
    all_categories = sorted(signal_table["category"].unique())
    return matrix.reindex(index=all_names, columns=all_categories)


def build_compound_report_summary(db) -> pd.DataFrame:
    compound_names = {c.id: c.canonical_name for c in db.query(Compound).all()}
    report_compound = _load_report_compound_membership(db)
    report_flags = pd.DataFrame(
        db.query(
            FaersReport.id, FaersReport.serious, FaersReport.seriousness_hospitalization, FaersReport.seriousness_death
        )
        .filter(FaersReport.is_deduplicated_latest.is_(True))
        .all(),
        columns=["report_id", "serious", "hospitalization", "death"],
    )
    merged = report_compound.merge(report_flags, on="report_id", how="left")

    rows = []
    for compound_id, group in merged.groupby("compound_id"):
        n = len(group)
        rows.append(
            {
                "canonical_name": compound_names[compound_id],
                "total_reports": n,
                "serious_reports": int(group["serious"].sum()),
                "hospitalization_reports": int(group["hospitalization"].sum()),
                "death_reports": int(group["death"].sum()),
                "serious_proportion": float(group["serious"].sum()) / n if n else float("nan"),
            }
        )
    return pd.DataFrame(rows).set_index("canonical_name").reindex(sorted(compound_names.values()))


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------

def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        molecular = build_molecular_descriptor_matrix(db)
        receptor_primary = build_receptor_phenotype_matrix(db, min_confidence=PRIMARY_CONFIDENCE_THRESHOLD)
        receptor_all_confidence = build_receptor_phenotype_matrix(db, min_confidence=None)
        category_map = load_ae_category_map()
        signal_table = build_safety_signal_table(db, category_map)
        safety_matrix = build_safety_phenotype_matrix(signal_table)
        report_summary = build_compound_report_summary(db)
    finally:
        db.close()

    molecular.to_csv(ARTIFACTS_DIR / "molecular_descriptor_matrix.csv")
    receptor_primary.to_csv(ARTIFACTS_DIR / "receptor_phenotype_matrix_primary.csv")
    receptor_all_confidence.to_csv(ARTIFACTS_DIR / "receptor_phenotype_matrix_all_confidence.csv")
    signal_table.to_csv(ARTIFACTS_DIR / "safety_signal_table_long.csv", index=False)
    safety_matrix.to_csv(ARTIFACTS_DIR / "safety_phenotype_matrix_logror.csv")
    report_summary.to_csv(ARTIFACTS_DIR / "compound_report_summary.csv")

    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": _code_version(),
        "min_compound_reports": MIN_COMPOUND_REPORTS,
        "min_cell_reports": MIN_CELL_REPORTS,
        "primary_confidence_threshold": PRIMARY_CONFIDENCE_THRESHOLD,
        "compounds": sorted(molecular.index.tolist()),
        "ae_categories": sorted(signal_table["category"].unique().tolist()),
        "receptor_matrix_primary_shape": list(receptor_primary.shape),
        "receptor_matrix_primary_nonnull_cells": int(receptor_primary.notna().sum().sum()),
        "safety_matrix_shape": list(safety_matrix.shape),
        "safety_matrix_nonnull_cells": int(safety_matrix.notna().sum().sum()),
        "compounds_meeting_minimum_reports": sorted(
            report_summary[report_summary["total_reports"] >= MIN_COMPOUND_REPORTS].index.tolist()
        ),
    }
    with (ARTIFACTS_DIR / "dataset_manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Molecular descriptor matrix: {molecular.shape}")
    print(f"Receptor phenotype matrix (primary, confidence>={PRIMARY_CONFIDENCE_THRESHOLD}): {receptor_primary.shape}, "
          f"{receptor_primary.notna().sum().sum()} non-null cells")
    print(f"Safety phenotype matrix (logROR, wide): {safety_matrix.shape}, "
          f"{safety_matrix.notna().sum().sum()} non-null cells (sparse/below-threshold cells set to NaN)")
    print(f"Wrote artifacts + manifest to {ARTIFACTS_DIR}/")


if __name__ == "__main__":
    run()
