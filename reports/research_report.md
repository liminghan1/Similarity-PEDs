# Structure-to-Safety Research Report

**Generated:** 2026-09-04T01:18:28.074502+00:00 at commit `04a1741` -- regenerate with `uv run python -m analysis.generate_reports` after any pipeline re-run.

**Status:** All findings in this report are derived from real ChEMBL/BindingDB/FAERS data (no synthetic data was used in any inferential result). See `TODO.md` for full phase-by-phase build history and `research/analysis_plan.md` for the pre-specified plan and its one documented, pre-result deviation.

## Abstract

Anabolic-androgenic steroids (AAS) differ in molecular structure and receptor pharmacology, but
whether these differences correspond to differences in real-world adverse-event reporting is not
well characterized. We built a reproducible pipeline integrating PubChem/RDKit molecular
descriptors, ChEMBL/BindingDB receptor bioactivity, and FDA FAERS adverse-event reports for a
10-compound AAS cohort, and tested whether pairwise molecular/pharmacological similarity is
associated with pairwise FAERS safety-reporting-profile similarity via a pre-registered,
permutation-based matrix-association test. The pre-specified primary test (receptor pharmacology
alone vs. safety phenotype) could not be executed, and neither could the related secondary test of
whether adding receptor pharmacology to structure explains more than structure alone: receptor
bioactivity data for this compound class proved far sparser than anticipated (only 3/10 compounds
had any measurement, and only 1 of 45 compound pairs shared any receptor target). The fully
computable secondary test (structural similarity alone vs. safety-reporting-profile similarity,
n=10 compounds) found no significant association (Spearman rho=-0.293, one-sided p=0.956), a
result that was stable across 9 of 10 computable pre-specified sensitivity variants, including an
all-FAERS-background variant made newly computable via live openFDA aggregate queries rather than
a full re-ingestion. In contrast, a secondary comparison of
FAERS reports classified as therapeutic-use-associated versus misuse-associated (using a two-tier
classifier that never treats ambiguous exposure evidence as sufficient alone for a misuse label)
found statistically significant differences in seriousness, hospitalization, and
adverse-event-category patterns that survive Benjamini-Hochberg correction for multiple comparisons
(7/11 categories) and, for all but one category, survive a sensitivity analysis controlling for
classifier-outcome leakage between the misuse classifier and the AE-category taxonomy. We report
these findings, including the non-computable primary test, the null secondary result, and the one
AE-category association (psychiatric) that did not survive leakage control, as a complete and
honest account of what this pipeline can and cannot currently show -- not a forced positive
result.

## Introduction

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

The central research question, broken into four specific aims and five pre-registered hypotheses
(H2 split into H2a/H2b, 2026-09-04 -- see `research/hypotheses.md`'s Amendment log), is stated in
full in that file:

- **H1** (PRIMARY): compounds more similar in receptor pharmacology alone will show more similar
  safety reporting profiles.
- **H2a** (SECONDARY): compounds more similar in molecular structure alone will show more similar
  safety reporting profiles.
- **H2b** (SECONDARY): structural similarity alone will explain less safety-profile variation than
  a combined structure+receptor representation.
- **H3** (SECONDARY): therapeutic-use-associated and misuse-associated reports will show
  measurably different safety reporting phenotypes.
- **H4** (EXPLORATORY): specific pharmacological features will associate with specific
  adverse-event categories, accounting for reporting volume.

## Methods

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
logROR categories, same 3-column minimum. The same Mantel-style permutation test (Spearman rho on
upper-triangle distances, N=9,999 permutations, seed=42, one- and two-sided empirical p-values,
1,999-resample bootstrap CI) is run three times against the safety distance matrix, each answering
a distinct pre-registered hypothesis (`research/analysis_plan.md`): the pre-specified primary test
(H1) uses the receptor-only distance matrix; H2a uses the structure-only distance matrix; H2b uses
the combined (structure+receptor) distance matrix.

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
were run against the one fully computable result (H2a).

**Software and reproducibility.** Python 3.13, RDKit 2026.3.5, pandas, numpy, scipy, scikit-learn,
SQLAlchemy/PostgreSQL, all pinned via `uv.lock`. All random seeds fixed (default 42). Every derived
artifact carries a provenance manifest with the git commit and generation timestamp.

## Results

**Data collected** (real, not synthetic; see `reports/data_quality.md` for full detail): 10 cohort compounds, all with validated structures; 19 receptor bioactivity records covering **3/10** compounds (testosterone, oxandrolone, stanozolol); 10/10 compounds meet the FAERS minimum-report threshold, with 7433 deduplicated FAERS reports and 31061 individual reaction records (4057 distinct terms) across the cohort.

**Phenotype matrix coverage**: molecular descriptor matrix 10/10 compounds fully populated; receptor phenotype matrix 10/80 cells populated (12.5%); safety phenotype matrix 100/110 cells populated (90.9%) across 11 research-defined AE categories.

### Primary analysis (H1: receptor pharmacology vs. safety phenotype)

**NOT COMPUTABLE.** fewer than 4 objects have complete pairwise data in the first matrix

### Secondary analysis: H2a (structure-only) and H2b (combined) vs. safety phenotype

| Hypothesis | Representation | n compounds | Spearman rho | p (one-sided) | p (two-sided) | Bootstrap 95% CI |
|---|---|---|---|---|---|---|
| H2a | Structure-only | 10 | -0.293 | 0.956 | 0.152 | see `artifacts/matrices/matrix_association_results.json` |
| H2b | Combined (structure+receptor) | -- | NOT COMPUTABLE | -- | -- | fewer than 4 objects have complete pairwise data in the first matrix |

H2a found no significant positive association between structural similarity and safety-phenotype similarity (Figure 7). H2b (whether combined structure+receptor explains more than structure alone) could not be tested, for the same receptor-sparsity reason as H1.

### Clustering comparison (SECONDARY)

Structure clustering: k=2 (cophenetic r=0.840). Safety clustering: k=2 (cophenetic r=0.983). **Adjusted Rand Index=-0.111, Normalized Mutual Information=0.081** -- essentially no agreement between the two independently-derived cluster structures (Figures 3-6).

### Therapeutic vs. misuse comparison (SECONDARY, H3)

Group sizes: **429** misuse-classified reports, **450** therapeutic-classified reports (both strata meet the 20-report minimum: yes). Full classifier v2 distribution across all 7433 deduplicated reports: 6097 unknown, 450 therapeutic, 429 misuse, 357 multi_aas_exposure, 100 ambiguous_exposure.

| Outcome | Misuse | Therapeutic | Odds Ratio [95% CI] | Fisher p |
|---|---|---|---|---|
| serious | 394/429 (91.8%) | 378/450 (84.0%) | 2.14 [1.40, 3.29] | <0.001 |
| hospitalization | 231/429 (53.8%) | 186/450 (41.3%) | 1.66 [1.27, 2.16] | <0.001 |
| death | 84/429 (19.6%) | 82/450 (18.2%) | 1.09 [0.78, 1.53] | 0.667 |

**7/11** research-defined AE categories showed a raw Fisher p<0.05 difference between misuse- and therapeutic-associated reports; **7/11** remain significant after Benjamini-Hochberg FDR correction across all 11 category tests (q<0.05) (the same categories in both cases here -- correction did not flip any borderline result, though it changes the q-values reported per category and is not guaranteed to agree with the raw count in general) -- research/hypotheses.md's H3 falsifiability clause requires surviving multiple-comparison correction, not raw p<0.05 alone, so the FDR-corrected count is the one that speaks to H3 support (Figure 9; full table in `artifacts/matrices/misuse_vs_therapeutic_ae_categories.csv`). A leakage-controlled sensitivity variant -- excluding every reaction term the classifier itself uses as misuse evidence from AE-category membership, since one such term ("substance abuse") is also a "psychiatric" category entry -- finds **6/11** categories FDR-significant (`artifacts/matrices/misuse_vs_therapeutic_ae_categories_leakage_controlled.csv`); see Discussion for which category's significance depended on this leakage.

### Multivariate association (EXPLORATORY, H4, molecular descriptors)

**0/11** AE categories showed a statistically significant (permutation p<0.05) Ridge-regression association with molecular descriptors; every category's leave-one-out cross-validated R^2 was negative (worse than predicting the mean), consistent with the H2a null finding via an independent method.

### Sensitivity analyses (Phase 11)

**9/10** pre-specified sensitivity variants were computable with current data; all computable variants remained non-significant and directionally consistent with the primary H2a result (Figure 10; full results in `artifacts/matrices/sensitivity_results.json`).


## Discussion

**H1 (primary) could not be tested, and neither could H2b, for the same reason.** Receptor-
bioactivity coverage for this compound class in ChEMBL and BindingDB, as of this pull, is far too
sparse to support a matrix-association test involving the receptor-only or combined distance
matrices: only 3/10 cohort compounds have any measurement against any of the six target receptors,
and only one compound pair shares any receptor target at all. This is not a coding limitation but a
real gap in publicly available receptor pharmacology data for classic (non-drug-candidate) AAS --
`pipelines/chembl/README.md` and `pipelines/bindingdb/README.md` document plausible reasons
(ChEMBL/BindingDB curation for this target class skews toward novel synthetic drug-candidate
chemotypes such as SARMs, not long-established steroids used as reference compounds). H1 and H2b
therefore remain open questions, not refuted ones.

**H2a (secondary): no evidence that structural similarity alone predicts safety-profile
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
57.3% sign agreement -- barely better than chance. **Despite this, re-running the H2a Mantel test
itself under the all-FAERS-background safety distance matrix still finds no significant
association** (rho=-0.237, one-sided p=0.884, Figure 10) -- a similar magnitude and direction to
the primary cohort-relative result (rho=-0.293, p=0.956). The cohort-relative background choice
does materially distort individual compound-category cells, exactly as hypothesized, but this does
not change the pairwise-similarity conclusion that H2a draws on: structural similarity does not
predict safety-profile similarity under either background. Testosterone's structural similarity to
the rest of the cohort is unremarkable (Figure 5), so the background-choice sensitivity is specific
to the safety-reporting axis, not a symptom of a broader data problem.

**H3 (secondary): therapeutic-use and misuse-associated reports differ substantially, including
after multiple-comparison correction.** Unlike H1/H2a/H2b, this comparison has real statistical power
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
confirms the molecular representation itself is capturing real chemistry -- the null H2a result is
about the *link* to the safety phenotype, not a failure of the structural representation.

## Limitations

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
primary analysis (H1) and the structure-vs-combined comparison (H2b) entirely. This reflects real,
documented gaps in ChEMBL/BindingDB curation for this compound class (see Discussion), not a
pipeline defect -- but it means this report cannot speak to the receptor-pharmacology-to-safety
question at all.

**The cohort-relative safety-phenotype background is a methodological choice with real,
now-confirmed consequences**, discussed above: with one compound (testosterone) contributing 75%
of total report volume, every other compound's relative logROR reflects both its own reporting
pattern and its relationship to testosterone's. An all-FAERS background (comparing each compound
to the entire FAERS database via live openFDA count queries rather than a full re-ingestion, see
`analysis/full_faers_background.py`) is now computable and confirms the mechanism: per-cell logROR
values agree with the cohort-relative background only weakly (r=0.522 in magnitude, 57.3% sign
agreement across 110 cells) -- but the H2a conclusion itself (structural similarity vs. safety
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
misclassification of raw FAERS drug-name strings is possible.

## Conclusion

This project built a reproducible, provenance-tracked pipeline integrating molecular structure,
receptor pharmacology, and FAERS adverse-event reporting for a 10-compound AAS cohort, and executed
a pre-registered analysis plan against real data end to end. The central, pre-specified test of
whether receptor-pharmacology similarity predicts safety-reporting-profile similarity (H1), and
whether receptor pharmacology adds incremental value over structure alone (H2b), could not be run
due to real, documented receptor-bioactivity data sparsity -- an honest negative capability
finding, not a null scientific result. The fully computable structural-similarity test (H2a) found no
significant association, a finding that was stable across every sensitivity analysis that could be
run. In contrast, therapeutic-use-versus-misuse reporting phenotypes differ substantially and
significantly (H3) after both multiple-comparison correction and a classifier-outcome-leakage
control -- and structural clustering independently recovered chemically sensible compound groups --
together indicating this pipeline is capturing real signal where the underlying data support it,
rather than producing noise throughout. Claims are held proportional to the evidence: this report
neither forces a positive structure-to-safety association nor discards the substantive
misuse-vs-therapeutic finding, and it withdraws the one specific AE-category claim (psychiatric)
that a leakage-control sensitivity analysis showed was a methodological artifact rather than a
real difference -- for the sake of a tidier narrative, none of these were suppressed or softened.
