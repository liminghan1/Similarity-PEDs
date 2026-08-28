# PubChem pipeline

Phase 4 of `TODO.md`. Retrieves compound identifiers/structure for the cohort in `cohort.py` via
PubChem PUG REST (https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) and upserts into `compounds`
(`backend/app/models/compounds.py`), validating each structure per `research/exclusion_rules.md` §2.

## Run

```bash
make db-up && make db-migrate   # if not already done
uv run python -m pipelines.pubchem.ingest
```

## Notes on the live API (verified 2026-08-27, not assumed from docs alone)

- Name → CID: `GET /compound/name/{name}/cids/JSON`. All 10 cohort names resolved to exactly one
  CID directly (no synonym fallback needed) -- verified with a live curl call before writing
  `cohort.py`, not guessed.
- Properties: `GET /compound/cid/{cid}/property/{...}/JSON`. **PubChem's legacy `CanonicalSMILES`
  and `IsomericSMILES` property names are deprecated.** The live API now returns `SMILES` (isomeric,
  includes stereochemistry when known) and `ConnectivitySMILES` (flat/2D, no stereochemistry) --
  confirmed empirically against a live request for testosterone (CID 6013), which additionally
  cross-validated our chemistry-module test fixtures (`backend/tests/test_chemistry.py`): the
  returned `ConnectivitySMILES` and `InChIKey` matched byte-for-byte.
- Rate limit: PubChem's usage policy allows up to 5 requests/second per IP; `client.py` throttles
  to ~3 req/s, which is more than sufficient for this project's small (~10-100 compound) cohorts
  and leaves headroom rather than running at the documented ceiling.
- No API key required at this volume.

## Structure validation

Every fetched structure must (a) parse and sanitize in RDKit and (b) have an RDKit-recomputed
molecular formula and molecular weight that agree with PubChem's reported values within tolerance
(±0.1 g/mol -- see `research/exclusion_rules.md` v0.2 change note for why ±0.02 was empirically too
tight given PubChem's 1-decimal MW rounding). A compound that fails validation is **not** inserted
or updated; it is logged as rejected and recorded in the `etl_runs` row for the pipeline run.
