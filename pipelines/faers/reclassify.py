"""Standalone re-classification of already-ingested FAERS reports.

Re-applies pipelines.faers.classification.classify_report to every already-persisted report,
using data already in the database (FaersDrug.normalized_compound_id/indication,
FaersReaction.meddra_term) -- no network calls to openFDA. Needed whenever the classifier's rules
change (CLASSIFIER_VERSION bump) after reports have already been ingested, since
pipelines.faers.ingest.persist_report deliberately never overwrites an existing
ReportClassification row (classification happens once, at ingest time, from the raw API
response). Reclassifies every report regardless of `is_deduplicated_latest` (cheap at this data
volume, and leaves no stale-classifier-version rows behind for a future audit to trip over), even
though only latest-version reports are used by analysis/misuse_analysis.py's H3 comparison.

Only drugs with a resolved compound_id (normalized_compound_id IS NOT NULL) are passed to the
classifier, mirroring pipelines.faers.parsing.parse_report's original filter -- a MANUAL_REVIEW
match (ambiguous, compound_id NULL, still persisted for auditability) was never classification
input at ingest time either.

Usage:
    uv run python -m pipelines.faers.reclassify
"""

from __future__ import annotations

from collections import defaultdict

from backend.app.db.session import SessionLocal
from backend.app.models import FaersDrug, FaersReaction, FaersReport, ReportClassification
from pipelines.faers.classification import CLASSIFIER_VERSION, MatchedDrug, classify_report


def run() -> None:
    db = SessionLocal()
    try:
        report_ids = [r.id for r in db.query(FaersReport.id).all()]

        drugs_by_report: dict[int, list[MatchedDrug]] = defaultdict(list)
        for report_id, compound_id, indication in db.query(
            FaersDrug.report_id, FaersDrug.normalized_compound_id, FaersDrug.indication
        ).filter(FaersDrug.normalized_compound_id.isnot(None)):
            drugs_by_report[report_id].append(MatchedDrug(compound_id=compound_id, drugindication=indication))

        reactions_by_report: dict[int, list[str]] = defaultdict(list)
        for report_id, term in db.query(FaersReaction.report_id, FaersReaction.meddra_term):
            reactions_by_report[report_id].append(term)

        existing = {rc.report_id: rc for rc in db.query(ReportClassification).all()}

        before_counts: dict[str, int] = defaultdict(int)
        after_counts: dict[str, int] = defaultdict(int)
        changed = 0

        for report_id in report_ids:
            result = classify_report(drugs_by_report.get(report_id, []), reactions_by_report.get(report_id, []))
            row = existing.get(report_id)

            if row is None:
                after_counts[result.use_classification.value] += 1
                db.add(
                    ReportClassification(
                        report_id=report_id,
                        use_classification=result.use_classification,
                        confidence=result.confidence,
                        evidence=result.evidence,
                        method=result.method,
                        classifier_version=result.classifier_version,
                    )
                )
                changed += 1
                continue

            before_counts[row.use_classification.value] += 1
            after_counts[result.use_classification.value] += 1
            if row.classifier_version != result.classifier_version or row.use_classification != result.use_classification:
                row.use_classification = result.use_classification
                row.confidence = result.confidence
                row.evidence = result.evidence
                row.method = result.method
                row.classifier_version = result.classifier_version
                changed += 1

        db.commit()
    finally:
        db.close()

    print(f"Reclassified {len(report_ids)} reports with classifier {CLASSIFIER_VERSION}: {changed} rows changed.")
    print(f"Before: {dict(before_counts)}")
    print(f"After:  {dict(after_counts)}")


if __name__ == "__main__":
    run()
