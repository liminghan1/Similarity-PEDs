"""Sensitivity 6: all-FAERS background for the safety phenotype (research/analysis_plan.md Sec.
24 / project brief Sec. 24). Previously hardcoded "not computable" in analysis/sensitivity.py,
documented as infeasible because this project's FAERS ingestion deliberately pulls only
cohort-relevant reports, not the full FAERS database -- see that module's prior note.

This module makes it computable without ingesting the full database: standard pharmacovigilance
2x2 table (compound D, AE category E), background = the entire FAERS database rather than just the
other 9 cohort compounds:

    a = reports of D with E
    b = reports of D without E          = N_D - a
    c = reports NOT of D with E         = N_E - a
    d = reports NOT of D without E      = N_total - N_D - N_E + a

N_D (per compound) and a (per compound x category) are queried LIVE against openFDA rather than
reused from this project's own ingested data, because testosterone's ingestion is deliberately
capped at 5,000 of its true 31,733 reports (pipelines/faers/README.md `MAX_REPORTS_PER_COMPOUND`)
-- reusing a capped a/N_D pair here would be internally consistent for testosterone alone but
inconsistent with a live N_E/N_total drawn from the full, uncapped database. Querying everything
live sidesteps the cap entirely and treats all 10 compounds uniformly.

All queries are count-only (limit=1, reading meta.results.total), never fetching or storing
individual reports: 10 compound totals + 11 category totals + 1 grand total + 10x11 combined
compound-x-category queries = 132 requests total, well within openFDA's keyless 1,000/day budget
(confirmed live: the unfiltered grand-total query alone returns ~20.7M reports across all of
FAERS, not just this cohort).

Usage:
    uv run python -m analysis.full_faers_background
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from analysis.phenotype_matrix import (
    MIN_CELL_REPORTS,
    MIN_COMPOUND_REPORTS,
    build_safety_phenotype_matrix,
    load_ae_category_map,
)
from backend.app.analytics.signals import compute_ror
from backend.app.db.session import SessionLocal
from backend.app.models import Compound
from pipelines.faers.client import OpenFdaClient
from pipelines.faers.ingest import build_openfda_query, build_search_terms

ARTIFACTS_DIR = Path("artifacts/matrices")


def _terms_by_category(category_map: dict[str, set[str]]) -> dict[str, list[str]]:
    """Reverses load_ae_category_map()'s term -> {categories} into category -> [terms], the
    representative reaction terms to OR together for one category's openFDA query."""
    by_category: dict[str, list[str]] = defaultdict(list)
    for term, categories in category_map.items():
        for category in categories:
            by_category[category].append(term)
    return dict(by_category)


def fetch_full_faers_counts(
    client: OpenFdaClient,
    drug_terms_by_compound: dict[str, list[str]],
    reaction_terms_by_category: dict[str, list[str]],
) -> dict:
    """All 132 live count-only queries. Returns raw counts as a JSON-serializable dict."""
    total = client.count("")

    n_d: dict[str, int] = {}
    for name, terms in drug_terms_by_compound.items():
        n_d[name] = client.count(build_openfda_query(terms))

    n_e: dict[str, int] = {}
    for category, terms in reaction_terms_by_category.items():
        quoted = " ".join(f'"{t}"' for t in terms)
        n_e[category] = client.count(f"patient.reaction.reactionmeddrapt:({quoted})")

    a: dict[str, dict[str, int]] = {}
    for name, drug_terms in drug_terms_by_compound.items():
        drug_query = build_openfda_query(drug_terms)
        a[name] = {}
        for category, reaction_terms in reaction_terms_by_category.items():
            quoted = " ".join(f'"{t}"' for t in reaction_terms)
            search = f"{drug_query} AND patient.reaction.reactionmeddrapt:({quoted})"
            a[name][category] = client.count(search)

    return {"total": total, "n_d": n_d, "n_e": n_e, "a": a}


def build_signal_table(counts: dict) -> pd.DataFrame:
    """Same columns as analysis/phenotype_matrix.py::compute_signal_table's output, so
    build_safety_phenotype_matrix() can consume it unmodified -- only the a/b/c/d source differs
    (live all-FAERS counts here, this project's own DB there)."""
    total = counts["total"]
    n_d = counts["n_d"]
    n_e = counts["n_e"]

    rows = []
    for name, per_category in counts["a"].items():
        n_total_compound = n_d[name]
        for category, a in per_category.items():
            n_event = n_e[category]
            b = n_total_compound - a
            c = n_event - a
            d = total - n_total_compound - n_event + a
            result = compute_ror(a, b, c, d)
            rows.append(
                {
                    "canonical_name": name,
                    "category": category,
                    "a": a, "b": b, "c": c, "d": d,
                    "total_compound_reports": n_total_compound,
                    "ror": result.ror,
                    "log_ror": result.log_ror,
                    "se_log_ror": result.se_log_ror,
                    "ci_low": result.ci_low,
                    "ci_high": result.ci_high,
                    "continuity_correction_applied": result.continuity_correction_applied,
                    "sparse_cell": a < MIN_CELL_REPORTS,
                    "compound_meets_minimum": n_total_compound >= MIN_COMPOUND_REPORTS,
                }
            )
    return pd.DataFrame(rows)


def run() -> None:
    db = SessionLocal()
    try:
        compound_ids_by_name = {c.canonical_name: c.id for c in db.query(Compound).all()}
        drug_terms_by_id = build_search_terms(db)
        category_map = load_ae_category_map()
    finally:
        db.close()

    drug_terms_by_compound = {
        name: drug_terms_by_id[cid] for name, cid in compound_ids_by_name.items()
    }
    reaction_terms_by_category = _terms_by_category(category_map)

    with OpenFdaClient(min_request_interval=0.5) as client:
        counts = fetch_full_faers_counts(client, drug_terms_by_compound, reaction_terms_by_category)

    with (ARTIFACTS_DIR / "full_faers_background_counts.json").open("w") as f:
        json.dump(counts, f, indent=2)

    signal_table = build_signal_table(counts)
    signal_table.to_csv(ARTIFACTS_DIR / "full_faers_background_signal_table.csv", index=False)

    matrix = build_safety_phenotype_matrix(signal_table)
    matrix.to_csv(ARTIFACTS_DIR / "full_faers_background_matrix.csv")

    cohort_relative = pd.read_csv(ARTIFACTS_DIR / "safety_signal_table_long.csv")
    merged = signal_table.merge(
        cohort_relative[["canonical_name", "category", "log_ror"]],
        on=["canonical_name", "category"],
        suffixes=("_full_faers", "_cohort_relative"),
    )
    correlation = merged["log_ror_full_faers"].corr(merged["log_ror_cohort_relative"])
    sign_agreement = (
        (merged["log_ror_full_faers"] > 0) == (merged["log_ror_cohort_relative"] > 0)
    ).mean()

    print(f"Total FAERS reports (live, all drugs): {counts['total']:,}")
    print(f"Wrote {ARTIFACTS_DIR / 'full_faers_background_matrix.csv'}")
    print(
        f"Pearson correlation between cohort-relative and full-FAERS-relative logROR "
        f"(n={len(merged)} shared compound x category cells): {correlation:.3f}"
    )
    print(f"Sign agreement (same direction of association): {sign_agreement:.1%}")


if __name__ == "__main__":
    run()
