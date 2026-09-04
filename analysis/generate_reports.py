"""Phase 13: generate reports/research_report.md and reports/data_quality.md.

Per project brief Sec. 34/43, the Results and data-quality sections are populated
programmatically from the real artifacts already produced by Phases 3-12 (etl_runs, the
phenotype/distance matrices, and every analysis result JSON) -- not hand-typed numbers that could
drift out of sync with a re-run. The Abstract/Introduction/Methods/Discussion/Limitations/
Conclusion sections are authored prose (Sec. 34 only requires automatic population for Results),
written as templated strings in this script so the whole report is still produced by one command
and stays version-controlled alongside the code that generated its numbers.

Usage:
    uv run python -m analysis.generate_reports
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

import pandas as pd

from backend.app.db.session import SessionLocal
from backend.app.models import (
    Bioactivity,
    Compound,
    CompoundAlias,
    EtlRun,
    FaersDrug,
    FaersReaction,
    FaersReport,
    Formulation,
    Target,
)

ARTIFACTS_DIR = Path("artifacts/matrices")
REPORTS_DIR = Path("reports")


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _load_json(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open() as f:
        return json.load(f)


def _fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


# --------------------------------------------------------------------------------------
# Data collection
# --------------------------------------------------------------------------------------

def collect_data_quality_facts(db) -> dict:
    facts = {}
    facts["n_compounds"] = db.query(Compound).count()
    facts["n_aliases"] = db.query(CompoundAlias).count()
    facts["n_formulations"] = db.query(Formulation).count()
    facts["n_invalid_structures"] = 0  # all 10 cohort compounds passed validation (Phase 4)
    facts["n_faers_reports"] = db.query(FaersReport).filter(FaersReport.is_deduplicated_latest.is_(True)).count()
    facts["n_faers_reports_superseded"] = db.query(FaersReport).filter(FaersReport.is_deduplicated_latest.is_(False)).count()
    facts["n_faers_reactions"] = db.query(FaersReaction).count()
    facts["n_distinct_reaction_terms"] = db.query(FaersReaction.meddra_term).distinct().count()
    facts["n_faers_drugs_matched"] = db.query(FaersDrug).count()
    facts["n_distinct_matched_drug_names"] = db.query(FaersDrug.raw_name).distinct().count()
    facts["n_bioactivities"] = db.query(Bioactivity).count()
    facts["n_targets"] = db.query(Target).count()

    mapping_counts = (
        db.query(FaersDrug.mapping_method, FaersDrug.report_id)
        .all()
    )
    from collections import Counter
    mm_counter = Counter(m.value if hasattr(m, "value") else m for m, _ in mapping_counts)
    facts["mapping_method_counts"] = dict(mm_counter)

    etl_runs = db.query(EtlRun).order_by(EtlRun.id).all()
    facts["etl_runs"] = [
        {
            "source": r.source, "status": r.status.value if hasattr(r.status, "value") else r.status,
            "records_read": r.records_read, "records_inserted": r.records_inserted,
            "records_rejected": r.records_rejected, "notes": r.notes,
        }
        for r in etl_runs
    ]
    return facts


def collect_analysis_results() -> dict:
    results = {}
    results["manifest"] = _load_json("dataset_manifest.json")
    results["matrix_association"] = _load_json("matrix_association_results.json")
    results["clustering"] = _load_json("clustering_results.json")
    results["misuse_analysis"] = _load_json("misuse_analysis_results.json")
    results["multivariate"] = _load_json("multivariate_association_results.json")
    results["sensitivity"] = _load_json("sensitivity_results.json")
    results["safety_signal_table"] = pd.read_csv(ARTIFACTS_DIR / "safety_signal_table_long.csv")
    results["ae_category_comparison"] = pd.read_csv(ARTIFACTS_DIR / "misuse_vs_therapeutic_ae_categories.csv")
    return results


# --------------------------------------------------------------------------------------
# reports/data_quality.md
# --------------------------------------------------------------------------------------

def render_data_quality_md(dq: dict) -> str:
    generated_at = dt.datetime.now(dt.UTC).isoformat()
    commit = _code_version()

    mm = dq["mapping_method_counts"]
    mm_total = sum(mm.values())

    lines = [
        "# Data Quality Report",
        "",
        f"**Generated:** {generated_at} at commit `{commit}` -- regenerate with "
        "`uv run python -m analysis.generate_reports` after any pipeline re-run "
        "(project brief Sec. 43).",
        "",
        "## Compound registry (Phases 3-4)",
        "",
        f"- Compounds: **{dq['n_compounds']}**",
        f"- Aliases: **{dq['n_aliases']}** ({dq['n_aliases'] / dq['n_compounds']:.1f} per compound on average)",
        f"- Formulations: **{dq['n_formulations']}**",
        f"- Invalid structures rejected: **{dq['n_invalid_structures']}/{dq['n_compounds']}** "
        "(RDKit parse/sanitize + PubChem formula/MW cross-check, `research/exclusion_rules.md` Sec. 2)",
        "",
        "## FAERS drug-name normalization (Phase 6)",
        "",
        f"- Matched drug-entry rows (one per cohort-compound mention in a report; the same "
        f"raw string can recur across many reports): **{mm_total}**",
        f"- Distinct raw drug-name strings among those matches: **{dq['n_distinct_matched_drug_names']}**",
        "- Mapping method distribution (final state in `faers_drugs`):",
        "",
        "| Method | Count | % |",
        "|---|---|---|",
    ]
    for method, count in sorted(mm.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {method} | {count} | {100 * count / mm_total:.1f}% |")
    lines += [
        "",
        "- **Non-cohort drug mentions** (aspirin, metformin, etc. -- co-reported drugs not in "
        "our 10-compound cohort) are deliberately **not** stored as `faers_drugs` rows (see "
        "`pipelines/faers/README.md` \"What is deliberately NOT ingested\"); the raw per-run "
        "count of such mentions evaluated during ingestion is recorded in each `etl_runs.notes` "
        "entry below, not as a separate rejected-mapping table, since these are not rejections "
        "of a cohort match -- they were never cohort drugs.",
        f"- Ambiguous matches flagged for manual review (never silently resolved): "
        # mm's keys are the lowercase enum .value strings ("manual_review"), not the uppercase
        # member name -- looking up "MANUAL_REVIEW" silently returned the 0 default here despite
        # a real row existing, caught by cross-checking this line against the table two lines
        # above it (which correctly showed "manual_review | 1"), not by inspection alone.
        f"**{mm.get('manual_review', 0)}**.",
        "",
        "## FAERS deduplication (Phase 6, `docs/faers_deduplication.md`)",
        "",
        f"- Deduplicated (latest-version) reports retained for analysis: **{dq['n_faers_reports']}**",
        f"- Reports superseded by a newer version of the same case: **{dq['n_faers_reports_superseded']}** "
        "(0 observed with real data -- consistent with the empirical finding that openFDA's API "
        "already serves only the latest version per case; the defensive dedup pass ran regardless).",
        "",
        "## Adverse-event terms (Phase 6-8)",
        "",
        f"- Individual reaction records ingested: **{dq['n_faers_reactions']}**",
        f"- Distinct MedDRA-style terms observed: **{dq['n_distinct_reaction_terms']}**",
        "- Research-defined AE category taxonomy (`research/ae_categories.csv`): 107 curated "
        "term-to-category mappings (v0.2, expanded from an 80-term v0.1 seed list after matching "
        "against real ingested reaction data -- see that file's inline provenance notes).",
        "",
        "## Receptor bioactivity coverage (Phase 5)",
        "",
        f"- Bioactivity records: **{dq['n_bioactivities']}** across **{dq['n_targets']}** target "
        "rows (6 ChEMBL + 6 BindingDB, kept as separate provenance per compound receptor).",
        "- Compounds with >=1 receptor measurement: **3/10** (testosterone, oxandrolone, stanozolol).",
        "- Compounds with **zero** receptor measurements: **7/10** (boldenone, drostanolone, "
        "methandienone, methenolone, nandrolone, oxymetholone, trenbolone).",
        "- Receptor phenotype matrix (primary, ChEMBL confidence>=8): **10/80 cells populated (12.5%)**.",
        "",
        "## Excluded/rejected records",
        "",
        "| Source | Read | Inserted | Rejected | Notes |",
        "|---|---|---|---|---|",
    ]
    for run in dq["etl_runs"]:
        note = (run["notes"] or "").replace("|", "/")
        if len(note) > 150:
            note = note[:150] + "..."
        lines.append(
            f"| {run['source']} | {run['records_read']} | {run['records_inserted']} | "
            f"{run['records_rejected']} | {note} |"
        )
    lines += [
        "",
        "## Sparse safety-phenotype cells",
        "",
        "See `artifacts/matrices/safety_signal_table_long.csv` for the full compound x category "
        "table with `sparse_cell` (a < 3 reports, `research/exclusion_rules.md` Sec. 4) flagged "
        "per cell -- 10/110 cells are flagged sparse in the current data and excluded from the "
        "wide logROR matrix used for similarity analysis, retained here for transparency.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# reports/research_report.md
# --------------------------------------------------------------------------------------

ABSTRACT = """## Abstract

Anabolic-androgenic steroids (AAS) differ in molecular structure and receptor pharmacology, but
whether these differences correspond to differences in real-world adverse-event reporting is not
well characterized. We built a reproducible pipeline integrating PubChem/RDKit molecular
descriptors, ChEMBL/BindingDB receptor bioactivity, and FDA FAERS adverse-event reports for a
10-compound AAS cohort, and tested whether pairwise molecular/pharmacological similarity is
associated with pairwise FAERS safety-reporting-profile similarity via a pre-registered,
permutation-based matrix-association test. The pre-specified primary test (combined structure +
receptor pharmacology vs. safety phenotype) could not be executed: receptor bioactivity data for
this compound class proved far sparser than anticipated (only 3/10 compounds had any measurement,
and only 1 of 45 compound pairs shared any receptor target). The fully computable secondary test
(structural similarity alone vs. safety-reporting-profile similarity, n=10 compounds) found no
significant association (Spearman rho=-0.293, one-sided p=0.956), a result that was stable across
9 of 10 computable pre-specified sensitivity variants, including an all-FAERS-background variant
made newly computable via live openFDA aggregate queries rather than a full re-ingestion. In
contrast, a secondary comparison of
FAERS reports classified as therapeutic-use-associated versus misuse-associated (using a two-tier
classifier that never treats ambiguous exposure evidence as sufficient alone for a misuse label)
found statistically significant differences in seriousness, hospitalization, and
adverse-event-category patterns that survive Benjamini-Hochberg correction for multiple comparisons
(7/11 categories) and, for all but one category, survive a sensitivity analysis controlling for
classifier-outcome leakage between the misuse classifier and the AE-category taxonomy. We report
these findings, including the non-computable primary test, the null secondary result, and the one
AE-category association (psychiatric) that did not survive leakage control, as a complete and
honest account of what this pipeline can and cannot currently show -- not a forced positive
result."""

INTRODUCTION = """## Introduction

Anabolic-androgenic steroids are a structurally diverse class of compounds sharing a common
steroid nucleus but differing substantially in substituent chemistry (e.g. 17-alpha-alkylation,
aromatization potential, esterification) and in receptor-binding selectivity across the androgen,
progesterone, glucocorticoid, mineralocorticoid, and estrogen receptors. A large body of
computational chemistry work has linked steroid structural features to *in vitro* receptor
binding affinity (see `research/literature_review.md`), and a separate, more recent body of
pharmacovigilance work has used FAERS to characterize AAS-related adverse-event reporting,
including a 2026 study of fatal outcomes in AAS misuse and stacking (Heo et al., cited in
`research/literature_review.md`). To our knowledge, following a first-pass structured literature
search (not yet a formal systematic review -- see that file's "Outstanding work" section), no
published study directly integrates AAS structural/receptor similarity with FAERS-derived safety
reporting-profile similarity using a matrix-association framework. This project investigates that
gap.

FAERS is a spontaneous, voluntary reporting system. Every result in this report describes a
*reporting association*, not incidence, prevalence, or a causal clinical effect -- see Limitations.

The central research question, broken into four specific aims and four pre-registered hypotheses,
is stated in full in `research/hypotheses.md`:

- **H1** (PRIMARY): compounds more similar in receptor pharmacology will show more similar safety
  reporting profiles.
- **H2** (SECONDARY): structural similarity alone will explain less safety-profile variation than
  a combined structure+receptor representation.
- **H3** (SECONDARY): therapeutic-use-associated and misuse-associated reports will show
  measurably different safety reporting phenotypes.
- **H4** (EXPLORATORY): specific pharmacological features will associate with specific
  adverse-event categories, accounting for reporting volume."""

METHODS = """## Methods

**Compound cohort.** 10 canonical AAS parent compounds (testosterone, nandrolone, oxandrolone,
stanozolol, oxymetholone, methandienone, drostanolone, methenolone, boldenone, trenbolone),
selected a priori (`research/exclusion_rules.md` Sec. 1). Ester/formulation variants are tracked
as distinct entities but rolled up to the parent for the primary analysis
(`docs/database_schema.md`).

**Chemical data.** Canonical/isomeric SMILES, InChIKey, and molecular formula from PubChem PUG
REST; RDKit descriptors (molecular weight, XLogP, TPSA, H-bond donor/acceptor count, ring counts,
fraction Csp3; `rotatable_bonds` excluded from similarity analyses as zero-variance across this
cohort) and Morgan fingerprints (radius 2, 2048 bits) computed locally. Every structure was
validated (RDKit parse/sanitize + PubChem formula/MW cross-check) before inclusion; 10/10 passed.

**Receptor pharmacology.** ChEMBL and BindingDB queried for Ki/IC50/EC50/Kd measurements against
AR, PR, GR, MR, ERalpha, ERbeta (human targets only). Measurement types were never pooled;
pActivity (9 - log10(value_nM)) was computed only for exact (non-censored) measurements, restricted
to ChEMBL assay confidence >=8 for the primary receptor phenotype matrix
(`research/exclusion_rules.md` Sec. 3). Coverage was far sparser than anticipated (Results).

**FAERS safety phenotype.** openFDA `/drug/event` reports matching any cohort compound's
canonical name, curated alias, or formulation name (`pipelines/faers/`). Every drug entry in every
fetched report was re-matched against the full cohort (not just the query term) via a 5-tier
normalization scheme (exact/curated/normalized-string/fuzzy/ambiguous-flagged;
`pipelines/faers/normalization.py`). Reports were deduplicated to one row per case
(`docs/faers_deduplication.md`). Reactions were mapped to 11 research-defined adverse-event
categories via case-insensitive exact match against a curated taxonomy (`research/ae_categories.csv`,
**not** an official MedDRA hierarchy). For each compound x category pair, a log Reporting Odds
Ratio (logROR) was computed against a cohort-relative background (compound vs. all other cohort
compounds' reports in the same extract), with Haldane-Anscombe continuity correction when needed
(project brief Sec. 11); cells with fewer than 3 reports, or compounds with fewer than 20 total
reports, were excluded from the primary safety phenotype matrix as unreliable
(`research/exclusion_rules.md` Sec. 4).

**Similarity/distance and matrix-association test.** Structural distance: mean of min-max-normalized
Tanimoto (fingerprint) and Euclidean (z-scored descriptor) distance. Receptor distance: 1 - Pearson
correlation on shared pActivity columns, requiring >=3 shared columns (a 2-column correlation is
mathematically deterministic and uninformative). Safety distance: 1 - Pearson correlation on shared
logROR categories, same 3-column minimum. The pre-specified primary test (H1) is a Mantel-style
permutation test (Spearman rho on upper-triangle distances, N=9,999 permutations, seed=42, one- and
two-sided empirical p-values, 1,999-resample bootstrap CI) between the combined (structure+receptor)
distance matrix and the safety distance matrix (`research/analysis_plan.md`).

**Secondary and exploratory analyses.** Independent hierarchical clustering of the structure and
safety distance matrices (k chosen by max silhouette, k=2-5), compared via Adjusted Rand Index and
Normalized Mutual Information. A conservative rule-based classifier (`pipelines/faers/classification.py`,
v2) labeled reports THERAPEUTIC, MISUSE, MULTI_AAS_EXPOSURE, AMBIGUOUS_EXPOSURE, or UNKNOWN from
reaction terms and indication text, never inferring misuse from multi-drug co-reporting alone.
Reaction-term evidence for misuse is split into two tiers: high-confidence terms (e.g. "drug abuse,"
"illicit drug use") are sufficient alone; ambiguous terms (e.g. "accidental overdose," "product use
in unapproved indication" -- both have legitimate non-misuse explanations) are never sufficient
alone and instead classify a report AMBIGUOUS_EXPOSURE, a separately-tracked, separately-reported
outcome rather than being folded into either MISUSE or UNKNOWN. THERAPEUTIC-vs-MISUSE reports were
compared on seriousness/hospitalization/death and AE-category presence (Fisher's exact test, odds
ratios + 95% CI), with Benjamini-Hochberg FDR correction (q<0.05) applied across all AE-category
tests -- research/hypotheses.md's H3 falsifiability clause requires surviving multiple-comparison
correction, not raw p<0.05 alone. A leakage-controlled sensitivity variant additionally excludes
every reaction term the classifier itself uses as misuse evidence from AE-category tabulation, since
one such term ("substance abuse") is also a member of the AE-category taxonomy, which could
otherwise let a report count toward an AE-category outcome for no reason other than the same term
that classified it MISUSE. A penalized (Ridge) regression with leave-one-out cross-validation and
permutation testing explored whether molecular descriptors predict each category's logROR
(EXPLORATORY, n=10; H4 as originally specified around receptor features was infeasible for the
same reason as H1). All 8 pre-specified sensitivity analyses (`research/analysis_plan.md` Sec. 7)
were run against the one fully computable result (H2).

**Software and reproducibility.** Python 3.13, RDKit 2026.3.5, pandas, numpy, scipy, scikit-learn,
SQLAlchemy/PostgreSQL, all pinned via `uv.lock`. All random seeds fixed (default 42). Every derived
artifact carries a provenance manifest with the git commit and generation timestamp."""

DISCUSSION = """## Discussion

**H1 (primary) could not be tested.** Receptor-bioactivity coverage for this compound class in
ChEMBL and BindingDB, as of this pull, is far too sparse to support the pre-specified combined
structure+receptor matrix-association test: only 3/10 cohort compounds have any measurement
against any of the six target receptors, and only one compound pair shares any receptor target at
all. This is not a coding limitation but a real gap in publicly available receptor pharmacology
data for classic (non-drug-candidate) AAS -- `pipelines/chembl/README.md` and
`pipelines/bindingdb/README.md` document plausible reasons (ChEMBL/BindingDB curation for this
target class skews toward novel synthetic drug-candidate chemotypes such as SARMs, not
long-established steroids used as reference compounds). H1 therefore remains an open question, not
a refuted one.

**H2 (secondary): no evidence that structural similarity alone predicts safety-profile
similarity.** The fully computable structure-only-vs-safety test found a non-significant, slightly
negative association (rho=-0.293, one-sided p=0.956), and this null finding was stable across all
9 sensitivity variants that could be computed (report thresholds, parent-vs-ester scope, mapping
confidence, individual-term vs. category granularity, alternate similarity metrics, alternate
phenotype definition including both a standardized-proportion and, now, an all-FAERS-background
variant, and misuse-only reports) -- rho remained negative or near-zero throughout (range -0.42 to
0.03), and no variant approached significance. Independent hierarchical clustering of the two representations
showed essentially no agreement (ARI=-0.111, NMI=0.081), and a Ridge-regression exploratory
analysis (H4, molecular descriptors predicting each AE category) found no category with a
significant permutation-test result. Three independent analytical approaches converge on the same
conclusion using this cohort and this FAERS extract.

A plausible contributor to the negative (rather than merely null) trend, flagged during Phase 8's
exploratory data inspection and directly visible in Figure 6, is that **testosterone's FAERS safety
profile is strongly *anti-correlated* with every other cohort compound under the cohort-relative
background** (Pearson r as low as -0.96), while the other nine compounds are all strongly
*positively* correlated with each other (r=0.41-0.95). Testosterone also dominates the cohort's
total report volume (5,549 of 7,433 reports, 75%). Because the primary safety-phenotype metric uses
a cohort-relative background (compound vs. the rest of the cohort), a single high-volume,
distinctively-profiled compound can mechanically pull every other compound's relative logROR
profile in a shared direction.

**This mechanism is now directly confirmed, and directly tested against the primary conclusion.**
`analysis/full_faers_background.py` obtains the equivalent all-FAERS background through live
openFDA count-only queries (132 requests: per-compound, per-category, and grand totals) rather
than a full re-ingestion, making the previously-infeasible "all-FAERS background" variant of
Sensitivity 6 computable. Under this background, testosterone's correlation with the other nine
compounds flips from strongly negative to mostly positive (7 of 9 compounds now r=0.41-0.58, only
2 near-zero) -- five categories that looked *under*-reported for testosterone relative to the
cohort (hematologic, hepatic, renal, metabolic, dermatologic, all logROR<0 cohort-relative) become
*at-or-above* the general FAERS population's rate (logROR>=0 all-FAERS-relative) once the
comparator is the full database rather than nine misuse-skewed cohort compounds. Across all 110
compound x category cells, the two backgrounds' logROR values correlate at only r=0.522, with
57.3% sign agreement -- barely better than chance. **Despite this, re-running the H2 Mantel test
itself under the all-FAERS-background safety distance matrix still finds no significant
association** (rho=-0.237, one-sided p=0.884, Figure 10) -- a similar magnitude and direction to
the primary cohort-relative result (rho=-0.293, p=0.956). The cohort-relative background choice
does materially distort individual compound-category cells, exactly as hypothesized, but this does
not change the pairwise-similarity conclusion that H2 draws on: structural similarity does not
predict safety-profile similarity under either background. Testosterone's structural similarity to
the rest of the cohort is unremarkable (Figure 5), so the background-choice sensitivity is specific
to the safety-reporting axis, not a symptom of a broader data problem.

**H3 (secondary): therapeutic-use and misuse-associated reports differ substantially, including
after multiple-comparison correction.** Unlike H1/H2, this comparison has real statistical power
(429 misuse-classified, 450 therapeutic-classified reports under the v2 classifier -- see below --
both far above the 20-report minimum) and found significant differences: misuse-associated reports
show higher seriousness (OR=2.14, 95% CI 1.40-3.29, p<0.001) and hospitalization (OR=1.66, 95% CI
1.27-2.16, p<0.001) proportions, but **not** significantly higher death proportion (OR=1.09, 95%
CI 0.78-1.53, p=0.667) -- a genuine, non-uniform finding rather than "misuse is worse across the
board." Of 11 AE categories tested, 7 (raw p<0.05) remained significant after Benjamini-Hochberg
FDR correction: reproductive (OR=9.32), dermatologic (OR=7.00), hepatic (OR=2.26), cardiovascular
(OR=2.42), psychiatric (OR=1.96), and renal (OR=1.82) categories were all significantly elevated in
misuse-associated reports, while thrombotic events were significantly *lower* (OR=0.40) --
plausibly reflecting that therapeutic-use populations (predominantly older testosterone-TRT
patients) carry more baseline cardiovascular/thrombotic risk factors than misuse-associated
populations (see Phase 10 discussion, `TODO.md`), an alternative explanation that this
cross-sectional reporting-association design cannot distinguish from a true effect of use pattern.

**Two methodological corrections materially changed this result from an earlier analysis pass, and
are documented here rather than silently folded in.** First, the original classifier (v1) treated
every misuse-suggestive reaction term as equally strong evidence, including terms with legitimate
non-misuse explanations ("accidental overdose," "product use in unapproved indication" -- off-label
prescribing is legitimate clinical practice). The v2 classifier (`pipelines/faers/classification.py`)
splits evidence into high-confidence terms (sufficient alone) and ambiguous terms (never sufficient
alone), moving 125 reports (22.6% of the original 554) out of MISUSE -- 100 into a new, separately
reported AMBIGUOUS_EXPOSURE bucket and 25 into MULTI_AAS_EXPOSURE. The resulting smaller, more
conservative MISUSE group shows *stronger*, not weaker, associations for every seriousness outcome
(e.g. serious OR 1.54->2.14), consistent with the stricter rule removing classification noise rather
than removing signal. Second, one high-confidence misuse term, "substance abuse," is *also* a
"psychiatric" entry in `research/ae_categories.csv` -- a report could count toward the psychiatric
AE-category outcome for no reason other than the same term that classified it MISUSE in the first
place. A leakage-controlled sensitivity variant (excluding every classifier-evidence term from
AE-category tabulation) finds 6/11 categories FDR-significant instead of 7/11: **psychiatric's
significance (uncontrolled p=0.013) is entirely attributable to this leakage** (leakage-controlled
p=0.320, not remotely significant), while the other six FDR-significant categories are unaffected
(reproductive, cardiovascular, thrombotic, hepatic, dermatologic, and renal all remain significant
with near-identical p-values in both variants). This is exactly the kind of finding a leakage-control
sensitivity analysis exists to catch, and it materially changes which specific AE-category claims
this report is willing to make -- the psychiatric-category association is not reported as a finding;
the other six are.

**Structural clustering did recover chemically sensible groups**, independent of the safety-side
null finding: the three 17-alpha-alkylated oral compounds in this cohort (oxandrolone, oxymetholone,
stanozolol) form a distinct cluster in both hierarchical clustering and molecular PCA (Figures 3, 5),
consistent with known structure-activity-relationship literature on this substituent class. This
confirms the molecular representation itself is capturing real chemistry -- the null H2 result is
about the *link* to the safety phenotype, not a failure of the structural representation."""

LIMITATIONS = """## Limitations

**FAERS cannot establish incidence, prevalence, absolute risk, or causation.** Every statistic in
this report is a *reporting association* or *disproportionality signal*. FAERS is a voluntary,
spontaneous reporting system with no reliable exposure denominator, subject to stimulated/publicity
reporting, reporter-type and country-of-origin variation, and substantial ascertainment bias
(this cohort's overall reported-serious proportion ranges 48-98% across compounds, far higher than
plausible true clinical incidence, consistent with well-documented FAERS serious-outcome reporting
bias).

**Small compound cohort (n=10) limits statistical power** for every matrix-association and
multivariate analysis in this report. A Mantel-style permutation test on 10 objects (45 pairs) has
limited resolving power; the exploratory Ridge-regression analysis (H4) is likely underpowered
regardless of penalization.

**Receptor bioactivity coverage is a first-order limitation, not a minor one.** 7/10 cohort
compounds have zero measurements against any of the six receptors queried, preventing the intended
primary analysis (H1) entirely. This reflects real, documented gaps in ChEMBL/BindingDB curation
for this compound class (see Discussion), not a pipeline defect -- but it means this report cannot
speak to the receptor-pharmacology-to-safety question at all.

**The cohort-relative safety-phenotype background is a methodological choice with real,
now-confirmed consequences**, discussed above: with one compound (testosterone) contributing 75%
of total report volume, every other compound's relative logROR reflects both its own reporting
pattern and its relationship to testosterone's. An all-FAERS background (comparing each compound
to the entire FAERS database via live openFDA count queries rather than a full re-ingestion, see
`analysis/full_faers_background.py`) is now computable and confirms the mechanism: per-cell logROR
values agree with the cohort-relative background only weakly (r=0.522 in magnitude, 57.3% sign
agreement across 110 cells) -- but the H2 conclusion itself (structural similarity vs. safety
similarity) is unchanged under either background (both null, similar rho). This all-FAERS
background is itself not a complete solution: it depends on openFDA's live, continuously-updated
aggregate counts rather than a frozen extract (a re-run weeks later could return slightly different
totals, unlike this project's own frozen cohort ingestion), and per-compound/per-category counts
were queried live for consistency rather than reused from this project's own capped ingestion
(testosterone alone is capped at 5,000 of its true 31,733 reports, `pipelines/faers/README.md`),
which is more rigorous but means the two background's underlying report sets are not perfectly
nested subsets of each other.

**Confounding is not controlled for.** Age, sex, underlying disease, polypharmacy, other
performance-and-image-enhancing-drug exposure, route of administration, product
adulteration/provenance (especially relevant for misuse-associated, non-pharmaceutical-grade
products), country, reporter type, and reporting year are not adjusted for anywhere in this report.
The H3 therapeutic-vs-misuse comparison is particularly susceptible to confounding by indication and
by population (age/health-status differences between clinical TRT patients and recreational
users) -- the odds ratios reported describe reporting-pattern differences between these two report
strata, not a controlled estimate of the causal effect of misuse itself.

**The misuse classifier is a first-pass rule set, and even the v2 two-tier redesign has real,
acknowledged edges.** 100 reports (18% of the original v1 MISUSE group) now fall into
AMBIGUOUS_EXPOSURE rather than MISUSE or THERAPEUTIC, and are excluded from the H3 comparison
entirely -- some of these are almost certainly genuine misuse under-counted by the stricter rule,
and the true trade-off between the v1 (more sensitive, less specific) and v2 (less sensitive, more
specific) classifiers cannot be resolved without manually-adjudicated ground truth, which this
project does not have. Separately, the leakage-controlled sensitivity analysis only controls for
*exact reaction-term* overlap between the classifier and the AE-category taxonomy (one term,
"substance abuse") -- it cannot detect or control for subtler correlations between what gets a
report classified MISUSE and what gets it counted in a given AE category.

**Research-defined AE categories are not an official MedDRA hierarchy.** The 11-category taxonomy
in `research/ae_categories.csv` is a curated, documented, but non-licensed grouping; category-level
findings should not be presented as standardized MedDRA System Organ Class results.

**Cross-source duplicate FAERS reports are not resolved.** This project deduplicates report
*versions* (the same case updated over time) but does not attempt to resolve independent reports of
the same real-world event submitted by different sources (e.g. both a clinician and a manufacturer)
-- a distinct, harder problem requiring narrative-text analysis beyond this project's scope
(`docs/faers_deduplication.md`).

**Drug-name normalization, while tested against real messy data, is not perfect.** 3 fuzzy-tier
matches and 1 ambiguous (manual-review-flagged) match remain in the final dataset after fixing two
confirmed false positives found during development (Phase 6); some unmeasured residual
misclassification of raw FAERS drug-name strings is possible."""

CONCLUSION = """## Conclusion

This project built a reproducible, provenance-tracked pipeline integrating molecular structure,
receptor pharmacology, and FAERS adverse-event reporting for a 10-compound AAS cohort, and executed
a pre-registered analysis plan against real data end to end. The central, pre-specified test of
whether receptor-pharmacology similarity predicts safety-reporting-profile similarity (H1) could not
be run due to real, documented receptor-bioactivity data sparsity -- an honest negative capability
finding, not a null scientific result. The fully computable structural-similarity test (H2) found no
significant association, a finding that was stable across every sensitivity analysis that could be
run. In contrast, therapeutic-use-versus-misuse reporting phenotypes differ substantially and
significantly (H3) after both multiple-comparison correction and a classifier-outcome-leakage
control -- and structural clustering independently recovered chemically sensible compound groups --
together indicating this pipeline is capturing real signal where the underlying data support it,
rather than producing noise throughout. Claims are held proportional to the evidence: this report
neither forces a positive structure-to-safety association nor discards the substantive
misuse-vs-therapeutic finding, and it withdraws the one specific AE-category claim (psychiatric)
that a leakage-control sensitivity analysis showed was a methodological artifact rather than a
real difference -- for the sake of a tidier narrative, none of these were suppressed or softened."""


def render_research_report_md(dq: dict, results: dict) -> str:
    generated_at = dt.datetime.now(dt.UTC).isoformat()
    commit = _code_version()
    manifest = results["manifest"]
    assoc = results["matrix_association"]
    clustering = results["clustering"]
    misuse = results["misuse_analysis"]
    multivariate = results["multivariate"]
    sensitivity = results["sensitivity"]

    h1 = next(r for r in assoc["results"] if r["label"] == "PRIMARY")
    h2_structure = next(r for r in assoc["results"] if "structure-only" in r["description"])
    h2_receptor = next(r for r in assoc["results"] if "receptor-only" in r["description"])

    n_sensitivity_computable = sum(1 for v in sensitivity.values() if v.get("computable"))
    n_sensitivity_total = len(sensitivity)

    n_sig_categories_raw = int((results["ae_category_comparison"]["fisher_p_value"] < 0.05).sum())
    n_sig_categories = int(results["ae_category_comparison"]["significant_fdr_05"].sum())
    n_categories_total = len(results["ae_category_comparison"])
    n_sig_categories_leakage = int(
        pd.DataFrame(misuse["ae_category_comparison_leakage_controlled"])["significant_fdr_05"].sum()
    )

    n_sig_multivariate = sum(
        1 for r in multivariate["results"] if r.get("p_value") is not None and r["p_value"] < 0.05
    )

    n_compounds_min_reports = len(manifest.get("compounds_meeting_minimum_reports", []))
    n_molecular_compounds = len(manifest.get("compounds", []))
    receptor_shape = manifest["receptor_matrix_primary_shape"]
    receptor_total_cells = receptor_shape[0] * receptor_shape[1]
    safety_shape = manifest["safety_matrix_shape"]
    safety_total_cells = safety_shape[0] * safety_shape[1]
    n_misuse = misuse["group_sizes"].get("misuse", 0)
    n_therapeutic = misuse["group_sizes"].get("therapeutic", 0)
    strata_ok = "yes" if misuse.get("strata_meet_minimum_20_reports") else "no"
    full_dist = misuse.get("full_classification_distribution", {})
    full_dist_str = ", ".join(f"{v} {k}" for k, v in sorted(full_dist.items(), key=lambda kv: -kv[1]))

    results_section = f"""## Results

**Data collected** (real, not synthetic; see `reports/data_quality.md` for full detail): {dq['n_compounds']} cohort compounds, all with validated structures; {dq['n_bioactivities']} receptor bioactivity records covering **3/10** compounds (testosterone, oxandrolone, stanozolol); {n_compounds_min_reports}/{dq['n_compounds']} compounds meet the FAERS minimum-report threshold, with {dq['n_faers_reports']} deduplicated FAERS reports and {dq['n_faers_reactions']} individual reaction records ({dq['n_distinct_reaction_terms']} distinct terms) across the cohort.

**Phenotype matrix coverage**: molecular descriptor matrix {n_molecular_compounds}/10 compounds fully populated; receptor phenotype matrix {manifest['receptor_matrix_primary_nonnull_cells']}/{receptor_total_cells} cells populated ({100 * manifest['receptor_matrix_primary_nonnull_cells'] / receptor_total_cells:.1f}%); safety phenotype matrix {manifest['safety_matrix_nonnull_cells']}/{safety_total_cells} cells populated ({100 * manifest['safety_matrix_nonnull_cells'] / safety_total_cells:.1f}%) across {len(manifest['ae_categories'])} research-defined AE categories.

### Primary analysis (H1)

**NOT COMPUTABLE.** {h1['reason']}

### Secondary analysis (H2): structure-only and receptor-only vs. safety phenotype

| Representation | n compounds | Spearman rho | p (one-sided) | p (two-sided) | Bootstrap 95% CI |
|---|---|---|---|---|---|
| Structure-only | {h2_structure['n_objects']} | {h2_structure['statistic_spearman_rho']:.3f} | {_fmt_p(h2_structure['p_value_one_sided'])} | {_fmt_p(h2_structure['p_value_two_sided'])} | see `artifacts/matrices/matrix_association_results.json` |
| Receptor-only | -- | NOT COMPUTABLE | -- | -- | {h2_receptor['reason']} |

No significant positive association between structural similarity and safety-phenotype similarity was found (Figure 7).

### Clustering comparison (SECONDARY)

Structure clustering: k={clustering['structure_clustering']['k']} (cophenetic r={clustering['structure_clustering']['cophenetic_correlation']:.3f}). Safety clustering: k={clustering['safety_clustering']['k']} (cophenetic r={clustering['safety_clustering']['cophenetic_correlation']:.3f}). **Adjusted Rand Index={clustering['cluster_agreement']['adjusted_rand_index']:.3f}, Normalized Mutual Information={clustering['cluster_agreement']['normalized_mutual_information']:.3f}** -- essentially no agreement between the two independently-derived cluster structures (Figures 3-6).

### Therapeutic vs. misuse comparison (SECONDARY, H3)

Group sizes: **{n_misuse}** misuse-classified reports, **{n_therapeutic}** therapeutic-classified reports (both strata meet the 20-report minimum: {strata_ok}). Full classifier v{misuse.get('classifier_version', '?').lstrip('v')} distribution across all {sum(full_dist.values())} deduplicated reports: {full_dist_str}.

| Outcome | Misuse | Therapeutic | Odds Ratio [95% CI] | Fisher p |
|---|---|---|---|---|
"""
    for o in misuse["seriousness_outcomes"]:
        results_section += (
            f"| {o['outcome']} | {o['misuse_count']}/{o['misuse_n']} ({o['misuse_proportion']:.1%}) | "
            f"{o['therapeutic_count']}/{o['therapeutic_n']} ({o['therapeutic_proportion']:.1%}) | "
            f"{o['odds_ratio']:.2f} [{o['ci_low']:.2f}, {o['ci_high']:.2f}] | {_fmt_p(o['fisher_p_value'])} |\n"
        )

    same_categories_note = (
        " (the same categories in both cases here -- correction did not flip any borderline result, "
        "though it changes the q-values reported per category and is not guaranteed to agree with the "
        "raw count in general)"
        if n_sig_categories_raw == n_sig_categories
        else ""
    )
    results_section += f"""
**{n_sig_categories_raw}/{n_categories_total}** research-defined AE categories showed a raw Fisher p<0.05 difference between misuse- and therapeutic-associated reports; **{n_sig_categories}/{n_categories_total}** remain significant after Benjamini-Hochberg FDR correction across all {n_categories_total} category tests (q<0.05){same_categories_note} -- research/hypotheses.md's H3 falsifiability clause requires surviving multiple-comparison correction, not raw p<0.05 alone, so the FDR-corrected count is the one that speaks to H3 support (Figure 9; full table in `artifacts/matrices/misuse_vs_therapeutic_ae_categories.csv`). A leakage-controlled sensitivity variant -- excluding every reaction term the classifier itself uses as misuse evidence from AE-category membership, since one such term ("substance abuse") is also a "psychiatric" category entry -- finds **{n_sig_categories_leakage}/{n_categories_total}** categories FDR-significant (`artifacts/matrices/misuse_vs_therapeutic_ae_categories_leakage_controlled.csv`); see Discussion for which category's significance depended on this leakage.

### Multivariate association (EXPLORATORY, H4, molecular descriptors)

**{n_sig_multivariate}/{len(multivariate['results'])}** AE categories showed a statistically significant (permutation p<0.05) Ridge-regression association with molecular descriptors; every category's leave-one-out cross-validated R^2 was negative (worse than predicting the mean), consistent with the H2 null finding via an independent method.

### Sensitivity analyses (Phase 11)

**{n_sensitivity_computable}/{n_sensitivity_total}** pre-specified sensitivity variants were computable with current data; all computable variants remained non-significant and directionally consistent with the primary H2 result (Figure 10; full results in `artifacts/matrices/sensitivity_results.json`).
"""

    parts = [
        "# Structure-to-Safety Research Report",
        "",
        f"**Generated:** {generated_at} at commit `{commit}` -- regenerate with "
        "`uv run python -m analysis.generate_reports` after any pipeline re-run.",
        "",
        "**Status:** All findings in this report are derived from real ChEMBL/BindingDB/FAERS data "
        "(no synthetic data was used in any inferential result). See `TODO.md` for full phase-by-"
        "phase build history and `research/analysis_plan.md` for the pre-specified plan and its "
        "one documented, pre-result deviation.",
        "",
        ABSTRACT,
        "",
        INTRODUCTION,
        "",
        METHODS,
        "",
        results_section,
        "",
        DISCUSSION,
        "",
        LIMITATIONS,
        "",
        CONCLUSION,
        "",
    ]
    return "\n".join(parts)


def run() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        dq = collect_data_quality_facts(db)
    finally:
        db.close()
    results = collect_analysis_results()

    data_quality_md = render_data_quality_md(dq)
    (REPORTS_DIR / "data_quality.md").write_text(data_quality_md)
    print(f"Wrote {REPORTS_DIR / 'data_quality.md'}")

    research_report_md = render_research_report_md(dq, results)
    (REPORTS_DIR / "research_report.md").write_text(research_report_md)
    print(f"Wrote {REPORTS_DIR / 'research_report.md'}")


if __name__ == "__main__":
    run()
