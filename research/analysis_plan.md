# Pre-Specified Analysis Plan

**Status:** Drafted before ingestion of any ChEMBL bioactivity data or FAERS reports. This document must be
committed to version control **before** the primary analysis (H1, Sec. 18) is run. Any deviation from what is
written here, made after data have been inspected, must be logged in the "Deviations" section at the bottom with
the original plan, the change, the reason, and an explicit statement of whether the change was made before or
after examining results (Sec. 39).

This plan operationalizes the hypotheses in [hypotheses.md](hypotheses.md) and the cohort/report criteria in
[exclusion_rules.md](exclusion_rules.md).

---

## 1. Primary outcome representation (Representation B — safety phenotype)

- **Unit of analysis:** compound (canonical parent entity, per the normalization hierarchy in
  `docs/database_schema.md`), not individual formulations/esters, for the primary analysis.
- **Primary metric:** log Reporting Odds Ratio (logROR) computed per compound × research-defined adverse-event
  category (Sec. 13), using the 2×2 disproportionality design in Sec. 11, with Haldane–Anscombe continuity
  correction (+0.5 to all four cells) applied **only** to cells that would otherwise be zero, applied
  consistently across all compound-event pairs. The choice of logROR over raw ROR, PRR, or shrinkage estimators
  is documented in `analysis/phenotype_matrix.py` docstrings and reports/research_report.md Methods once
  candidate representations have been compared empirically (Sec. 14 requires comparing candidates, not choosing
  arbitrarily).
- **Comparator group:** all other cohort compounds' reports in the same FAERS extract (compound vs. rest-of-cohort
  design), not the full FAERS database, so that disproportionality reflects relative reporting differences
  *within the AAS class* rather than AAS-vs-all-drugs (which would trivially separate AAS from non-endocrine
  drugs). This choice is a primary methodological decision and is revisited in Sensitivity 6 (Sec. 24) using an
  all-FAERS background as an alternative definition.
- **Category set:** research-defined adverse-event categories in `research/ae_categories.csv` (cardiovascular,
  thrombotic, hepatic, renal, endocrine, reproductive, psychiatric, neurologic, dermatologic, hematologic,
  metabolic). Individual MedDRA preferred terms are preserved separately and used in Sensitivity 4.
- **Secondary safety-phenotype fields retained alongside logROR:** report count, serious report count,
  hospitalization count, death report count, serious proportion — always displayed next to any logROR figure
  or table (Sec. 12).

## 2. Primary molecular/pharmacological representation (Representation A)

*(Revised 2026-09-04 — see `hypotheses.md`'s Amendment log and this file's Deviations table. The prior version
of this section justified a **combined** structure+receptor representation as primary via "H1's test is
specified as 'receptor pharmacology' broadly construed with structure as a covering representation" — a
description that didn't match H1's own statement in hypotheses.md, which has always been about receptor
pharmacology alone. Fixed here to match; no test result changed, since the combined and receptor-only
representations were already computed identically and were already both NOT COMPUTABLE for the same
receptor-sparsity reason regardless of which one carried the "primary" label.)*

- **Receptor-only representation** (standardized receptor pharmacology: pKi/pIC50/pEC50 per receptor, kept
  within measurement-type-homogeneous groups — see Sec. 27 and exclusion_rules.md) is primary, used for H1's
  test (Sec. 18), matching H1's statement in `hypotheses.md` exactly ("receptor pharmacology... binding and
  functional activity profiles").
- **Structure-only representation** (standardized molecular descriptors + Morgan fingerprint-derived similarity)
  is SECONDARY, used for H2a's test (Sec. 18, same test infrastructure as H1) and as one arm of H2b's comparison.
- **Combined representation** (concatenation of structure-only and receptor-only) is SECONDARY, used only as the
  other arm of H2b's comparison (Sec. 19) — it is not, and was never intended to be, H1's own test.
- **Missing receptor data:** compounds missing a given receptor's activity data contribute `NaN` to that column;
  the primary similarity calculation uses **pairwise-complete** feature overlap (Sec. 15) rather than mean
  imputation. A complete-case sensitivity analysis is run separately (Sensitivity 1 variant, restricted to
  compounds with AR data at minimum, since AR is the historically best-characterized target for this class).

## 3. Similarity / distance metrics

| Data type | Primary metric | Rationale | Alternate metrics tested in sensitivity |
|---|---|---|---|
| Structural fingerprints | Tanimoto similarity on Morgan (ECFP-like) fingerprints, radius=2, 2048 bits | Standard for 2D structural similarity in cheminformatics; bounded [0,1] | Dice coefficient |
| Molecular descriptors | Euclidean distance on z-scored descriptors | Descriptors are continuous, differing scales; z-scoring make Euclidean meaningful | Cosine distance |
| Receptor pharmacology | Pearson correlation (converted to distance = 1 − r) across shared pActivity features | Captures relative receptor-selectivity *pattern* similarity, which is pharmacologically more interpretable than absolute-value distance for compounds with partial data | Spearman correlation, cosine similarity, Euclidean distance |
| Safety phenotype | Pearson correlation (converted to distance = 1 − r) across shared AE-category logROR values | Same rationale: captures relative-profile shape | Spearman correlation, cosine similarity, Euclidean distance |

The primary metric per row is used for H1's primary test. All "alternate metrics tested in sensitivity" columns
are run under Sensitivity 5 (Sec. 24) to test robustness of the primary conclusion to metric choice.

## 4. Primary statistical test (H1)

- **Method:** Mantel-style permutation test (Sec. 18) between the pairwise **receptor-only** pharmacological
  distance matrix and the pairwise safety-phenotype distance matrix (matching H1's statement in
  `hypotheses.md` exactly — see Sec. 2's revision note above). H2a reuses this same test infrastructure against
  the structure-only distance matrix instead; H2b compares both against the combined distance matrix.
- **Test statistic:** Spearman correlation between the upper-triangle entries of the two distance matrices
  (Spearman chosen over Pearson because distances are not assumed linearly related and because the compound
  count is small, making rank-based association more robust to outlying pairs).
- **Permutation procedure:** randomly permute compound labels (rows/columns jointly) on one matrix, holding the
  other fixed; recompute the test statistic; repeat for **N = 9,999 permutations** (chosen to give a
  minimum-achievable two-sided p-value of 1×10⁻⁴, well below the alpha threshold, while remaining fast to
  compute for the small matrix sizes involved).
- **Random seed:** `42` (module-level `numpy.random.default_rng(42)`), recorded in the run manifest
  (`artifacts/manifests/`) for every execution.
- **Empirical p-value:** `(1 + #{permuted statistic ≥ observed statistic}) / (1 + N)` for a one-sided-positive
  test (consistent with H1's directional prediction), reported alongside the two-sided version.
- **Uncertainty characterization:** in addition to the permutation p-value, a bootstrap (compound-pair
  resampling with replacement, 1,999 resamples) confidence interval on the Spearman statistic is reported as a
  secondary uncertainty measure. Because pairwise distances are not independent observations, this bootstrap CI
  is explicitly labeled approximate/exploratory, not a substitute for the permutation p-value.
- **Alpha:** 0.05, pre-specified, not adjusted post hoc.

## 5. Compound inclusion criteria (cohort-level)

See `research/exclusion_rules.md` for the full, versioned criteria and thresholds table. Summary:

- Valid, RDKit-parseable structure (canonical SMILES resolves to a sanitizable Mol object) — required for any
  inclusion.
- Minimum FAERS reports (compound-level, post-deduplication) to enter the safety phenotype matrix.
- Minimum number of usable (assay-type-homogeneous, human-target, confidence-filtered) receptor measurements to
  enter the receptor phenotype matrix for a given target.
- A compound may be included in the structural analysis, excluded from the receptor analysis (insufficient
  bioactivity data), and included or excluded from the safety analysis independently — the cohort is
  **analysis-specific**, not a single fixed list (Sec. 8).

## 6. Missing-data handling

- Receptor phenotype: pairwise-complete similarity (Sec. 2 above); no mean/median imputation used for the
  primary analysis. A missingness coverage figure (Fig. 2, `analysis/missingness_analysis.py`) is produced
  before any modeling.
- Safety phenotype: adverse-event categories with too few reports for a given compound are treated as missing
  (`NaN`), not zero, and excluded from that compound's contribution to correlation-based similarity — never
  imputed as "no signal."
- Any imputation beyond pairwise-complete handling would require explicit justification and is not used in the
  primary analysis (Sec. 15).

## 7. Sensitivity analyses (all pre-specified; see Sec. 24)

1. Alternate minimum-report thresholds (e.g., ±50% of primary threshold).
2. Parent compounds only vs. parent + defined ester/formulation aliases merged.
3. All FAERS reports vs. reports excluding uncertain/low-confidence drug-name normalization.
4. Category-level AE grouping vs. individual MedDRA preferred terms.
5. Alternate similarity metrics (see table in Sec. 3 above).
6. Alternate safety-phenotype definitions (logROR vs. standardized report proportion vs. serious-proportion
   vector) and alternate comparator background (cohort-relative vs. all-FAERS).
7. Therapeutic-only report subset.
8. Misuse-associated report subset.

Each sensitivity analysis reruns the primary H1 test with one factor changed, holding all else fixed, and reports
whether the conclusion (direction, approximate p-value magnitude) is stable. Sensitivity results are summarized
in Fig. 10 and `reports/research_report.md`.

## 8. Software / reproducibility

- Python version, RDKit version, and all pinned library versions are recorded in `backend/pyproject.toml` /
  `uv.lock` and echoed into `artifacts/manifests/dataset_manifest.json` at each pipeline run, along with the
  Git commit hash of the code that produced the artifact (Sec. 28–29).
- All random seeds are fixed and logged (Sec. 29).

## 9. Analysis labeling

Every analysis output in this project is labeled PRIMARY, SECONDARY, or EXPLORATORY (Sec. 40) in its source
docstring, its figure caption, and the research report. The mapping is given in hypotheses.md's
"Hypothesis-to-analysis mapping summary" table.

---

## Deviations from pre-specified plan

| Date | Section | Original | Change | Reason | Before/after results examined |
|---|---|---|---|---|---|
| 2026-08-28 | Sec. 2/4 (primary combined representation; H1 primary test) | The primary test (Sec. 18) is the combined structure+receptor distance matrix vs. the safety distance matrix, evaluated via Mantel-style permutation, on the full 10-compound cohort. | The combined and receptor-only distance matrices are computed exactly as specified (Pearson correlation on shared pActivity columns, pairwise-complete, no imputation), but **before running the Mantel test itself**, inspection of the receptor phenotype matrix built in Phase 8 showed that only 3/10 cohort compounds (testosterone, oxandrolone, stanozolol) have *any* ChEMBL/BindingDB receptor measurement, and of the 45 possible compound pairs, only **1** (testosterone-oxandrolone, sharing AR_IC50/AR_Ki) has a defined receptor distance at all — every other pair shares zero receptor columns. A Mantel-style permutation test requires a complete (or at least substantially populated) n x n distance matrix for a well-defined set of objects; with only 1 of 45 pairs defined, the combined and receptor-only matrices cannot support a meaningful permutation test for any subset of >=3 compounds (even the 3 compounds with any receptor data at all only yield 1 of their 3 mutual pairs). This is therefore reported as **"not computable"** rather than as a p-value forced out of a degenerate matrix. **Structure-only distance vs. safety distance (Sec. 19, originally SECONDARY) is fully computable on all 10 compounds and is reported as the main computable result of Phase 9**, explicitly still labeled SECONDARY per the original hierarchy — it is not promoted to "primary," since that label change would misrepresent what was pre-registered. The intended primary (combined) test remains an open question pending better receptor-bioactivity coverage for this compound class, which is itself a reportable finding (Phase 5's README already documents *why* coverage is this sparse: ChEMBL/BindingDB curation for this class skews toward synthetic drug-candidate chemotypes, not classic AAS). | This is a data-availability fact discovered through the Phase 8 phenotype-matrix build (i.e., before any H1 test was run or its correlation/p-value inspected) — not a reaction to the H1 result itself, which remains unknown at the time of this entry. Logged **before** examining any matrix-association result. |
| 2026-09-04 | Sec. 6/22 (H3 misuse classifier and AE-category comparison, exclusion_rules.md Sec. 6) | The v1 classifier (`pipelines/faers/classification.py`) treated every misuse-suggestive reaction term as equally sufficient evidence for a MISUSE label; the H3 AE-category comparison used only raw Fisher p<0.05 per category, with no multiple-comparison correction, despite hypotheses.md's own H3 falsifiability clause requiring one; and no check was run for overlap between the classifier's own evidence terms and the `research/ae_categories.csv` taxonomy. | Three corrections, made together: (1) the classifier (now v2) splits misuse evidence into a high-confidence tier (sufficient alone: "drug abuse," "illicit drug use," "intentional product misuse," "intentional overdose," "prescription drug used without prescription," "substance abuse," "drug abuser") and an ambiguous tier (never sufficient alone: "overdose," "accidental overdose," "product use in unapproved indication," "intentional product use issue"), moving 125/554 (22.6%) of v1's MISUSE-classified reports to a new, separately-tracked `AMBIGUOUS_EXPOSURE` classification or `MULTI_AAS_EXPOSURE`; (2) Benjamini-Hochberg FDR correction (q<0.05) is now computed and reported alongside every raw Fisher p-value in the AE-category comparison; (3) a leakage-controlled sensitivity variant excludes every classifier-evidence reaction term from AE-category tabulation, since "substance abuse" is both a high-confidence misuse term and a `research/ae_categories.csv` "psychiatric" entry. Net result on real data: the smaller, more conservative MISUSE group (n=429 vs. 554) shows *stronger* seriousness/hospitalization associations than before; 7/11 AE categories remain FDR-significant (same 7 as raw p<0.05 here); the leakage control drops that to 6/11, with the psychiatric category's significance (raw p=0.013) shown to be entirely attributable to the term-overlap leakage (leakage-controlled p=0.320) while the other 6 FDR-significant categories are unaffected. Full detail in `reports/research_report.md` Discussion. | This was identified from external review of the already-published v1 result (raw "7/11 categories significant" claim, no FDR correction, no leakage check) -- i.e. **after** examining the H3 result. Logged as an explicit post-hoc methodological correction, not a silent revision: the v1 numbers, the reasoning for the change, and both the corrected and leakage-controlled results are all reported in `reports/research_report.md` rather than only the corrected numbers. |
| 2026-09-04 | Sec. 2/4 (primary representation for H1); `hypotheses.md` H2 split into H2a/H2b | Sec. 2 justified a **combined** structure+receptor distance matrix as H1's primary representation via "H1's test is specified as 'receptor pharmacology' broadly construed with structure as a covering representation" — language that didn't match H1's own statement in `hypotheses.md` (receptor pharmacology alone). Separately, `hypotheses.md`'s single H2 conflated "does structure alone predict safety similarity" (the test this project actually reports as its main computable secondary result) with "does combined structure+receptor outperform structure alone" (a comparison of two results) — one statement covering two distinct claims with only one operational definition/falsifiability criterion, which cleanly fit only the second claim. | Sec. 2/4 now name **receptor-only** distance as H1's primary representation/test, matching H1's text exactly; combined distance is now described only as one arm of H2b's comparison. `hypotheses.md`'s H2 is split into **H2a** (structure-only distance vs. safety distance, its own full statement/null/operational-definition/falsifiability) and **H2b** (the original structure-vs-combined comparison, otherwise unchanged). `analysis/matrix_association.py`'s `TESTS` list, `reports/research_report.md`, and the dashboard relabeled to match. | External review identified both as internal-consistency problems in the pre-registered documents/code themselves (a mismatch between stated hypothesis and coded test; a hypothesis definition not matching what was actually reported under its name) — not new findings from the data, and not a reaction to any result. No result changed: H1's and H2b's underlying tests (receptor-only, combined) were already computed and already both NOT COMPUTABLE for the same receptor-sparsity reason regardless of label; H2a's test (structure-only) was already computed and already reported as the main secondary result under the "H2" name. Logged here as a labeling/attribution fix made after the primary analysis had already been run and its results seen, per this document's own rule. |
| 2026-09-04 | Sec. 24 (Sensitivity 6, all-FAERS background) | Sensitivity 6's all-FAERS-background variant was reported "not computable": this project's FAERS ingestion (`pipelines/faers/ingest.py`) deliberately pulls only cohort-relevant reports, not the full FAERS database, so the comparator data needed for a full-database background did not exist in this dataset. | Realized the *aggregate counts* an all-FAERS background needs (per-compound totals, per-category totals across all drugs, and the grand total) do not require ingesting or storing the full database -- they can be obtained directly from openFDA's own count-only aggregation endpoint (`meta.results.total` on a `limit=1` query). Built `analysis/full_faers_background.py`: 132 live, count-only queries (10 compound totals + 11 category totals + 1 grand total + 10x11 combined), querying compound/category counts live rather than reusing this project's own ingestion (which caps testosterone at 5,000 of its true 31,733 reports) to keep all 10 compounds on equal footing. Wired into `analysis/sensitivity.py`'s Sensitivity 6 in place of the prior hardcoded `computable: false`. Result: 9/10 sensitivity variants now computable (was 8/10). The all-FAERS-background Mantel test itself remains null (rho=-0.237, p=0.884, similar to the primary rho=-0.293), but the underlying per-cell logROR values shift substantially under the alternate background (r=0.522 correlation, 57.3% sign agreement vs. the cohort-relative version across 110 cells) -- confirming the cohort-relative background's testosterone-dominance effect discussed in the H2 Discussion is real, even though it doesn't change the H2 conclusion. Full detail in `reports/research_report.md` Discussion and Limitations. | This was identified from external review's suggestion to compare AAS-relative vs. full-FAERS ROR -- a capability gap noted in the original report, not a reaction to having seen what the all-FAERS result would show (the result was unknown until this was built and run). Logged as a capability addition rather than a result-driven change, but recorded here per this document's own rule that any change made after the primary analysis has been run once belongs in this table. |
