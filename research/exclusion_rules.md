# Inclusion / Exclusion Criteria and Minimum-Data Thresholds

**Status:** Pre-specified, version 0.2. These thresholds are defaults chosen to balance statistical stability
against the reality that this compound class has limited pharmacovigilance and bioactivity coverage. They are
deliberately revisited in `research/sensitivity_analyses.md` (Sensitivity 1) rather than tuned post hoc against
the primary result.

**v0.2 change (2026-08-27, Phase 4 implementation, before any primary/H1 analysis was run):** the molecular-weight
structure-integrity tolerance in Sec. 2 was widened from ±0.02 to ±0.1 g/mol after empirically checking it
against real PubChem data. PubChem's `MolecularWeight` property is reported rounded to 1 decimal place (e.g.
`288.4` for testosterone), while RDKit's `Descriptors.MolWt` computes to full precision (`288.431` for the same
structure) -- a ~0.03 g/mol gap from rounding alone, before any minor atomic-mass-table differences between the
two tools. ±0.02 would fail on real, correctly-parsed structures; ±0.1 comfortably covers PubChem's rounding
while still catching genuine structure mismatches (which typically differ by whole atoms, i.e. several g/mol).

The cohort is **analysis-specific** (Sec. 8 of the project brief): a compound can satisfy structural criteria,
fail receptor criteria, and pass or fail FAERS criteria independently. Every table/figure that uses a cohort
must state which of the criteria below it applied and list the resulting compound set (`artifacts/manifests/`).

---

## 1. Initial candidate cohort

Starting candidate list (canonical parent compounds; see `docs/database_schema.md` for the
parent/derivative/alias hierarchy):

testosterone, nandrolone, oxandrolone, stanozolol, oxymetholone, methandienone (metandienone), drostanolone,
methenolone, boldenone, trenbolone.

This list is a **starting point**, not a guarantee of inclusion in any given analysis — each compound must
independently satisfy the criteria below for each representation it participates in. The list may be extended
later (e.g., additional esters/derivatives as distinct formulation entities) but any extension must be logged
here with a version bump and rationale.

## 2. Structural validity (required for any inclusion, any analysis)

- Canonical SMILES must be retrievable from PubChem (PUG REST) for the parent compound.
- SMILES must parse to a sanitizable RDKit `Mol` object (`Chem.MolFromSmiles(...)` does not return `None`, and
  `Chem.SanitizeMol` does not raise).
- Molecular formula and molecular weight computed from the parsed structure must match the PubChem-reported
  values within rounding tolerance (±0.1 g/mol -- see v0.2 change note above), as a structure-integrity check.
- Failure at this step **excludes the compound from every downstream analysis** and is logged in
  `reports/data_quality.md` under "invalid structures."

## 3. Receptor-pharmacology (ChEMBL/BindingDB) inclusion — per target

For a compound to contribute a value for a given receptor target (AR, PR, GR, MR, ERα, ERβ) in the receptor
phenotype matrix:

- **Minimum usable measurements:** ≥ 1 measurement from a human-target assay (`assays.organism` = *Homo
  sapiens*, or a well-validated ortholog assay explicitly flagged as such — never silently pooled with human
  data) with a documented `measurement_type` (Ki, IC50, EC50, or Kd — never pooled across types) and an
  unambiguous relation (`=`; `>`/`<`-qualified "censored" values are retained in the database but excluded from
  the point-estimate pActivity used in the primary phenotype matrix, per Sec. 3 of the brief).
- **Assay confidence:** ChEMBL `confidence_score` ≥ 8 (direct single-protein target assignment) preferred;
  assays below this threshold are retained in the database with their confidence score but excluded from the
  primary receptor phenotype matrix and flagged in a confidence-restricted sensitivity subset.
- **Aggregation when multiple qualifying measurements exist for the same compound × target × measurement_type:**
  use the **median** standardized pActivity within that homogeneous group (same measurement type, same
  organism, comparable assay format — binding vs. functional/cell-based kept as separate candidate groups, and
  which group is "primary" for a given target is documented in `analysis/receptor_profiles.py` once real data
  are inspected, per Sec. 27). Never average across measurement types or across binding/functional assay
  formats.
- A target with **zero qualifying measurements** for a compound is recorded as missing (`NaN`) for that
  compound × target cell — never imputed as zero or as "no activity."

## 4. FAERS report inclusion — compound level

- **Minimum total drug reports (post-deduplication, post-normalization) for a compound to enter the safety
  phenotype matrix at all:** ≥ 20 reports mapped to that compound at "exact alias" or "curated match" mapping
  confidence (see `docs/database_schema.md` compound-normalization mapping methods). This default is a starting
  threshold, tested at ±50% in Sensitivity 1.
- **Minimum drug-event pair reports for a specific compound×adverse-event-category cell to be included in the
  primary logROR table as a headline result:** ≥ 3 reports for that cell (`a` in the 2×2 table). Cells below this
  are still computed and stored (for transparency and for meta-level "sparse category" reporting in
  `reports/data_quality.md`) but are **not** presented as reliable signals in the report/dashboard without an
  explicit sparse-data caveat, and are visually distinguished (e.g., grayed out / flagged) wherever shown.
- **Minimum background cell count:** each of `b`, `c`, `d` in the 2×2 contingency table (Sec. 11) must be > 0
  after continuity correction; a Haldane–Anscombe +0.5 correction is applied to all four cells whenever any cell
  is zero, applied uniformly (documented in `analysis/faers_signals.py`).
- Reports with unmapped or low-confidence (`fuzzy`/unverified) drug-name normalization are **retained in the
  database** with their mapping confidence but **excluded from the primary compound-level phenotype**; a
  sensitivity analysis (Sensitivity 3) re-includes them to test robustness.

## 5. Formulation / ester handling

- The **primary** analysis operates at the canonical **parent compound** level (e.g., all nandrolone esters map
  to `nandrolone`) because receptor pharmacology is predominantly a property of the released active parent
  steroid, not the ester, and because FAERS reporting volume per individual ester is often too sparse to
  support compound-level statistics.
- Ester/formulation identity is **preserved** in `faers_drugs.formulation_id` and `formulations` at all times —
  merging to parent happens only in the analysis layer, never destructively at ingestion.
- Sensitivity 2 re-runs the primary analysis restricted to reports mapped to the exact parent compound name only
  (excluding all ester-labeled reports), to test whether ester-inclusive aggregation changes conclusions.

## 6. Therapeutic-use vs. misuse classification inclusion (Aim 4 / H3)

- A report is eligible for the therapeutic-vs-misuse comparison only if it received a
  non-"unknown/unclassifiable" label under the conservative classification scheme (Sec. 22): therapeutic,
  misuse, or multi-AAS exposure. See `docs/database_schema.md` `report_classifications` table for stored
  evidence/confidence/method fields.
- A compound-stratum (e.g., "testosterone, misuse-associated reports") must have ≥ 20 classified reports to be
  included in the group-comparison statistics; smaller strata are reported descriptively only (counts, no
  inferential test).
- Multi-drug reports are **never** automatically classified as "stacking"/misuse solely because more than one
  drug is listed (explicit brief requirement, Sec. 5 and Sec. 22). Co-reported anabolic agents contribute
  evidence toward a misuse/multi-AAS label only in combination with at least one other qualifying evidence type
  (explicit abuse/misuse MedDRA term, product-use-error term, or documented supratherapeutic exposure) — the
  exact evidence-combination rule is implemented in `pipelines/faers/classification.py` and version-stamped
  (`classifier_version`) so re-runs are reproducible and auditable.

## 7. Assay/measurement heterogeneity exclusions

- Non-human orthologs are never pooled with human-target data in the primary analysis.
- Agonist/antagonist functional readouts are treated as a **separate measurement group** from binding
  affinity (Ki/Kd) — never combined into one pActivity column without explicit labeling of which functional
  readout is represented.
- Where ChEMBL and BindingDB both report a measurement for the same compound×target×type, provenance is kept
  separate (`bioactivities.source_record_id`, source database field) and never silently merged into a single
  unlabeled number; the aggregation rule across sources is the same median-within-homogeneous-group rule as
  Sec. 3 above, applied only after confirming assay comparability.

## 8. Versioning

Any change to a numeric threshold in this document must bump the version number at the top of the file and be
noted in `TODO.md` and, if it occurs after the primary analysis has been run once, logged in
`research/analysis_plan.md`'s Deviations table.
