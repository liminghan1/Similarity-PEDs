"""Phase 5: fetch receptor bioactivity (Ki/IC50/EC50/Kd) for the 6 targets in targets.py against
every cohort compound that has a matching ChEMBL molecule, and upsert into targets/assays/
bioactivities (backend/app/models/pharmacology.py).

Filtering applied at ingestion (research/exclusion_rules.md Sec. 3, and documented further in
pipelines/chembl/README.md):
    - measurement_type restricted server-side to Ki/IC50/EC50/Kd (never pooled as equivalent).
    - rows with no usable standard_relation/standard_value are skipped (nothing to store).
    - rows ChEMBL itself flags as a likely duplicate (potential_duplicate == 1) are skipped.
    - rows ChEMBL flags with a data_validity_comment (e.g. "Outside typical range") are skipped.
    - standardized_value_nm and p_activity are computed only when unit conversion is recognized
      (pipelines/chembl/units.py) and, for p_activity, only when relation == '='.
    - assay confidence_score, organism, and format are stored on every row -- filtering by
      confidence for the *primary* receptor phenotype matrix is a Phase 8 analysis-layer decision
      (research/exclusion_rules.md Sec. 3: >=8 preferred), not an ingestion-time exclusion, so the
      raw layer stays complete and inspectable.

Usage:
    uv run python -m pipelines.chembl.ingest
"""

from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import dataclass

from backend.app.analytics.signals import p_activity_from_nm
from backend.app.db.session import SessionLocal
from backend.app.models import Assay, Bioactivity, Compound, EtlRun, Target
from backend.app.models.etl import EtlStatus
from backend.app.models.pharmacology import MeasurementType
from pipelines.chembl.client import ChemblClient, ChemblLookupError
from pipelines.chembl.targets import RECEPTOR_TARGETS
from pipelines.chembl.units import to_nanomolar


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class ActivityEvaluation:
    keep: bool
    skip_reason: str | None = None
    measurement_type: str | None = None
    relation: str | None = None
    raw_value: float | None = None
    raw_units: str | None = None
    standardized_value_nm: float | None = None
    p_activity: float | None = None
    unrecognized_units: bool = False


def evaluate_activity(activity: dict) -> ActivityEvaluation:
    """Pure filtering/standardization logic for one raw ChEMBL activity record, kept separate
    from the DB-writing loop in run() so it is independently unit-testable
    (backend/tests/test_chembl_pipeline.py) against real fixture payloads."""
    relation = activity.get("standard_relation")
    raw_standard_value = activity.get("standard_value")
    if relation is None or raw_standard_value is None:
        return ActivityEvaluation(keep=False, skip_reason="no_relation_or_value")
    if activity.get("potential_duplicate") == 1:
        return ActivityEvaluation(keep=False, skip_reason="potential_duplicate")
    if activity.get("data_validity_comment") is not None:
        return ActivityEvaluation(keep=False, skip_reason="data_validity_flagged")

    standard_value = float(raw_standard_value)
    standard_units = activity.get("standard_units")
    standardized_value_nm = to_nanomolar(standard_value, standard_units) if standard_units else None
    unrecognized_units = standardized_value_nm is None

    p_activity = None
    if relation == "=" and standardized_value_nm is not None and standardized_value_nm > 0:
        p_activity = p_activity_from_nm(standardized_value_nm)

    return ActivityEvaluation(
        keep=True,
        measurement_type=activity["standard_type"],
        relation=relation,
        raw_value=_safe_float(activity.get("value")),
        raw_units=activity.get("units"),
        standardized_value_nm=standardized_value_nm,
        p_activity=p_activity,
        unrecognized_units=unrecognized_units,
    )


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def get_or_create_target(db, receptor) -> Target:
    target = db.query(Target).filter_by(source="chembl", source_target_id=receptor.chembl_target_id).one_or_none()
    if target is None:
        target = Target(
            name=receptor.full_name,
            gene_symbol=receptor.gene_symbol,
            organism=receptor.organism,
            source_target_id=receptor.chembl_target_id,
            source="chembl",
        )
        db.add(target)
        db.flush()
    return target


def get_or_create_assay(db, client: ChemblClient, target: Target, assay_chembl_id: str) -> Assay:
    assay = db.query(Assay).filter_by(source="chembl", source_assay_id=assay_chembl_id).one_or_none()
    if assay is not None:
        return assay
    details = client.get_assay(assay_chembl_id)
    assay = Assay(
        source="chembl",
        source_assay_id=assay_chembl_id,
        target_id=target.id,
        assay_type=details.get("assay_type"),
        description=details.get("description"),
        organism=details.get("assay_organism"),
        confidence_score=details.get("confidence_score"),
        assay_format=details.get("bao_label"),
    )
    db.add(assay)
    db.flush()
    return assay


def run() -> None:
    db = SessionLocal()
    run_record = EtlRun(
        source="chembl",
        started_at=dt.datetime.now(dt.timezone.utc),
        status=EtlStatus.RUNNING,
        version=_code_version(),
    )
    db.add(run_record)
    db.commit()

    compounds_with_no_chembl_match: list[str] = []
    skipped_no_relation = skipped_duplicate = skipped_validity_flagged = skipped_bad_units = 0
    records_read = records_inserted = records_updated = 0

    try:
        with ChemblClient() as client:
            targets_by_receptor = {r.short_name: get_or_create_target(db, r) for r in RECEPTOR_TARGETS}
            db.commit()

            compounds = db.query(Compound).filter(Compound.inchikey.isnot(None)).all()
            for compound in compounds:
                try:
                    chembl_molecule_id = client.get_molecule_chembl_id_by_inchikey(compound.inchikey)
                except ChemblLookupError as exc:
                    compounds_with_no_chembl_match.append(f"{compound.canonical_name} (ambiguous: {exc})")
                    print(f"AMBIGUOUS CHEMBL MATCH: {compound.canonical_name}: {exc}")
                    continue
                if chembl_molecule_id is None:
                    compounds_with_no_chembl_match.append(compound.canonical_name)
                    print(f"NO CHEMBL MATCH: {compound.canonical_name} (InChIKey {compound.inchikey})")
                    continue

                for receptor in RECEPTOR_TARGETS:
                    target = targets_by_receptor[receptor.short_name]
                    activities = list(client.iterate_activities(chembl_molecule_id, receptor.chembl_target_id))
                    kept_for_pair = 0

                    for activity in activities:
                        records_read += 1
                        evaluation = evaluate_activity(activity)
                        if not evaluation.keep:
                            if evaluation.skip_reason == "no_relation_or_value":
                                skipped_no_relation += 1
                            elif evaluation.skip_reason == "potential_duplicate":
                                skipped_duplicate += 1
                            elif evaluation.skip_reason == "data_validity_flagged":
                                skipped_validity_flagged += 1
                            continue
                        if evaluation.unrecognized_units:
                            skipped_bad_units += 1

                        assay = get_or_create_assay(db, client, target, activity["assay_chembl_id"])

                        source_record_id = str(activity["activity_id"])
                        existing = (
                            db.query(Bioactivity)
                            .filter_by(source="chembl", source_record_id=source_record_id)
                            .one_or_none()
                        )
                        if existing is None:
                            existing = Bioactivity(
                                compound_id=compound.id,
                                assay_id=assay.id,
                                target_id=target.id,
                                source="chembl",
                                source_record_id=source_record_id,
                            )
                            db.add(existing)
                            records_inserted += 1
                        else:
                            records_updated += 1

                        existing.measurement_type = MeasurementType(evaluation.measurement_type)
                        existing.relation = evaluation.relation
                        existing.raw_value = evaluation.raw_value
                        existing.raw_units = evaluation.raw_units
                        existing.standardized_value_nm = evaluation.standardized_value_nm
                        existing.p_activity = evaluation.p_activity
                        existing.retrieved_at = dt.datetime.now(dt.timezone.utc)
                        kept_for_pair += 1

                    db.commit()
                    if activities:
                        print(
                            f"{compound.canonical_name} x {receptor.short_name}: "
                            f"{len(activities)} fetched, {kept_for_pair} kept"
                        )

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
        notes = []
        if compounds_with_no_chembl_match:
            notes.append(f"No ChEMBL match: {', '.join(compounds_with_no_chembl_match)}")
        notes.append(
            f"Skipped: {skipped_no_relation} no relation/value, {skipped_duplicate} potential_duplicate, "
            f"{skipped_validity_flagged} data_validity_comment flagged, {skipped_bad_units} unrecognized units"
        )
        run_record.notes = " | ".join(notes)
        run_record.records_rejected = (
            len(compounds_with_no_chembl_match) + skipped_no_relation + skipped_duplicate + skipped_validity_flagged
        )
        db.commit()
        db.close()

    print(
        f"\nChEMBL ingest complete: {records_read} activities read, {records_inserted} inserted, "
        f"{records_updated} updated.\n"
        f"Skipped: {skipped_no_relation} no relation/value, {skipped_duplicate} potential duplicates, "
        f"{skipped_validity_flagged} data-validity-flagged, {skipped_bad_units} unrecognized units "
        "(stored raw without standardized_value_nm).\n"
        f"Compounds with no ChEMBL match: {compounds_with_no_chembl_match or 'none'}"
    )


if __name__ == "__main__":
    run()
