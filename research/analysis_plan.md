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

- **Primary combined representation:** concatenation of (a) standardized molecular descriptors + Morgan
  fingerprint-derived similarity and (b) standardized receptor pharmacology (pKi/pIC50/pEC50 per receptor,
  kept within measurement-type-homogeneous groups — see Sec. 27 and exclusion_rules.md). This combined
  representation is primary because H1's test is specified as "receptor pharmacology" broadly construed with
  structure as a covering representation; H2 explicitly interrogates whether structure alone underperforms this
  combined representation.
- **Structure-only and receptor-only representations** are computed identically but are SECONDARY, used only for
  the H2 comparison (Sec. 19).
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

- **Method:** Mantel-style permutation test (Sec. 18) between the pairwise combined molecular/pharmacological
  distance matrix and the pairwise safety-phenotype distance matrix.
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

*(None yet. This project has not ingested data or run the primary analysis as of the date this file was first
committed. Any future deviation is logged below in the format: Date | Section | Original | Change | Reason |
Before/after results were examined.)*

| Date | Section | Original | Change | Reason | Before/after results examined |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
