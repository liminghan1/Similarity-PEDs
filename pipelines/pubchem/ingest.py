"""Phase 4: fetch structures/identifiers for the initial cohort from PubChem and upsert
into the `compounds` table, validating each structure per research/exclusion_rules.md Sec. 2.

Usage:
    uv run python -m pipelines.pubchem.ingest
"""

from __future__ import annotations

import datetime as dt
import subprocess

from backend.app.analytics.chemistry import InvalidStructureError, compute_descriptors, parse_smiles
from backend.app.db.session import SessionLocal
from backend.app.models import Compound, EtlRun
from backend.app.models.etl import EtlStatus
from pipelines.pubchem.client import PubChemClient, PubChemLookupError
from pipelines.pubchem.cohort import INITIAL_COHORT

MOLECULAR_WEIGHT_TOLERANCE_G_PER_MOL = 0.1  # research/exclusion_rules.md Sec. 2 (v0.2)


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001 -- version tag is best-effort, must never block ingestion
        return "unknown"


def validate_structure(canonical_smiles: str, pubchem_formula: str, pubchem_mw: float) -> None:
    """Raise InvalidStructureError if the structure fails to parse or its RDKit-computed
    formula/MW disagree with PubChem's reported values beyond the documented tolerance."""
    mol = parse_smiles(canonical_smiles)  # raises InvalidStructureError on unparseable SMILES
    desc = compute_descriptors(canonical_smiles)
    if desc.molecular_formula != pubchem_formula:
        raise InvalidStructureError(
            f"RDKit formula {desc.molecular_formula!r} != PubChem formula {pubchem_formula!r} "
            f"for SMILES {canonical_smiles!r}"
        )
    if abs(desc.molecular_weight - pubchem_mw) > MOLECULAR_WEIGHT_TOLERANCE_G_PER_MOL:
        raise InvalidStructureError(
            f"RDKit MW {desc.molecular_weight:.3f} vs PubChem MW {pubchem_mw:.3f} differ by more than "
            f"{MOLECULAR_WEIGHT_TOLERANCE_G_PER_MOL} g/mol for SMILES {canonical_smiles!r}"
        )
    del mol  # parsed only to confirm validity; descriptors already recomputed it


def run() -> None:
    db = SessionLocal()
    run_record = EtlRun(
        source="pubchem",
        started_at=dt.datetime.now(dt.timezone.utc),
        status=EtlStatus.RUNNING,
        version=_code_version(),
        records_read=0,
        records_inserted=0,
        records_rejected=0,
    )
    db.add(run_record)
    db.commit()

    records_read = records_inserted = records_updated = records_rejected = 0
    rejected_names: list[str] = []

    try:
        with PubChemClient() as client:
            for entry in INITIAL_COHORT:
                records_read += 1
                try:
                    record = client.fetch_compound(entry.pubchem_query_name)
                    validate_structure(record.canonical_smiles, record.molecular_formula, record.molecular_weight)
                except (PubChemLookupError, InvalidStructureError) as exc:
                    records_rejected += 1
                    rejected_names.append(entry.canonical_name)
                    print(f"REJECTED {entry.canonical_name}: {exc}")
                    continue

                existing = db.query(Compound).filter_by(canonical_name=entry.canonical_name).one_or_none()
                if existing is None:
                    compound = Compound(canonical_name=entry.canonical_name)
                    db.add(compound)
                    records_inserted += 1
                else:
                    compound = existing
                    records_updated += 1

                compound.pubchem_cid = record.pubchem_cid
                compound.smiles = record.canonical_smiles
                compound.isomeric_smiles = record.isomeric_smiles
                compound.inchikey = record.inchikey
                compound.molecular_formula = record.molecular_formula
                compound.molecular_weight = record.molecular_weight
                compound.drug_class = entry.drug_class
                compound.source = "pubchem"
                compound.retrieved_at = dt.datetime.now(dt.timezone.utc)
                db.commit()
                print(f"OK {entry.canonical_name}: CID {record.pubchem_cid}, {record.molecular_formula}")

        run_record.status = EtlStatus.SUCCESS if records_rejected == 0 else EtlStatus.PARTIAL
    except Exception as exc:  # noqa: BLE001 -- record failure status before re-raising
        run_record.status = EtlStatus.FAILED
        run_record.notes = str(exc)
        db.commit()
        raise
    finally:
        run_record.completed_at = dt.datetime.now(dt.timezone.utc)
        run_record.records_read = records_read
        run_record.records_inserted = records_inserted
        run_record.records_rejected = records_rejected
        if rejected_names:
            run_record.notes = f"Rejected: {', '.join(rejected_names)}"
        db.commit()
        db.close()

    print(
        f"\nPubChem ingest complete: {records_read} read, {records_inserted} inserted, "
        f"{records_updated} updated, {records_rejected} rejected."
    )


if __name__ == "__main__":
    run()
