# ChEMBL pipeline

Phase 5 of `TODO.md`. Retrieves receptor bioactivity (Ki/IC50/EC50/Kd against AR/PR/GR/MR/ERα/ERβ)
for every cohort compound with a matching ChEMBL molecule entry, and upserts into
`targets`/`assays`/`bioactivities` (`backend/app/models/pharmacology.py`).

## Run

```bash
uv run python -m pipelines.pubchem.ingest   # if not already done -- compounds must exist first
uv run python -m pipelines.chembl.ingest
```

## Targets (verified live, 2026-08-27 -- see `targets.py`)

| Receptor | ChEMBL target ID | UniProt |
|---|---|---|
| AR | CHEMBL1871 | P10275 |
| PR | CHEMBL208 | P06401 |
| GR | CHEMBL2034 | P04150 |
| MR | CHEMBL1994 | P08235 |
| ERα (ESR1) | CHEMBL206 | P03372 |
| ERβ (ESR2) | CHEMBL242 | Q92731 |

A plain-text ChEMBL target search for "estrogen receptor alpha/beta" surfaces the unrelated ERR1
orphan receptor and a combined "Estrogen receptor" PROTEIN FAMILY entry ahead of the correct
SINGLE PROTEIN targets -- CHEMBL206/CHEMBL242 were confirmed instead by searching
`target_synonym__icontains=ESR1`/`ESR2` and cross-checking the returned UniProt accessions.

## Molecule matching

Exact InChIKey match only (`GET /molecule.json?molecule_structures__standard_inchi_key=...`) --
no name-based fallback, to avoid a false-positive match on a different stereoisomer or salt form.
**methenolone has no ChEMBL molecule entry under its parent-compound InChIKey**: ChEMBL only
curates its *esters* (methenolone acetate = CHEMBL2106880, methenolone enanthate = CHEMBL2106949),
not the free parent steroid. This is a genuine coverage gap, not a bug -- confirmed by searching
ChEMBL by name. We deliberately do **not** substitute ester-form bioactivity for the parent
compound (the ester is typically a pharmacologically much weaker prodrug at the receptor, cleaved
in vivo to release the active parent -- using its own binding data would misrepresent the parent's
receptor pharmacology, the same "never conflate parent and derivative" principle applied to
aliases in `pipelines/normalization/README.md`).

## Filtering applied at ingestion (see `ingest.py` docstring and `research/exclusion_rules.md` §3)

- `standard_type` restricted server-side to Ki/IC50/EC50/Kd.
- Rows with no usable `standard_relation`/`standard_value` are skipped (e.g. ChEMBL's own
  "Not Determined" comment rows).
- Rows ChEMBL flags `potential_duplicate == 1` are skipped.
- Rows ChEMBL flags with a `data_validity_comment` (e.g. "Outside typical range") are skipped.
- `standardized_value_nm` uses `standard_units` via `units.py`; unrecognized units are stored raw
  without a standardized value rather than guessed.
- `p_activity` (`9 - log10(value_nM)`) is computed only for `relation == '='`.
- Assay `confidence_score`/`organism`/format (via `bao_label`) are stored for **every** row --
  filtering to high-confidence assays for the *primary* receptor phenotype matrix is a Phase 8
  analysis-layer decision, not an ingestion-time exclusion, so the raw layer stays complete.

**Cross-validation**: for testosterone-vs-AR IC50 = 3.9 nM, our `p_activity_from_nm` computes
8.409, matching ChEMBL's own `pchembl_value` (8.41) for that same record almost exactly --
confirms our pActivity formula agrees with ChEMBL's own convention.

## Live ingestion result (2026-08-27, 10-compound cohort)

19 bioactivity records inserted across testosterone (AR/GR/ERα/ERβ), oxandrolone (AR), and
stanozolol (ERα, GR). **6 of 10 cohort compounds (nandrolone, oxymetholone, methandienone,
drostanolone, boldenone, trenbolone) had matching ChEMBL molecules but zero qualifying Ki/IC50/
EC50/Kd activities against any of the 6 receptors.** This was verified directly against the live
API (not assumed): e.g. nandrolone's only ChEMBL AR-related entries are typed "RBA"/"Relative
binding affinity" (a relative, unitless measure vs. a reference ligand, not convertible to nM),
and oxymetholone's are typed "Potency" with no `standard_relation`. Both are correctly excluded by
our measurement-type/relation rules, not lost to a bug. Boldenone has literally zero ChEMBL
activity records against AR of any type. This sparsity is itself a real, reportable finding --
see `research/exclusion_rules.md` and the forthcoming missingness analysis (Phase 5/`TODO.md`) --
and is consistent with the project's stated expectation that receptor coverage for this compound
class would be a major limitation, likely reflecting that ChEMBL's curation draws heavily on
medicinal-chemistry drug-discovery literature, where these long-established steroids are less
often the subject of new receptor-binding characterization than novel candidate compounds.
