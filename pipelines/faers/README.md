# FAERS pipeline

Phase 6 of `TODO.md`. Fetches openFDA `/drug/event` reports mentioning any cohort compound (by
canonical name, curated alias, or formulation name), normalizes every drug entry in every fetched
report against the cohort (not just the entry that triggered the search match), extracts
reactions, and applies the conservative therapeutic-vs-misuse classifier.

## Run

```bash
uv run python -m pipelines.pubchem.ingest          # compounds must exist first
uv run python -m pipelines.normalization.seed_registry   # aliases/formulations must exist first
uv run python -m pipelines.faers.ingest
```

## API facts confirmed live (2026-08-28), not assumed from documentation

- **Rate limits**: 240 requests/minute + 1,000 requests/day per IP without a key; 240/minute +
  120,000/day with a key (`OPENFDA_API_KEY` in `.env`, optional). Confirmed against
  `open.fda.gov/apis/authentication/`.
- **Page size quirk**: `limit=999` works without a key; `limit=1000` exactly returns an
  `API_KEY_MISSING` error even though smaller and larger-than-typical limits (1, 100, 500, 999)
  do not. Undocumented; found empirically. We use `limit=500`.
- **Pagination ceiling**: `skip` beyond 25,000 is rejected ("Skip value must 25000 or less") --
  an Elasticsearch-backed constraint. See the per-compound cap below for how this interacts with
  our cohort.
- **OR-grouped queries work**: `patient.drug.medicinalproduct:("term1" "term2" ...)` matches any
  of several terms in one request, letting us issue one combined query per compound (canonical
  name + all aliases + all formulation names) rather than one request per alias string.
- **A report can list many drugs, and the query match is not necessarily drug #0**: a real fetched
  report (case 10028019, found searching for "nandrolone") is fundamentally about Soliris/
  eculizumab for PNH, with nandrolone appearing as drug entry #6 of 10, characterized as
  "concomitant." Our pipeline re-runs normalization matching across **every** drug entry in every
  fetched report against the full cohort (not just the query term), which is also how co-reported
  cohort compounds ("multi-AAS exposure") get detected.

## Live query volume (count-only queries, 2026-08-28)

| Compound | Total FAERS reports |
|---|---|
| testosterone | 31,733 |
| nandrolone | 367 |
| oxandrolone | 331 |
| stanozolol | 303 |
| oxymetholone | 106 |
| methenolone | 135 |
| trenbolone | 217 |
| boldenone | 47 |
| drostanolone | 34 |
| methandienone | 4 |

**Scope decision**: `MAX_REPORTS_PER_COMPOUND = 5000` in `ingest.py`. Only testosterone exceeds
this; all other 9 compounds are pulled in full. This keeps the initial pull's total request count
and processing time manageable (project brief: "Begin with a manageable time period if necessary.
Design for scaling later") while requiring essentially none of the anonymous 1,000-request/day
budget (the full run needs on the order of dozens of requests, not hundreds). The true, uncapped
total for every compound is recorded in `etl_runs.notes` on every run, so a capped pull is never
mistaken for a complete one, and methandienone's 4 total reports fall below the ≥20-report minimum
in `research/exclusion_rules.md` §4 -- it will be visibly excluded from the primary safety
phenotype, not silently absent.

## Real data findings that shaped this pipeline (see fixtures in `backend/tests/fixtures/`)

- **A real fatal multi-AAS case** (safetyreportid 10085268): a 24-year-old male, testosterone
  undecanoate + stanozolol + nandrolone decanoate + methandienone (raw text "METHANE
  DROSTENOLONE" -- "Methane" is real-world slang for methandienone, not in our original curated
  alias list; discovered here and promoted into `pipelines/normalization/aliases_seed.csv` with
  full provenance rather than left to chance fuzzy-matching), reactions including explicit "Drug
  abuse" and two fatal-outcome-coded events (carotid artery occlusion, intracranial venous sinus
  thrombosis). Our classifier correctly labels this MISUSE (not THERAPEUTIC or bare
  MULTI_AAS_EXPOSURE) on the explicit "Drug abuse" reaction term. This record is used directly in
  `backend/tests/test_faers_parsing.py` -- real data, not synthetic, per the project's
  no-fabrication principle.
- **A real therapeutic case** (safetyreportid 10028019): nandrolone prescribed for haemolytic
  anaemia (a genuine historical indication) as a concomitant drug in a Soliris/PNH case --
  correctly classified THERAPEUTIC on the recognized `drugindication` text, with no misuse
  evidence present.

## What is deliberately NOT ingested

- **Non-cohort drugs.** A fetched report's other, unrelated concomitant medications (aspirin,
  metformin, etc.) are not stored as `faers_drugs` rows -- only drug entries that match a cohort
  compound (any confidence tier, including `manual_review`-flagged ambiguous matches, which are
  stored precisely so they stay auditable rather than silently dropped). This keeps the dataset
  scoped to what the project's analyses actually use.
- **Cross-source duplicate reports** (FDA's own `duplicate`/`reportduplicate` fields) -- see
  `docs/faers_deduplication.md` for why this is a documented limitation, not an oversight.

## A real false-positive caught and fixed during this pipeline's first live run

The first full run's manual spot-check of `fuzzy_high_confidence` matches (62 rows) surfaced two
genuine errors, both at ratio ~0.90-0.92 -- indistinguishable by confidence score alone from
several *correct* matches in the same range (e.g. "TREBELONE ACETATE" -> trenbolone at 0.914):

- `ANDROSTANOLONE` (3 rows) matched to **drostanolone**, but androstanolone = dihydrotestosterone
  (DHT), a chemically distinct compound (drostanolone is 2alpha-methyl-DHT) -- confirmed via web
  search.
- `TRIENOLONE` (1 row) matched to **trenbolone**, but trienolone = methyltrienolone = metribolone
  = R1881, trenbolone's distinct 17-alpha-methylated, orally-active derivative -- confirmed via
  web search.

Fixed in `pipelines/faers/normalization.py` via `KNOWN_DISTINCT_COMPOUNDS`, a targeted block-list
checked before every matching tier (raising `FUZZY_THRESHOLD` was considered and rejected -- it
would have also excluded the correct matches in the same confidence range). See that module's
"False-positive guard" docstring section and `backend/tests/test_faers_normalization.py::
TestKnownDistinctCompoundGuard` for the regression tests. The FAERS tables were truncated and
re-ingested after the fix; **all numbers in this README are from the corrected run.**

The same spot-check also surfaced two genuine, high-value **correct** fuzzy matches worth
promoting to curated exact aliases (now in `pipelines/normalization/aliases_seed.csv`, both
`source=faers_data_discovery_2026-08-28`):
- `DROMOSTANOLONE`/`DROMOSTANOLONE PROPIONATE` (46 occurrences pre-fix) -- the official US
  USAN name for drostanolone.
- `NORTESTOSTERONE` (3 occurrences) -- a standard synonym for nandrolone (19-nortestosterone)
  that didn't exact-match the existing hyphenated alias.

After promotion, the fuzzy-tier match count dropped from 62 to 10 on re-ingestion, and every
remaining fuzzy match is a plausible spelling/language variant (e.g. `BOLDENON`, `TESTOSTERON` --
German-style names without the final "e"; `STANOZOLOLUM` -- a Latin pharmacopeial form), not
another cross-compound error.

## Live ingestion result (corrected run, 2026-08-28)

7,433 reports inserted across all 10 cohort compounds (testosterone 5,549; methenolone 720;
oxandrolone 528; nandrolone 463; stanozolol 331; boldenone 301; trenbolone 242; oxymetholone 162;
methandienone 153; drostanolone 95) -- **every compound clears the >=20-report minimum in
research/exclusion_rules.md** §4, unlike the receptor-bioactivity data in Phase 5 where 6/10
compounds had zero usable measurements. FAERS coverage for this cohort is real, substantive, and
far less sparse than ChEMBL/BindingDB coverage -- worth noting directly in the research report's
discussion of representation asymmetry between Aim 1 (molecular/pharmacological) and Aim 2
(safety) data availability.

Report-level classification distribution (v1 classifier, first live run): 6,099 unknown, 554
misuse, 450 therapeutic, 332 multi-AAS exposure. Per-compound patterns are consistent with known
pharmacology and worth noting: trenbolone and drostanolone (never approved for human therapeutic
use) show heavy misuse-classification skew and near-zero therapeutic classifications, while
testosterone (the only cohort compound in wide legitimate clinical use) has the largest absolute
THERAPEUTIC count (445) alongside its large MISUSE count (539) -- both a real reporting-volume
effect (testosterone dominates the cohort's total report count) and consistent with its dual
legitimate/misuse profile described in the literature (`research/literature_review.md`).

## Classifier term list: v1 -> v2 (2026-09-04)

`pipelines/faers/classification.py`'s v1 `MISUSE_EVIDENCE_REACTION_TERMS` treated every
misuse-suggestive reaction term as equally strong, sufficient-alone evidence -- including terms
that don't actually imply *intentional* non-medical use ("accidental overdose" is by definition
not intentional; "product use in unapproved indication" describes legitimate off-label
prescribing). v2 splits this into `HIGH_CONFIDENCE_MISUSE_TERMS` (sufficient alone) and
`AMBIGUOUS_EXPOSURE_TERMS` (never sufficient alone -- see the new `UseClassification.AMBIGUOUS_EXPOSURE`
outcome, tracked and reported separately rather than silently folded into MISUSE or UNKNOWN). This
also matters for the H3 AE-category comparison (`analysis/misuse_analysis.py`): "substance abuse"
is both a high-confidence misuse term *and* a `research/ae_categories.csv` "psychiatric" entry, a
source of classifier-outcome leakage that module's new leakage-controlled sensitivity variant
detects and controls for.

Re-classifying the same, already-ingested 7,433 reports with v2 (`uv run python -m
pipelines.faers.reclassify` -- no re-fetch from openFDA needed) changed the distribution to:
6,097 unknown, 450 therapeutic, **429** misuse, 357 multi-AAS exposure, **100** ambiguous exposure
(new). 125 reports (22.6% of v1's 554 MISUSE) moved out of MISUSE: 100 to AMBIGUOUS_EXPOSURE, 25 to
MULTI_AAS_EXPOSURE (reports with an ambiguous-tier term plus a second cohort compound co-reported,
which now resolves to MULTI_AAS_EXPOSURE rather than MISUSE). The resulting smaller MISUSE group
shows *stronger* seriousness/hospitalization associations in the H3 comparison than v1's larger,
noisier group did -- see `reports/research_report.md` Discussion and
`research/analysis_plan.md`'s Deviations table for the full before/after comparison.

## Classifier term list: known remaining first-pass status

The term lists (both tiers) and `THERAPEUTIC_INDICATION_TERMS` remain a first-pass curated list,
not a database-verified MedDRA extract. The live run's actual reaction/indication term
distribution (see `etl_runs.notes` and `reports/data_quality.md`) should be reviewed periodically
to check whether additional real, recurring terms belong on any list -- exactly the same discovery
process that surfaced "Methane" above.
