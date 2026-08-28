# BindingDB pipeline (optional complementary source)

Phase 5 of `TODO.md`. Per the project brief: "Use as an optional complementary source for
measured protein-ligand interactions. Keep BindingDB and ChEMBL source provenance separate."

## Run

```bash
uv run python -m pipelines.pubchem.ingest   # if not already done
uv run python -m pipelines.bindingdb.ingest
```

## Method

Unlike ChEMBL (queried compound-first, by exact InChIKey), BindingDB's REST API does not offer a
reliable compound-first exact-structure lookup for this use case -- `getTargetByCompound` (its
compound-search endpoint) returned only 2 hits for testosterone even at a similarity cutoff of 1.0
(exact match), neither of them AR/PR/GR/MR/ER, suggesting its similarity search does not reliably
surface exact hits the way a direct index lookup would. Instead, this pipeline queries **target-
first**: `getLigandsByUniprot` for each of the 6 receptor UniProt accessions (same targets as
`pipelines/chembl/targets.py`, cross-referenced to UniProt via ChEMBL's own target-component
cross-references), fetching every ligand BindingDB has for that target with a maximally inclusive
1 mM affinity cutoff, then matching each returned ligand's SMILES against our cohort by
**connectivity-layer InChIKey** (`backend/app/analytics/chemistry.py::connectivity_inchikey_block`)
-- stereo-independent, since we've already seen (in the PubChem/ChEMBL pipelines) that different
databases can assign stereo descriptors inconsistently for the same real compound.

## Live result (2026-08-27): zero matches

Fetched all 1,659 qualifying (Ki/IC50/EC50/Kd) records across the 6 targets (266 AR, 157 PR, 289
GR, 91 MR, 652 ERα, 204 ERβ) and matched every one's structure against all 10 cohort compounds.
**None matched.** This was verified by inspection before being accepted as a real result, not
assumed: the AR record set, for example, consists overwhelmingly of synthetic drug-candidate
chemotypes (fluorinated aromatic nitriles typical of non-steroidal SARM/antiandrogen medicinal
chemistry series), not classic steroidal AAS. This is consistent with BindingDB's curation being
drawn heavily from structure-activity-relationship medicinal chemistry papers, where a
well-characterized reference compound like testosterone is often *mentioned* but not
*extracted as a novel data point* the way ChEMBL's broader curation captures it (ChEMBL itself
found real testosterone-AR data, e.g. IC50 = 3.9 nM -- see `pipelines/chembl/README.md`).

This zero-match result is stored as a real outcome, not silently discarded: the pipeline still
runs, creates the 6 `targets` rows (`source='bindingdb'`, distinct `source_target_id` from the
ChEMBL rows for the same biological receptors), and records a `SUCCESS` `etl_runs` row with
`records_read=1659`, `records_inserted=0`. Per the project's own framing (Sec. 46 of the original
brief): "no detectable association" (here, no data overlap) is a valid, reportable result when the
methodology is sound -- it is not evidence of a pipeline defect, and the check above confirms that.

## Known limitations of this implementation

- `getLigandsByUniprot` does not expose per-assay/per-publication granularity (no assay ID,
  confidence score, or organism field) -- see the `Assay` row documentation in `ingest.py`.
  If a future compound match occurs, its `assays.confidence_score` will legitimately be `NULL`
  rather than a fabricated value.
- Only exact-structure (connectivity-layer) matches are captured. A future cohort expansion that
  includes close synthetic analogs (SARMs, esters as distinct entities with their own structure)
  might match more BindingDB records; the current 10-compound parent-only cohort does not.
- BindingDB also offers bulk TSV downloads with richer per-assay metadata; that path was not
  pursued here given the zero-match result above and the added complexity of a full-database
  bulk-file pipeline for an explicitly optional source -- documented as a possible future
  extension rather than implemented speculatively.
