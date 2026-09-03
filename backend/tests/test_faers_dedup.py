"""Tests for pipelines.faers.ingest.deduplicate_versions (Phase 6, docs/faers_deduplication.md).

Runs against the real local Postgres database (project-wide preference for real data over
mocks), but every test is wrapped in an outer transaction that is rolled back on teardown --
`deduplicate_versions` calls `db.commit()` internally, so a plain rollback is not enough; the
fixture uses SQLAlchemy's documented "join a session into an external transaction" recipe
(a SAVEPOINT restarted after every commit) so no synthetic row is ever left in the real dataset.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event

from backend.app.db.session import SessionLocal, engine
from backend.app.models.faers import FaersReport
from pipelines.faers.ingest import deduplicate_versions


@pytest.fixture
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = SessionLocal(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


def _make_report(case_id: str, version: int | None, source_report_id: str) -> FaersReport:
    return FaersReport(case_id=case_id, version=version, source_report_id=source_report_id)


class TestDeduplicateVersions:
    def test_keeps_only_max_version_as_latest(self, db_session):
        db_session.add_all(
            [
                _make_report("case-dedup-test-1", 1, "src-1"),
                _make_report("case-dedup-test-1", 2, "src-2"),
                _make_report("case-dedup-test-1", 3, "src-3"),
            ]
        )
        db_session.commit()

        superseded = deduplicate_versions(db_session)

        rows = (
            db_session.query(FaersReport)
            .filter_by(case_id="case-dedup-test-1")
            .order_by(FaersReport.version)
            .all()
        )
        assert [r.is_deduplicated_latest for r in rows] == [False, False, True]
        assert rows[-1].dedup_reason is None
        for r in rows[:-1]:
            assert r.dedup_reason == "superseded_by_newer_version"
        assert superseded >= 2

    def test_single_version_case_is_untouched(self, db_session):
        db_session.add(_make_report("case-dedup-test-2", 1, "src-solo"))
        db_session.commit()

        deduplicate_versions(db_session)

        row = db_session.query(FaersReport).filter_by(case_id="case-dedup-test-2").one()
        assert row.is_deduplicated_latest is True
        assert row.dedup_reason is None

    def test_null_version_is_treated_as_lowest(self, db_session):
        db_session.add_all(
            [
                _make_report("case-dedup-test-3", None, "src-null"),
                _make_report("case-dedup-test-3", 1, "src-versioned"),
            ]
        )
        db_session.commit()

        deduplicate_versions(db_session)

        null_row = (
            db_session.query(FaersReport)
            .filter_by(case_id="case-dedup-test-3", source_report_id="src-null")
            .one()
        )
        versioned_row = (
            db_session.query(FaersReport)
            .filter_by(case_id="case-dedup-test-3", source_report_id="src-versioned")
            .one()
        )
        assert null_row.is_deduplicated_latest is False
        assert null_row.dedup_reason == "superseded_by_newer_version"
        assert versioned_row.is_deduplicated_latest is True

    def test_rows_are_never_deleted(self, db_session):
        db_session.add_all(
            [
                _make_report("case-dedup-test-4", 1, "src-a"),
                _make_report("case-dedup-test-4", 2, "src-b"),
            ]
        )
        db_session.commit()

        deduplicate_versions(db_session)

        count = (
            db_session.query(FaersReport).filter_by(case_id="case-dedup-test-4").count()
        )
        assert count == 2
