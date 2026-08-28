# Compound registry normalization (aliases + formulations)

Phase 3 of `TODO.md`. Seeds `formulations` and `compound_aliases` (`backend/app/models/compounds.py`)
from curated CSVs. Must run **after** `pipelines/pubchem/ingest.py`, which creates the `compounds`
rows these files reference by `canonical_name`.

```bash
uv run python -m pipelines.pubchem.ingest        # if not already run
uv run python -m pipelines.normalization.seed_registry
```

## Files

- `formulations_seed.csv` — ester/route variants of each cohort parent compound.
- `aliases_seed.csv` — brand names, abbreviations, and chemical-name synonyms. Each row has a
  `formulation_name` column: **blank means the alias applies to the parent compound across all
  its forms** (e.g. `Tren`, or a chemical name); a non-blank value scopes the alias to that
  specific ester/formulation (e.g. `Deca-Durabolin` names nandrolone *decanoate*, not
  unesterified nandrolone). This distinction exists because the project brief (Sec. 9) explicitly
  requires never conflating a parent molecule with a specific derivative -- most real brand names
  in this compound class in fact name a specific ester, not the bare hormone.

## Curation methodology and confidence

This is a curated data layer, not an API pull, so every alias row carries a `source` and a
`verified` boolean rather than being asserted as fact:

- `verified = True`, `source = web_search_2026-08-27`: the alias/brand mapping was explicitly
  confirmed in a real web search performed during this session (see
  `research/literature_review.md` for the general search log; the specific query was
  "anabolic steroid common esters brand names testosterone nandrolone oxandrolone stanozolol
  oxymetholone methandienone drostanolone methenolone boldenone trenbolone", 2026-08-27).
- `verified = False`, `source = curated_seed_v1`: the mapping reflects well-established
  pharmacology reference knowledge (the kind found in standard steroid-chemistry references and
  regulatory/clinical literature) but was **not** independently re-confirmed against a specific
  citable source in this session. These are plausible and, for the well-known entries (e.g.
  Deca-Durabolin, Anavar's underlying ester-free status), very likely correct, but per the
  project's "do not fabricate / do not present curated data as verified fact" rule they are
  flagged for a future manual citation pass rather than marked verified.
- One exception is independently, mechanically verified rather than by web search: the
  `metandienone` == `methandienone` synonym row, confirmed by querying PubChem PUG REST for both
  names and observing they resolve to the same CID (6300) -- see `pipelines/pubchem/README.md`.

**Outstanding work** (tracked in `TODO.md`): cross-check every `verified = False` row against a
citable primary source (e.g. DrugBank, an FDA label, or a peer-reviewed pharmacology reference)
before this data is used in any manuscript-facing claim. None of these rows currently affect the
project's statistical results -- they only affect FAERS drug-name normalization coverage
(Phase 6), where `mapping_confidence` on `faers_drugs` additionally reflects match quality
independent of alias-curation confidence.

## Why this isn't just a database seed baked into the migration

Per `docs/database_schema.md`: "no seed data is included in the migration itself... so that 'run
the migration' and 'trust the scientific content of the seed data' remain auditable as separate
actions." Running `seed_registry.py` is an explicit, logged (`etl_runs`) step, not a side effect
of `alembic upgrade head`.
