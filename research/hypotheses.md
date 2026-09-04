# Hypotheses

**Project:** Structure-to-Safety — Multimodal Computational Pharmacology of Anabolic-Androgenic Steroids
**Status:** Pre-specified prior to primary analysis. See [analysis_plan.md](analysis_plan.md) for the statistical
methods that operationalize these hypotheses, and [exclusion_rules.md](exclusion_rules.md) for the inclusion
criteria that determine which compounds/reports enter each test.
**Version:** 0.1 (drafted at project inception, before any FAERS or ChEMBL data have been ingested or analyzed)

## Purpose and framing

These are hypotheses to be **tested**, not outcomes to be produced. A null or negative result (no detectable
association) is a scientifically valid and reportable outcome, provided the methodology is sound. This document
exists so that the primary analysis (Aim 3 / H1–H2b) cannot be silently redefined after results are seen. Any
change to a hypothesis or its operational definition after data inspection must be logged in
[analysis_plan.md](analysis_plan.md) under "Deviations from pre-specified plan," with the original text, the
change, the reason, and whether the change occurred before or after examining results.

All hypotheses concern **FAERS reporting phenotypes**, not clinical incidence, prevalence, or causal adverse
effects. See [Section 23 confounding discussion / reports/research_report.md Limitations] for why FAERS cannot
support causal or incidence claims.

---

## H1 — Receptor pharmacology similarity and reporting-profile similarity

**Statement:** Anabolic-androgenic steroids that are more similar in receptor pharmacology (AR/PR/GR/MR/ER
binding and functional activity profiles) will exhibit more similar real-world adverse-event **reporting**
profiles in FAERS, compared to compound pairs that are less similar in receptor pharmacology.

**Null hypothesis (H1₀):** There is no association between pairwise receptor-pharmacology similarity and
pairwise FAERS reporting-profile similarity across the compound cohort (population Mantel/Spearman correlation
of pairwise distances = 0).

**Operational definition:**
- Receptor-pharmacology similarity: pairwise distance/similarity over the receptor phenotype matrix (Sec. 15),
  restricted to compounds meeting the minimum receptor-measurement thresholds in exclusion_rules.md.
- Reporting-profile similarity: pairwise distance/similarity over the safety phenotype matrix (Sec. 14),
  restricted to compounds meeting the minimum FAERS report thresholds.
- Test: Mantel-style permutation test between the two distance matrices (Sec. 18). Primary test — see
  analysis_plan.md.

**Direction:** Positive association predicted (more receptor-similar → more report-similar). A negative or null
result does not falsify AAS pharmacology broadly; it may reflect FAERS reporting noise, small compound-pair
sample size, or genuine absence of a detectable relationship at current data volume.

**Falsifiability:** H1 is not supported if the permutation p-value exceeds the pre-specified alpha (0.05,
two-sided framing but tested as one-sided-positive per analysis_plan.md) or if the point estimate is
near zero/negative with a confidence interval that excludes a scientifically meaningful positive association.

*Note (2026-09-04, see Amendment log): this statement, null hypothesis, and operational definition were never
changed -- H1 has always been about receptor pharmacology alone. What was wrong was the "Hypothesis-to-analysis
mapping summary" table below, which listed H1's primary test as the **combined** structure+receptor distance
matrix, not the receptor-only matrix this section actually defines. That table is now fixed to match this
section, not the other way around.*

---

## H2a — Structural similarity and reporting-profile similarity

*(Added 2026-09-04, split out of the original single "H2" -- see Amendment log. The original H2 conflated two
distinct claims: whether structure alone predicts safety-profile similarity, and whether receptor pharmacology
adds incremental value over structure. Renamed the first claim H2a and kept the second as H2b, below, so each
has its own operational definition and falsifiability criterion rather than sharing one that only cleanly fit
the second.)*

**Statement:** Anabolic-androgenic steroids that are more similar in molecular structure (2D fingerprint /
descriptor similarity) will exhibit more similar real-world adverse-event **reporting** profiles in FAERS,
compared to compound pairs that are less similar in structure.

**Null hypothesis (H2a₀):** There is no association between pairwise structural similarity and pairwise FAERS
reporting-profile similarity across the compound cohort (population Mantel/Spearman correlation of pairwise
distances = 0).

**Operational definition:**
- Structural similarity: pairwise distance over the molecular structure representation (fingerprint + descriptor,
  Sec. 15), computable for all compounds meeting the minimum FAERS report thresholds -- unlike H1/H2b, not
  gated by receptor-bioactivity coverage.
- Reporting-profile similarity: same safety phenotype matrix as H1 (Sec. 14).
- Test: Mantel-style permutation test between the two distance matrices (Sec. 18). SECONDARY relative to H1.

**Direction:** Positive association predicted (more structure-similar → more report-similar).

**Falsifiability:** H2a is not supported if the permutation p-value exceeds the pre-specified alpha (0.05, tested
as one-sided-positive) or if the point estimate is near zero/negative.

---

## H2b — Incremental value of receptor pharmacology over structure alone

**Statement:** Molecular structural similarity alone (2D fingerprint / descriptor similarity) will explain less
of the variation in FAERS reporting-profile similarity than a combined representation that adds receptor
pharmacology to structure.

**Null hypothesis (H2b₀):** The association between structure-only similarity and reporting-profile similarity is
equal to (not smaller than) the association between combined structure+receptor similarity and reporting-profile
similarity.

**Rationale:** Two steroids can be structurally close (shared steroid nucleus, similar substituents) yet exert
divergent receptor selectivity (e.g., aromatizable vs. non-aromatizable compounds, differential
progestogenic/glucocorticoid affinity) that plausibly drives divergent adverse-event categories (e.g.,
estrogenic/gynecomastia-related events vs. hepatic events). If true, receptor pharmacology should carry
information about reporting phenotype beyond what structure alone provides.

**Operational definition:** Compare three matrix-association results (Sec. 19, Sec. 21):
(A) structure-only distance vs. safety distance (= H2a's own test, reused rather than recomputed), (B)
receptor-only distance vs. safety distance (= H1's own test, reused), (C) combined distance vs. safety distance.
This comparison is **secondary/exploratory** relative to H1's primary test (Sec. 40) because with ~10 compounds
the number of independent comparisons that can be reliably distinguished is limited; formal statistical
comparison of dependent correlations will be attempted but underpowered results will be reported as such, not
suppressed.

**Falsifiability:** H2b is not supported if structure-only association is equal to or stronger than the combined
association, or if the combined model does not improve out-of-sample predictive performance in
cross-validated comparisons (Sec. 19, Sec. 21).

---

## H3 — Therapeutic-use vs. misuse-associated reporting phenotypes

**Statement:** Reports classified as misuse/abuse-associated (Sec. 22) will exhibit a measurably different
adverse-event reporting phenotype — including a higher proportion of serious outcomes, hospitalization, and
death — than reports classified as therapeutic-use-associated.

**Null hypothesis (H3₀):** No difference in adverse-event category distribution, seriousness proportion, or
outcome distribution between therapeutic-use-associated and misuse-associated report strata.

**Operational definition:** Uses the conservative, evidence-logged classification scheme in Sec. 22
(exclusion_rules.md documents required evidence). Compounds/report strata with too few classified reports
(below the minimum threshold) are excluded from this specific test but retained in the "unknown/unclassifiable"
category for transparency. Comparison uses chi-square/Fisher's exact tests for categorical outcomes and, where
sample size allows, logistic regression with effect sizes and confidence intervals — not p-values alone.

**Important caveat:** A finding here reflects a **reporting-pattern difference**, not proof that misuse causes
worse clinical outcomes. Misuse-associated reports may differ in reporter type, polypharmacy, dose, product
provenance (unregulated/adulterated sources), and reporting completeness — all of which confound any
naive causal reading.

**Falsifiability:** H3 is not supported if no statistically and practically meaningful difference is observed
across the tested outcome measures after correcting for multiple comparisons.

*Implementation note (2026-09-04, logged in `analysis_plan.md`'s Deviations table, not here, since this
document's own text was not changed): the multiple-comparison correction this falsifiability clause requires
was not actually implemented in `analysis/misuse_analysis.py` until this date, and the misuse classifier used
up to that point did not distinguish high-confidence from ambiguous misuse evidence. Both are now fixed
(Benjamini-Hochberg FDR correction + a classifier-outcome-leakage-controlled sensitivity variant); see
`reports/research_report.md` Discussion for the corrected result.*

---

## H4 — Receptor/pharmacological features associated with specific adverse-event categories

**Statement:** After accounting for compound-level reporting volume and other available covariates, specific
receptor/pharmacological features (e.g., AR binding affinity, aromatization potential, 17α-alkylation status)
will show associations with specific FAERS adverse-event categories (e.g., hepatic events with 17α-alkylation,
cardiovascular/lipid-related events with AR/aromatization profile).

**Null hypothesis (H4₀):** No pharmacological feature shows an association with any adverse-event category
after penalization/multiple-comparison correction and accounting for reporting-volume covariates.

**Operational definition:** Multivariate association analysis (Sec. 21) using penalized regression
(ridge / sparse models) or partial least squares given the small number of compounds (n≈10), with permutation
based inference. This is explicitly **secondary/exploratory** — with so few independent compounds, any
per-feature "hit" must be interpreted as hypothesis-generating, not confirmatory, and will be labeled as such
throughout (Sec. 40).

**Falsifiability:** H4 findings that do not survive permutation-based significance testing or that are not
robust to the sensitivity analyses in Sec. 24 will be reported as non-robust/exploratory, not as confirmed
associations.

---

## Hypothesis-to-analysis mapping summary

| Hypothesis | Primary/Secondary | Analysis section | Primary test |
|---|---|---|---|
| H1 | **PRIMARY** | Sec. 18 (Central matrix-association test) | Mantel-style permutation test, **receptor-only** distance vs. safety distance |
| H2a | SECONDARY | Sec. 18 (same test infrastructure as H1) | Mantel-style permutation test, **structure-only** distance vs. safety distance |
| H2b | SECONDARY | Sec. 19 (Compare representations) | Structure-only vs. receptor-only vs. combined matrix association; cross-validated comparison |
| H3 | SECONDARY | Sec. 22 (Therapeutic vs. misuse) | Chi-square/Fisher tests, logistic regression, effect sizes |
| H4 | EXPLORATORY | Sec. 21 (Multivariate association) | Penalized regression with permutation inference |

## Amendment log

| Date | Section | Original | New | Reason | Before/after results examined |
|---|---|---|---|---|---|
| 2026-09-04 | H2 (split); Hypothesis-to-analysis mapping summary | A single H2 covering "structure alone explains less than combined structure+receptor" (a comparison of two matrix-association results), while the report's actual computable secondary result (structure-only distance vs. safety distance, reported since Phase 9) was never a formally pre-registered hypothesis in its own right. Separately, the mapping table listed H1's primary test as the **combined** structure+receptor distance matrix, contradicting H1's own statement/operational-definition text above (receptor pharmacology alone). | Split H2 into **H2a** (structure-only distance vs. safety distance -- the test this project actually reports as its main computable secondary result) and **H2b** (the original comparison: does combined structure+receptor explain more than structure alone). Fixed the mapping table so H1's primary test is receptor-only distance vs. safety distance, matching H1's own text. | External review noted the mismatch between H1's stated definition (receptor pharmacology) and its coded primary test (combined structure+receptor), calling it "unnecessarily vulnerable to a reviewer asking: was the endpoint changed?" -- and separately that the report's actual computed "H2" result doesn't match hypotheses.md's own H2 definition. Both are real internal-consistency bugs in this document and the code, not scientific findings, and were caught by reading text against code/report output, not by seeing a result change. | No result changed: H1's and H2b's underlying tests (receptor-only, combined) were already computed and already both NOT COMPUTABLE for the same receptor-sparsity reason regardless of label; H2a's test (structure-only) was already computed and already reported as the main secondary result. This is a labeling/attribution fix, not a re-analysis -- logged here per this document's own rule regardless, since the change was made after the primary analysis had already been run and its results seen. |
