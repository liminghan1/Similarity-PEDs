# Database Schema Design

**Status:** Design document, precedes implementation (`backend/app/models/`). Implements the entity list in
Sec. 32 of the project brief. PostgreSQL, managed via SQLAlchemy models + Alembic migrations.

## Design principles

1. **Never silently merge entities.** Parent compound, ester/formulation, and brand alias are distinct rows with
   an explicit hierarchy (`compounds.parent_compound_id`, `formulations.compound_id`, `compound_aliases`).
2. **Preserve raw + derived side by side.** Raw reported drug names, raw bioactivity values/units, and raw FAERS
   report fields are always stored alongside their normalized/standardized counterparts — never overwritten.
3. **Provenance on every derived record.** Source database, source record ID, retrieval date, and (for ETL
   batches) a run ID linking to `etl_runs`.
4. **No fabricated fields.** Columns exist only for data this project actually populates from a real source;
   speculative columns are not added "for later."

## Entity-relationship overview

```
compounds (self-referencing parent_compound_id)
   |  1---N
   +--> compound_aliases
   |  1---N
   +--> formulations
   |  1---N (via bioactivities.compound_id)
   +--> bioactivities <---N---1 assays <---N---1 targets
   |  1---N (via faers_drugs.normalized_compound_id)
   +--> faers_drugs ---N---1 faers_reports
                          |  1---N
                          +--> faers_reactions
                          |  1---1
                          +--> report_classifications

etl_runs — independent audit table, referenced by source-tagged rows where useful
```

## Tables

### `compounds`
Canonical chemistry/identity registry. A row with `parent_compound_id IS NULL` is a root parent compound (e.g.
`nandrolone`). A row with `parent_compound_id` set is itself a distinct chemical entity that is nonetheless
conceptually "under" a parent for reporting purposes — in practice, for this project's cohort, `formulations`
handles ester/salt variants of a single molecule, so `parent_compound_id` is reserved for genuinely distinct
active parent steroids that are nonetheless grouped for a specific analysis (documented per-analysis, not
implied by the schema alone).

| column | type | notes |
|---|---|---|
| id | PK serial | |
| canonical_name | text, unique, not null | e.g. `nandrolone` |
| parent_compound_id | FK → compounds.id, nullable | self-referencing |
| pubchem_cid | integer, nullable, unique | |
| chembl_id | text, nullable, unique | |
| smiles | text, nullable | canonical SMILES as retrieved |
| isomeric_smiles | text, nullable | |
| inchikey | text, nullable, indexed | |
| molecular_formula | text, nullable | |
| molecular_weight | numeric, nullable | |
| drug_class | text, nullable | e.g. `anabolic-androgenic steroid` |
| created_at / updated_at | timestamptz | |
| source | text | e.g. `pubchem` |
| retrieved_at | timestamptz, nullable | |

### `compound_aliases`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| compound_id | FK → compounds.id, not null | always populated, even for a formulation-scoped alias (denormalized parent lookup) |
| formulation_id | FK → formulations.id, nullable | **set when the alias names a specific ester/formulation, not the bare parent** — e.g. `Deca-Durabolin`/`Deca` are aliases of the *nandrolone decanoate* formulation, not of unesterified nandrolone (Sec. 9: never conflate parent and derivative). Null for aliases that genuinely apply to the parent across all forms (chemical names, class-wide slang like `Tren`). Added in migration `add_formulation_scoping_to_aliases` after Phase 3 curation revealed most real brand names are formulation-specific, not parent-specific. |
| alias | text, not null | e.g. `Deca-Durabolin`, `Deca` |
| alias_type | enum: `brand`, `common_name`, `chemical_name`, `misspelling`, `abbreviation`, `other` | |
| source | text, nullable | citation/provenance for the alias |
| verified | boolean, default false | true only after manual/curated confirmation |
| created_at | timestamptz | |

unique constraint on (`alias`, `alias_type`) is intentionally **not** enforced globally — the same alias string
could plausibly be curated differently for different compounds pending review; ambiguous matches are resolved at
the mapping layer (`faers_drugs.mapping_method`/`mapping_confidence`), not by a DB constraint.

### `formulations`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| compound_id | FK → compounds.id, not null | parent active molecule |
| formulation_name | text, not null | e.g. `nandrolone decanoate` |
| ester_name | text, nullable | e.g. `decanoate` |
| route | text, nullable | e.g. `intramuscular injection`, `oral` |
| source | text, nullable | |
| created_at | timestamptz | |

### `targets`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| name | text, not null | e.g. `Androgen Receptor` |
| gene_symbol | text, nullable | e.g. `AR` |
| organism | text, nullable | e.g. `Homo sapiens` |
| source_target_id | text, nullable | e.g. ChEMBL target CHEMBL ID |
| source | text, nullable | `chembl`, `bindingdb` |

### `assays`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| source | text, not null | `chembl` \| `bindingdb` — kept separate per Sec. 27/Sec. 3 of the brief |
| source_assay_id | text, not null | |
| target_id | FK → targets.id, nullable | |
| assay_type | text, nullable | e.g. `B` (binding), `F` (functional) per ChEMBL convention |
| description | text, nullable | |
| organism | text, nullable | |
| confidence_score | integer, nullable | ChEMBL assay confidence (0–9) where applicable |
| assay_format | text, nullable | e.g. `cell-based`, `cell-free binding` — populated where determinable |

unique (`source`, `source_assay_id`)

### `bioactivities`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| compound_id | FK → compounds.id, not null | |
| assay_id | FK → assays.id, not null | |
| target_id | FK → targets.id, not null | denormalized for query convenience; must match assays.target_id |
| measurement_type | enum: `Ki`, `IC50`, `EC50`, `Kd` | never pooled across types (Sec. 2/Sec. 27) |
| relation | text | `=`, `>`, `<`, `>=`, `<=` |
| raw_value | numeric, nullable | as reported |
| raw_units | text, nullable | as reported, e.g. `nM`, `uM` |
| standardized_value_nm | numeric, nullable | converted to nM; conversion documented in ingestion code |
| p_activity | numeric, nullable | `9 - log10(standardized_value_nm)`; **only computed when relation = '='** (censored values keep `p_activity` NULL) |
| source | text, not null | `chembl` \| `bindingdb` |
| source_record_id | text, not null | |
| retrieved_at | timestamptz, nullable | |

### `faers_reports`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| case_id | text, not null | FAERS `safetyreportid` / `caseid` |
| version | integer, nullable | FAERS follow-up sequence number |
| source_report_id | text, not null | openFDA `safetyreportid` (case+version composite as reported) |
| received_date | date, nullable | |
| age | numeric, nullable | |
| age_unit | text, nullable | |
| sex | text, nullable | |
| country | text, nullable | |
| serious | boolean, nullable | |
| seriousness_death | boolean, nullable | |
| seriousness_hospitalization | boolean, nullable | |
| is_deduplicated_latest | boolean, not null, default true | true only for the record retained after dedup (Sec. 10); superseded versions retained with this flag false, never deleted |
| dedup_reason | text, nullable | populated for records where `is_deduplicated_latest = false` |

unique (`case_id`, `version`)

### `faers_drugs`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| report_id | FK → faers_reports.id, not null | |
| raw_name | text, not null | as reported (`medicinalproduct`) |
| normalized_compound_id | FK → compounds.id, nullable | null if unmapped |
| formulation_id | FK → formulations.id, nullable | |
| role | text, nullable | `PS` (primary suspect), `SS`, `C`, `I` per FAERS `drugcharacterization` |
| indication | text, nullable | as reported |
| mapping_method | enum: `exact_alias`, `curated_match`, `normalized_string_match`, `fuzzy_high_confidence`, `manual_review`, `unmapped` | |
| mapping_confidence | numeric, nullable | 0–1 |
| mapping_version | text, not null | version tag of the normalization ruleset used |

### `faers_reactions`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| report_id | FK → faers_reports.id, not null | |
| meddra_term | text, not null | as reported (`reactionmeddrapt`) — exact term always preserved |
| outcome | text, nullable | as reported, if available |

### `report_classifications`
| column | type | notes |
|---|---|---|
| report_id | PK, FK → faers_reports.id | one classification per report |
| use_classification | enum: `therapeutic`, `misuse`, `multi_aas_exposure`, `unknown` | |
| confidence | numeric, nullable | 0–1 |
| evidence | jsonb | structured list of evidence items that drove the label (Sec. 5/Sec. 22) |
| method | text, not null | rule-set description |
| classifier_version | text, not null | |

### `etl_runs`
| column | type | notes |
|---|---|---|
| id | PK serial | |
| source | text, not null | `pubchem` \| `chembl` \| `bindingdb` \| `faers` \| `normalization` |
| started_at | timestamptz, not null | |
| completed_at | timestamptz, nullable | |
| records_read | integer, nullable | |
| records_inserted | integer, nullable | |
| records_rejected | integer, nullable | |
| status | enum: `running`, `success`, `failed`, `partial` | |
| version | text, not null | code/version tag, ideally the Git commit hash |
| notes | text, nullable | |

## Indexes / constraints summary

- `compounds`: unique on `canonical_name`, `pubchem_cid`, `chembl_id`; index on `inchikey`, `parent_compound_id`.
- `bioactivities`: index on (`compound_id`, `target_id`, `measurement_type`); index on `assay_id`.
- `faers_reports`: unique on (`case_id`, `version`); index on `case_id`, `received_date`.
- `faers_drugs`: index on `normalized_compound_id`, `report_id`, `mapping_method`.
- `faers_reactions`: index on `meddra_term`, `report_id`.
- `report_classifications`: index on `use_classification`.

## Implementation

SQLAlchemy 2.0-style declarative models live in `backend/app/models/`. Alembic migrations live in
`backend/alembic/`. The first migration (`0001_initial_schema`) creates exactly the tables above; no seed data
is included in the migration itself (seed data, when curated, is loaded via a separate, explicitly-run script so
that "run the migration" and "trust the scientific content of the seed data" remain auditable as separate
actions).
