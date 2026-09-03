"""Phase 10 (SECONDARY, H3): therapeutic-use-vs-misuse report comparison (project brief Sec. 22).

Compares reports classified THERAPEUTIC vs. MISUSE (pipelines/faers/classification.py) on:
seriousness/hospitalization/death proportions, research-defined AE category presence rates, and
available demographics (age, sex) -- with odds ratios + 95% CI (not p-values alone, per Sec. 22).

Scope: MULTI_AAS_EXPOSURE and UNKNOWN reports are excluded from this comparison -- H3 is
specifically about therapeutic-use vs. misuse-associated phenotypes, and mixing in the structurally
different "multiple AAS co-reported, no other evidence" category or the large uninformative
UNKNOWN pool would blur that specific contrast (this mirrors research/exclusion_rules.md Sec. 6:
a stratum needs >=20 classified reports; both THERAPEUTIC (450) and MISUSE (554) clear this by a
wide margin with real data).

Odds ratios reuse backend/app/analytics/signals.compute_ror directly: an odds ratio computed from
a 2x2 table is the same statistic regardless of whether the "exposure" axis is drug-vs-other-drugs
(pharmacovigilance ROR) or misuse-vs-therapeutic (this analysis) -- the formula does not change,
only the interpretation label does, so re-deriving it here would just be duplicated, untested code.

Statistical test: Fisher's exact test (scipy), which is valid regardless of expected cell counts
and therefore preferred over chi-square for the smaller AE-category strata (Sec. 22: "chi-square/
Fisher tests where appropriate").

Usage:
    uv run python -m analysis.misuse_analysis
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

from analysis.phenotype_matrix import load_ae_category_map
from backend.app.analytics.signals import compute_ror
from backend.app.db.session import SessionLocal
from backend.app.models import FaersDrug, FaersReaction, FaersReport, ReportClassification
from backend.app.models.faers import UseClassification

ARTIFACTS_DIR = Path("artifacts/matrices")
COMPARISON_GROUPS = (UseClassification.THERAPEUTIC, UseClassification.MISUSE)
MIN_STRATUM_REPORTS = 20  # research/exclusion_rules.md Sec. 6


def load_group_report_table(db) -> pd.DataFrame:
    """One row per classified (THERAPEUTIC or MISUSE) report: group label, seriousness flags,
    age, sex."""
    rows = (
        db.query(
            FaersReport.id,
            ReportClassification.use_classification,
            FaersReport.serious,
            FaersReport.seriousness_hospitalization,
            FaersReport.seriousness_death,
            FaersReport.age,
            FaersReport.sex,
        )
        .join(ReportClassification, ReportClassification.report_id == FaersReport.id)
        .filter(
            FaersReport.is_deduplicated_latest.is_(True),
            ReportClassification.use_classification.in_(COMPARISON_GROUPS),
        )
        .all()
    )
    df = pd.DataFrame(
        rows, columns=["report_id", "group", "serious", "hospitalization", "death", "age", "sex"]
    )
    # Store the plain enum .value ("misuse"/"therapeutic"), not the UseClassification member
    # itself: pandas' string-dtype inference calls str() on column elements, and Enum.__str__
    # for a `class Foo(str, Enum)` mixin returns "Foo.MEMBER" (e.g. "UseClassification.MISUSE"),
    # not the underlying string value -- even though the member IS equal to its value under `==`.
    # Left as enum objects, every group-equality filter below would silently match zero rows.
    # Found via test_misuse_analysis.py failing with misuse_n=0 against a fixture that clearly
    # had 6 misuse rows, not by inspection.
    df["group"] = df["group"].apply(lambda g: g.value if isinstance(g, UseClassification) else g)
    # FaersReport.age is a Postgres NUMERIC column; psycopg returns it as Decimal, not float.
    # scipy's mannwhitneyu (via np.isnan) cannot operate on an object-dtype array of Decimals --
    # found running this against the real database, not in tests using plain-float fixtures.
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    return df


def load_report_categories(db, category_map: dict[str, set[str]]) -> pd.DataFrame:
    rows = db.query(FaersReaction.report_id, FaersReaction.meddra_term).all()
    pairs = set()
    for report_id, term in rows:
        for category in category_map.get(term.strip().lower(), ()):
            pairs.add((report_id, category))
    return pd.DataFrame(sorted(pairs), columns=["report_id", "category"])


def compare_binary_outcome(df: pd.DataFrame, outcome_col: str) -> dict:
    """2x2: rows=group (MISUSE vs THERAPEUTIC), cols=outcome present/absent. Odds ratio compares
    MISUSE to THERAPEUTIC (OR > 1 => higher odds of the outcome in misuse-associated reports)."""
    misuse = df[df["group"] == UseClassification.MISUSE.value]
    therapeutic = df[df["group"] == UseClassification.THERAPEUTIC.value]
    a = int(misuse[outcome_col].sum())
    b = int((~misuse[outcome_col].astype(bool)).sum())
    c = int(therapeutic[outcome_col].sum())
    d = int((~therapeutic[outcome_col].astype(bool)).sum())

    ror = compute_ror(a, b, c, d)
    _, fisher_p = fisher_exact([[a, b], [c, d]])
    return {
        "outcome": outcome_col,
        "misuse_n": len(misuse), "therapeutic_n": len(therapeutic),
        "misuse_count": a, "misuse_proportion": a / len(misuse) if len(misuse) else float("nan"),
        "therapeutic_count": c, "therapeutic_proportion": c / len(therapeutic) if len(therapeutic) else float("nan"),
        "odds_ratio": ror.ror, "ci_low": ror.ci_low, "ci_high": ror.ci_high,
        "fisher_p_value": float(fisher_p),
    }


def compare_ae_categories(df: pd.DataFrame, report_categories: pd.DataFrame, categories: list[str]) -> pd.DataFrame:
    misuse_ids = set(df[df["group"] == UseClassification.MISUSE.value]["report_id"])
    therapeutic_ids = set(df[df["group"] == UseClassification.THERAPEUTIC.value]["report_id"])
    cats_by_report: dict[str, set[int]] = {
        cat: set(g["report_id"]) for cat, g in report_categories.groupby("category")
    }

    rows = []
    for category in categories:
        cat_reports = cats_by_report.get(category, set())
        a = len(misuse_ids & cat_reports)
        b = len(misuse_ids) - a
        c = len(therapeutic_ids & cat_reports)
        d = len(therapeutic_ids) - c
        ror = compute_ror(a, b, c, d)
        _, fisher_p = fisher_exact([[a, b], [c, d]])
        rows.append(
            {
                "category": category,
                "misuse_count": a, "misuse_n": len(misuse_ids),
                "therapeutic_count": c, "therapeutic_n": len(therapeutic_ids),
                "odds_ratio": ror.ror, "ci_low": ror.ci_low, "ci_high": ror.ci_high,
                "fisher_p_value": float(fisher_p),
            }
        )
    return pd.DataFrame(rows).sort_values("fisher_p_value")


def compare_demographics(df: pd.DataFrame) -> dict:
    misuse_age = df[(df["group"] == UseClassification.MISUSE.value) & df["age"].notna()]["age"]
    therapeutic_age = df[(df["group"] == UseClassification.THERAPEUTIC.value) & df["age"].notna()]["age"]

    age_result: dict = {
        "misuse_n_with_age": len(misuse_age), "therapeutic_n_with_age": len(therapeutic_age),
        "misuse_median_age": float(misuse_age.median()) if len(misuse_age) else None,
        "therapeutic_median_age": float(therapeutic_age.median()) if len(therapeutic_age) else None,
    }
    if len(misuse_age) >= 5 and len(therapeutic_age) >= 5:
        _, p = mannwhitneyu(misuse_age, therapeutic_age)
        age_result["mannwhitney_p_value"] = float(p)
    else:
        age_result["mannwhitney_p_value"] = None
        age_result["note"] = "insufficient n with recorded age for a formal test"

    sex_counts = df[df["sex"].notna()].groupby(["group", "sex"]).size().unstack(fill_value=0)
    sex_result = {"table": sex_counts.to_dict()} if not sex_counts.empty else {"table": {}}
    if sex_counts.shape == (2, 2):
        _, sex_p = fisher_exact(sex_counts.values)
        sex_result["fisher_p_value"] = float(sex_p)

    return {"age": age_result, "sex": sex_result}


def run() -> None:
    db = SessionLocal()
    try:
        df = load_group_report_table(db)
        category_map = load_ae_category_map()
        report_categories = load_report_categories(db, category_map)
    finally:
        db.close()

    categories = sorted({c for cats in category_map.values() for c in cats})
    group_sizes = df["group"].value_counts().to_dict()

    outcomes = [compare_binary_outcome(df, col) for col in ("serious", "hospitalization", "death")]
    category_table = compare_ae_categories(df, report_categories, categories)
    demographics = compare_demographics(df)

    strata_meet_minimum = all(n >= MIN_STRATUM_REPORTS for n in group_sizes.values())

    result = {
        "label": "SECONDARY (H3: therapeutic vs. misuse comparison)",
        "group_sizes": {str(k): int(v) for k, v in group_sizes.items()},
        "strata_meet_minimum_20_reports": strata_meet_minimum,
        "seriousness_outcomes": outcomes,
        "ae_category_comparison": category_table.to_dict(orient="records"),
        "demographics": demographics,
    }
    with (ARTIFACTS_DIR / "misuse_analysis_results.json").open("w") as f:
        json.dump(result, f, indent=2, default=str)
    category_table.to_csv(ARTIFACTS_DIR / "misuse_vs_therapeutic_ae_categories.csv", index=False)

    print(f"Group sizes: {result['group_sizes']} (both >= {MIN_STRATUM_REPORTS}: {strata_meet_minimum})")
    print("\nSeriousness outcomes (misuse vs. therapeutic):")
    for o in outcomes:
        print(
            f"  {o['outcome']}: misuse {o['misuse_count']}/{o['misuse_n']} "
            f"({o['misuse_proportion']:.1%}) vs. therapeutic {o['therapeutic_count']}/{o['therapeutic_n']} "
            f"({o['therapeutic_proportion']:.1%}) -- OR={o['odds_ratio']:.2f} "
            f"[{o['ci_low']:.2f}, {o['ci_high']:.2f}], Fisher p={o['fisher_p_value']:.4g}"
        )
    print("\nTop AE category differences (by Fisher p-value):")
    print(category_table.head(5).to_string(index=False))
    print(f"\nWrote {ARTIFACTS_DIR / 'misuse_analysis_results.json'}")


if __name__ == "__main__":
    run()
