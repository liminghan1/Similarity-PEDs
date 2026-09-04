# Data Quality Report

**Generated:** 2026-09-04T01:32:34.970903+00:00 at commit `3563110` -- regenerate with `uv run python -m analysis.generate_reports` after any pipeline re-run (project brief Sec. 43).

## Compound registry (Phases 3-4)

- Compounds: **10**
- Aliases: **36** (3.6 per compound on average)
- Formulations: **17**
- Invalid structures rejected: **0/10** (RDKit parse/sanitize + PubChem formula/MW cross-check, `research/exclusion_rules.md` Sec. 2)

## FAERS drug-name normalization (Phase 6)

- Matched drug-entry rows (one per cohort-compound mention in a report; the same raw string can recur across many reports): **11858**
- Distinct raw drug-name strings among those matches: **683**
- Mapping method distribution (final state in `faers_drugs`):

| Method | Count | % |
|---|---|---|
| exact_alias | 8958 | 75.5% |
| curated_match | 2889 | 24.4% |
| fuzzy_high_confidence | 10 | 0.1% |
| manual_review | 1 | 0.0% |

- **Non-cohort drug mentions** (aspirin, metformin, etc. -- co-reported drugs not in our 10-compound cohort) are deliberately **not** stored as `faers_drugs` rows (see `pipelines/faers/README.md` "What is deliberately NOT ingested"); the raw per-run count of such mentions evaluated during ingestion is recorded in each `etl_runs.notes` entry below, not as a separate rejected-mapping table, since these are not rejections of a cohort match -- they were never cohort drugs.
- Ambiguous matches flagged for manual review (never silently resolved): **1**.

## FAERS deduplication (Phase 6, `docs/faers_deduplication.md`)

- Deduplicated (latest-version) reports retained for analysis: **7433**
- Reports superseded by a newer version of the same case: **0** (0 observed with real data -- consistent with the empirical finding that openFDA's API already serves only the latest version per case; the defensive dedup pass ran regardless).

## Adverse-event terms (Phase 6-8)

- Individual reaction records ingested: **31061**
- Distinct MedDRA-style terms observed: **4057**
- Research-defined AE category taxonomy (`research/ae_categories.csv`): 107 curated term-to-category mappings (v0.2, expanded from an 80-term v0.1 seed list after matching against real ingested reaction data -- see that file's inline provenance notes).

## Receptor bioactivity coverage (Phase 5)

- Bioactivity records: **19** across **12** target rows (6 ChEMBL + 6 BindingDB, kept as separate provenance per compound receptor).
- Compounds with >=1 receptor measurement: **3/10** (testosterone, oxandrolone, stanozolol).
- Compounds with **zero** receptor measurements: **7/10** (boldenone, drostanolone, methandienone, methenolone, nandrolone, oxymetholone, trenbolone).
- Receptor phenotype matrix (primary, ChEMBL confidence>=8): **10/80 cells populated (12.5%)**.

## Excluded/rejected records

| Source | Read | Inserted | Rejected | Notes |
|---|---|---|---|---|
| pubchem | 10 | 10 | 0 |  |
| normalization | 49 | 49 | 0 |  |
| chembl | 46 | 19 | 28 | No ChEMBL match: methenolone / Skipped: 22 no relation/value, 5 potential_duplicate, 0 data_validity_comment flagged, 0 unrecognized units |
| bindingdb | 1659 | 0 | 0 | Matched compounds: none. Skipped: 0 non-qualifying measurement type, 0 unparseable affinity value, 0 unparseable SMILES. |
| normalization | 50 | 1 | 0 |  |
| faers | 7941 | 7422 | 2 | True per-compound totals (uncapped): {'testosterone': 32449, 'nandrolone': 460, 'oxandrolone': 526, 'stanozolol': 330, 'oxymetholone': 162, 'methandie... |
| normalization | 53 | 3 | 0 |  |
| faers | 7992 | 7433 | 2 | True per-compound totals (uncapped): {'testosterone': 32449, 'nandrolone': 466, 'oxandrolone': 526, 'stanozolol': 330, 'oxymetholone': 162, 'methandie... |

## Sparse safety-phenotype cells

See `artifacts/matrices/safety_signal_table_long.csv` for the full compound x category table with `sparse_cell` (a < 3 reports, `research/exclusion_rules.md` Sec. 4) flagged per cell -- 10/110 cells are flagged sparse in the current data and excluded from the wide logROR matrix used for similarity analysis, retained here for transparency.
