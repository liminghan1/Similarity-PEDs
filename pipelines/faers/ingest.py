"""Phase 6: fetch FAERS/openFDA adverse-event reports mentioning any cohort compound (by
canonical name, curated alias, or formulation name), normalize drug names against the cohort
(pipelines/faers/normalization.py), extract reactions (pipelines/faers/reactions.py), and apply
the conservative therapeutic-vs-misuse classifier (pipelines/faers/classification.py).

Scope decision (documented, per project brief: "Begin with a manageable time period if
necessary. Design for scaling later."): `MAX_REPORTS_PER_COMPOUND` caps how many reports this
initial pull retrieves for any one compound. Only testosterone (31,733 total reports found live)
exceeds this cap; all other 9 cohort compounds are pulled in full. The true total (uncapped) count
is always recorded in `etl_runs.notes` so a capped pull is never mistaken for a complete one. See
pipelines/faers/README.md for the exact numbers from the live run.

Usage:
    uv run python -m pipelines.faers.ingest
"""

from __future__ import annotations

import datetime as dt
import subprocess
from collections import Counter

from sqlalchemy import func

from backend.app.db.session import SessionLocal
from backend.app.models import (
    Compound,
    CompoundAlias,
    EtlRun,
    FaersDrug,
    FaersReaction,
    FaersReport,
    Formulation,
    ReportClassification,
)
from backend.app.models.etl import EtlStatus
from backend.app.models.faers import MappingMethod
from pipelines.faers.client import OpenFdaClient
from pipelines.faers.normalization import build_index
from pipelines.faers.parsing import ParsedReport, parse_report

MAX_REPORTS_PER_COMPOUND = 5000
COMMIT_EVERY = 200


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def build_search_terms(db) -> dict[int, list[str]]:
    """compound_id -> [canonical_name, *aliases, *formulation_names]."""
    terms: dict[int, list[str]] = {}
    for compound in db.query(Compound).all():
        terms[compound.id] = [compound.canonical_name]
    for alias in db.query(CompoundAlias).all():
        terms.setdefault(alias.compound_id, []).append(alias.alias)
    for formulation in db.query(Formulation).all():
        terms.setdefault(formulation.compound_id, []).append(formulation.formulation_name)
    return terms


def build_global_index(db):
    rows = []
    compounds_by_id = {c.id: c.canonical_name for c in db.query(Compound).all()}
    for compound in db.query(Compound).all():
        rows.append((compound.canonical_name, compound.id, compound.canonical_name, None))
    for alias in db.query(CompoundAlias).all():
        rows.append((alias.alias, alias.compound_id, compounds_by_id[alias.compound_id], alias.formulation_id))
    for formulation in db.query(Formulation).all():
        rows.append(
            (formulation.formulation_name, formulation.compound_id, compounds_by_id[formulation.compound_id], formulation.id)
        )
    return build_index(rows)


def build_openfda_query(terms: list[str]) -> str:
    quoted = " ".join(f'"{t}"' for t in terms)
    return f"patient.drug.medicinalproduct:({quoted})"


def persist_report(db, report: ParsedReport) -> str:
    """Returns 'inserted', 'updated', or 'skipped_no_cohort_match'."""
    if not report.cohort_drugs:
        return "skipped_no_cohort_match"

    existing = db.query(FaersReport).filter_by(case_id=report.case_id, version=report.version).one_or_none()
    if existing is None:
        db_report = FaersReport(
            case_id=report.case_id,
            version=report.version,
            source_report_id=report.source_report_id,
            received_date=report.received_date,
            age=report.age,
            age_unit=report.age_unit,
            sex=report.sex,
            country=report.country,
            serious=report.serious,
            seriousness_death=report.seriousness_death,
            seriousness_hospitalization=report.seriousness_hospitalization,
        )
        db.add(db_report)
        db.flush()
        outcome = "inserted"
    else:
        db_report = existing
        outcome = "updated"

    for drug in report.drugs:
        if drug.match.mapping_method == MappingMethod.UNMAPPED:
            continue
        db.add(
            FaersDrug(
                report_id=db_report.id,
                raw_name=drug.raw_name,
                normalized_compound_id=drug.match.compound_id,
                formulation_id=drug.match.formulation_id,
                role=drug.role,
                indication=drug.indication,
                mapping_method=drug.match.mapping_method,
                mapping_confidence=drug.match.confidence,
                mapping_version="v1",
            )
        )

    for reaction in report.reactions:
        db.add(FaersReaction(report_id=db_report.id, meddra_term=reaction.meddra_term, outcome=reaction.outcome))

    if report.classification is not None:
        existing_classification = db.query(ReportClassification).filter_by(report_id=db_report.id).one_or_none()
        if existing_classification is None:
            db.add(
                ReportClassification(
                    report_id=db_report.id,
                    use_classification=report.classification.use_classification,
                    confidence=report.classification.confidence,
                    evidence=report.classification.evidence,
                    method=report.classification.method,
                    classifier_version=report.classification.classifier_version,
                )
            )

    return outcome


def deduplicate_versions(db) -> int:
    """Post-ingestion defensive pass (docs/faers_deduplication.md): for any case_id with more
    than one ingested version, keep only the max-version row as is_deduplicated_latest=True."""
    case_ids_with_multiple = (
        db.query(FaersReport.case_id)
        .group_by(FaersReport.case_id)
        .having(func.count(FaersReport.id) > 1)
        .all()
    )
    superseded_count = 0
    for (case_id,) in case_ids_with_multiple:
        versions = db.query(FaersReport).filter_by(case_id=case_id).all()
        latest = max(versions, key=lambda r: (r.version or -1))
        for report in versions:
            if report.id != latest.id:
                report.is_deduplicated_latest = False
                report.dedup_reason = "superseded_by_newer_version"
                superseded_count += 1
            else:
                report.is_deduplicated_latest = True
    db.commit()
    return superseded_count


def run() -> None:
    db = SessionLocal()
    run_record = EtlRun(
        source="faers",
        started_at=dt.datetime.now(dt.timezone.utc),
        status=EtlStatus.RUNNING,
        version=_code_version(),
    )
    db.add(run_record)
    db.commit()

    seen_case_ids: set[str] = set()
    outcome_counts: Counter[str] = Counter()
    mapping_method_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    true_totals: dict[str, int] = {}
    records_read = 0
    since_commit = 0

    try:
        index = build_global_index(db)
        search_terms = build_search_terms(db)
        compounds_by_id = {c.id: c.canonical_name for c in db.query(Compound).all()}

        with OpenFdaClient() as client:
            for compound_id, terms in search_terms.items():
                compound_name = compounds_by_id[compound_id]
                query = build_openfda_query(terms)
                total = client.count(query)
                true_totals[compound_name] = total
                cap = min(total, MAX_REPORTS_PER_COMPOUND)
                print(f"{compound_name}: {total} total FAERS reports, fetching up to {cap}")

                for record in client.iterate_all(query, max_records=MAX_REPORTS_PER_COMPOUND):
                    records_read += 1
                    case_id = record.get("safetyreportid")
                    if case_id in seen_case_ids:
                        continue
                    seen_case_ids.add(case_id)

                    report = parse_report(record, index)
                    for drug in report.drugs:
                        mapping_method_counts[drug.match.mapping_method.value] += 1
                    if report.classification is not None:
                        classification_counts[report.classification.use_classification.value] += 1

                    outcome = persist_report(db, report)
                    outcome_counts[outcome] += 1
                    since_commit += 1
                    if since_commit >= COMMIT_EVERY:
                        db.commit()
                        since_commit = 0

        db.commit()
        superseded = deduplicate_versions(db)
        run_record.status = EtlStatus.SUCCESS
    except Exception as exc:  # noqa: BLE001
        run_record.status = EtlStatus.FAILED
        run_record.notes = str(exc)
        db.commit()
        raise
    finally:
        run_record.completed_at = dt.datetime.now(dt.timezone.utc)
        run_record.records_read = records_read
        run_record.records_inserted = outcome_counts.get("inserted", 0)
        run_record.records_rejected = outcome_counts.get("skipped_no_cohort_match", 0)
        run_record.notes = (
            f"True per-compound totals (uncapped): {true_totals}. "
            f"Outcomes: {dict(outcome_counts)}. "
            f"Mapping methods: {dict(mapping_method_counts)}. "
            f"Classifications: {dict(classification_counts)}."
        )
        db.commit()
        db.close()

    print(f"\nFAERS ingest complete: {records_read} raw records read, {dict(outcome_counts)}")
    print(f"Mapping method distribution: {dict(mapping_method_counts)}")
    print(f"Classification distribution: {dict(classification_counts)}")
    print(f"True (uncapped) totals per compound: {true_totals}")


if __name__ == "__main__":
    run()
