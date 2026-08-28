"""Phase 3: seed `formulations` and `compound_aliases` from the curated CSVs in this directory.

Curated, not derived from an API -- every row in the source CSVs carries a `source` and
(for aliases) a `verified` flag documenting how confident the curation is (research/
exclusion_rules.md and Sec. 9/Sec. 2 of the project brief: never fabricate scientific/reference
data, and maintain a clearly documented curated-data layer with citations). Rows marked
verified=False are still loaded (they are usable, well-sourced pharmacology knowledge) but are
flagged for a future manual citation pass -- see pipelines/normalization/README.md.

Must run after pipelines/pubchem/ingest.py, since aliases and formulations reference an
already-existing `compounds` row by canonical_name.

Usage:
    uv run python -m pipelines.normalization.seed_registry
"""

from __future__ import annotations

import csv
import datetime as dt
import subprocess
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.models import Compound, CompoundAlias, EtlRun, Formulation
from backend.app.models.compounds import AliasType
from backend.app.models.etl import EtlStatus

SEED_DIR = Path(__file__).parent
FORMULATIONS_CSV = SEED_DIR / "formulations_seed.csv"
ALIASES_CSV = SEED_DIR / "aliases_seed.csv"


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _str_to_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes")


def seed_formulations(db) -> tuple[int, int, list[str]]:
    inserted = updated = 0
    rejected: list[str] = []
    with FORMULATIONS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            compound = db.query(Compound).filter_by(canonical_name=row["canonical_name"]).one_or_none()
            if compound is None:
                rejected.append(f"formulation {row['formulation_name']!r}: unknown compound {row['canonical_name']!r}")
                continue
            existing = (
                db.query(Formulation)
                .filter_by(compound_id=compound.id, formulation_name=row["formulation_name"])
                .one_or_none()
            )
            if existing is None:
                existing = Formulation(compound_id=compound.id, formulation_name=row["formulation_name"])
                db.add(existing)
                inserted += 1
            else:
                updated += 1
            existing.ester_name = row["ester_name"] or None
            existing.route = row["route"] or None
            existing.source = row["source"] or None
    db.commit()
    return inserted, updated, rejected


def seed_aliases(db) -> tuple[int, int, list[str]]:
    inserted = updated = 0
    rejected: list[str] = []
    with ALIASES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            compound = db.query(Compound).filter_by(canonical_name=row["canonical_name"]).one_or_none()
            if compound is None:
                rejected.append(f"alias {row['alias']!r}: unknown compound {row['canonical_name']!r}")
                continue

            formulation_id = None
            formulation_name = row.get("formulation_name", "").strip()
            if formulation_name:
                formulation = (
                    db.query(Formulation)
                    .filter_by(compound_id=compound.id, formulation_name=formulation_name)
                    .one_or_none()
                )
                if formulation is None:
                    rejected.append(
                        f"alias {row['alias']!r}: unknown formulation {formulation_name!r} for {row['canonical_name']!r} "
                        "(seed_formulations must run first)"
                    )
                    continue
                formulation_id = formulation.id

            try:
                alias_type = AliasType(row["alias_type"])
            except ValueError:
                rejected.append(f"alias {row['alias']!r}: invalid alias_type {row['alias_type']!r}")
                continue

            existing = (
                db.query(CompoundAlias)
                .filter_by(compound_id=compound.id, alias=row["alias"], alias_type=alias_type)
                .one_or_none()
            )
            if existing is None:
                existing = CompoundAlias(compound_id=compound.id, alias=row["alias"], alias_type=alias_type)
                db.add(existing)
                inserted += 1
            else:
                updated += 1
            existing.formulation_id = formulation_id
            existing.source = row["source"] or None
            existing.verified = _str_to_bool(row["verified"])
    db.commit()
    return inserted, updated, rejected


def run() -> None:
    db = SessionLocal()
    run_record = EtlRun(
        source="normalization",
        started_at=dt.datetime.now(dt.timezone.utc),
        status=EtlStatus.RUNNING,
        version=_code_version(),
    )
    db.add(run_record)
    db.commit()

    try:
        f_ins, f_upd, f_rej = seed_formulations(db)
        a_ins, a_upd, a_rej = seed_aliases(db)
        rejected = f_rej + a_rej
        run_record.status = EtlStatus.SUCCESS if not rejected else EtlStatus.PARTIAL
        run_record.records_read = f_ins + f_upd + len(f_rej) + a_ins + a_upd + len(a_rej)
        run_record.records_inserted = f_ins + a_ins
        run_record.records_rejected = len(rejected)
        if rejected:
            run_record.notes = "; ".join(rejected)
        db.commit()
        print(f"Formulations: {f_ins} inserted, {f_upd} updated, {len(f_rej)} rejected.")
        print(f"Aliases: {a_ins} inserted, {a_upd} updated, {len(a_rej)} rejected.")
        for r in rejected:
            print(f"REJECTED: {r}")
    except Exception as exc:  # noqa: BLE001
        run_record.status = EtlStatus.FAILED
        run_record.notes = str(exc)
        db.commit()
        raise
    finally:
        run_record.completed_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        db.close()


if __name__ == "__main__":
    run()
