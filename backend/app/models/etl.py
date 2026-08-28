from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class EtlStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class EtlRun(Base):
    """Audit record for one pipeline execution (Sec. 28 provenance requirements)."""

    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_read: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_inserted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_rejected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[EtlStatus] = mapped_column(nullable=False, default=EtlStatus.RUNNING)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
