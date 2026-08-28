"""Phase 5 (BindingDB, optional complementary source): fetch all ligand-affinity records
BindingDB has for each of the 6 receptor targets (pipelines/bindingdb/targets.py), match them
against our cohort compounds by structure (connectivity-layer InChIKey -- see
backend/app/analytics/chemistry.py::connectivity_inchikey_block), and store any matches with
source='bindingdb', kept strictly separate from ChEMBL provenance (Sec. 3 of the project brief).

BindingDB's getLigandsByUniprot endpoint does not expose per-assay/per-paper granularity the way
ChEMBL's activity+assay endpoints do (no assay ID, no confidence score, no organism field) -- we
represent this honestly rather than inventing structure that isn't there: one synthetic `Assay`
row per target (source_assay_id = "bdb-uniprot-{UniProt ID}"), documented in its own
`description` field as an aggregate, non-granular placeholder, with confidence_score left NULL
(never fabricated).

Usage:
    uv run python -m pipelines.bindingdb.ingest
"""

from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import dataclass

from backend.app.analytics.chemistry import InvalidStructureError, connectivity_inchikey_block
from backend.app.analytics.signals import p_activity_from_nm
from backend.app.db.session import SessionLocal
from backend.app.models import Assay, Bioactivity, Compound, EtlRun, Target
from backend.app.models.etl import EtlStatus
from backend.app.models.pharmacology import MeasurementType
from pipelines.bindingdb.client import BindingDbClient
from pipelines.bindingdb.targets import BINDINGDB_TARGETS

QUALIFYING_MEASUREMENT_TYPES = {"Ki", "IC50", "EC50", "Kd"}


@dataclass(frozen=True)
class ParsedAffinity:
    relation: str
    value_nm: float


def parse_affinity(raw: str) -> ParsedAffinity | None:
    """Parse BindingDB's free-text affinity string (e.g. " 219", ">10000", "<0.5") into a
    relation + numeric nM value. Returns None if the text isn't parseable as a number, rather
    than guessing (e.g. some BindingDB fields can contain non-numeric placeholders)."""
    text = raw.strip()
    relation = "="
    if text.startswith(">") or text.startswith("<"):
        relation, text = text[0], text[1:].strip()
    try:
        value = float(text)
    except ValueError:
        return None
    return ParsedAffinity(relation=relation, value_nm=value)


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def get_or_create_target(db, receptor) -> Target:
    target = db.query(Target).filter_by(source="bindingdb", source_target_id=receptor.uniprot_id).one_or_none()
    if target is None:
        target = Target(
            name=receptor.full_name,
            gene_symbol=None,
            organism="Homo sapiens",
            source_target_id=receptor.uniprot_id,
            source="bindingdb",
        )
        db.add(target)
        db.flush()
    return target


def get_or_create_assay(db, target: Target, uniprot_id: str) -> Assay:
    source_assay_id = f"bdb-uniprot-{uniprot_id}"
    assay = db.query(Assay).filter_by(source="bindingdb", source_assay_id=source_assay_id).one_or_none()
    if assay is None:
        assay = Assay(
            source="bindingdb",
            source_assay_id=source_assay_id,
            target_id=target.id,
            assay_type=None,
            description=(
                "Aggregate BindingDB ligand-target affinity data via the getLigandsByUniprot "
                "REST endpoint -- this endpoint does not expose per-assay/per-publication "
                "granularity, so this Assay row represents all matched BindingDB records for "
                f"this target (UniProt {uniprot_id}), not a single experiment."
            ),
            organism="Homo sapiens",
            confidence_score=None,
            assay_format=None,
        )
        db.add(assay)
        db.flush()
    return assay


def run() -> None:
    db = SessionLocal()
    run_record = EtlRun(
        source="bindingdb",
        started_at=dt.datetime.now(dt.timezone.utc),
        status=EtlStatus.RUNNING,
        version=_code_version(),
    )
    db.add(run_record)
    db.commit()

    records_read = records_inserted = records_updated = 0
    skipped_type = skipped_unparseable = skipped_bad_structure = 0
    matched_compound_names: set[str] = set()

    try:
        compounds = db.query(Compound).filter(Compound.smiles.isnot(None)).all()
        compound_blocks: dict[str, Compound] = {}
        for compound in compounds:
            try:
                compound_blocks[connectivity_inchikey_block(compound.smiles)] = compound
            except InvalidStructureError:
                continue  # already flagged during PubChem ingestion; nothing new to log here

        with BindingDbClient() as client:
            for receptor in BINDINGDB_TARGETS:
                target = get_or_create_target(db, receptor)
                db.commit()
                affinities = client.get_ligands_by_uniprot(receptor.uniprot_id)
                print(f"{receptor.short_name} (UniProt {receptor.uniprot_id}): {len(affinities)} BindingDB records")

                for record in affinities:
                    records_read += 1
                    affinity_type = record.get("bdb.affinity_type")
                    if affinity_type not in QUALIFYING_MEASUREMENT_TYPES:
                        skipped_type += 1
                        continue

                    raw_smiles = (record.get("bdb.smile") or "").replace("|r|", "").strip()
                    if not raw_smiles:
                        skipped_bad_structure += 1
                        continue
                    try:
                        block = connectivity_inchikey_block(raw_smiles)
                    except InvalidStructureError:
                        skipped_bad_structure += 1
                        continue

                    compound = compound_blocks.get(block)
                    if compound is None:
                        continue  # not one of our cohort compounds -- expected for most records

                    parsed = parse_affinity(record.get("bdb.affinity", ""))
                    if parsed is None:
                        skipped_unparseable += 1
                        continue

                    assay = get_or_create_assay(db, target, receptor.uniprot_id)
                    source_record_id = f"bdb-{record.get('bdb.monomerid')}-{affinity_type}"
                    existing = (
                        db.query(Bioactivity)
                        .filter_by(source="bindingdb", source_record_id=source_record_id)
                        .one_or_none()
                    )
                    if existing is None:
                        existing = Bioactivity(
                            compound_id=compound.id,
                            assay_id=assay.id,
                            target_id=target.id,
                            source="bindingdb",
                            source_record_id=source_record_id,
                        )
                        db.add(existing)
                        records_inserted += 1
                    else:
                        records_updated += 1

                    existing.measurement_type = MeasurementType(affinity_type)
                    existing.relation = parsed.relation
                    existing.raw_value = parsed.value_nm
                    existing.raw_units = "nM"
                    existing.standardized_value_nm = parsed.value_nm
                    existing.p_activity = (
                        p_activity_from_nm(parsed.value_nm)
                        if parsed.relation == "=" and parsed.value_nm > 0
                        else None
                    )
                    existing.retrieved_at = dt.datetime.now(dt.timezone.utc)
                    matched_compound_names.add(compound.canonical_name)
                    db.commit()

        run_record.status = EtlStatus.SUCCESS
    except Exception as exc:  # noqa: BLE001
        run_record.status = EtlStatus.FAILED
        run_record.notes = str(exc)
        db.commit()
        raise
    finally:
        run_record.completed_at = dt.datetime.now(dt.timezone.utc)
        run_record.records_read = records_read
        run_record.records_inserted = records_inserted
        run_record.records_rejected = skipped_type + skipped_unparseable + skipped_bad_structure
        run_record.notes = (
            f"Matched compounds: {sorted(matched_compound_names) or 'none'}. "
            f"Skipped: {skipped_type} non-qualifying measurement type, {skipped_unparseable} "
            f"unparseable affinity value, {skipped_bad_structure} unparseable SMILES."
        )
        db.commit()
        db.close()

    print(
        f"\nBindingDB ingest complete: {records_read} records read across {len(BINDINGDB_TARGETS)} targets, "
        f"{records_inserted} inserted, {records_updated} updated.\n"
        f"Matched cohort compounds: {sorted(matched_compound_names) or 'NONE -- see pipelines/bindingdb/README.md'}"
    )


if __name__ == "__main__":
    run()
