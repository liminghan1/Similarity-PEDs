from __future__ import annotations

import datetime as dt
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.compounds import Compound


class MeasurementType(str, enum.Enum):
    KI = "Ki"
    IC50 = "IC50"
    EC50 = "EC50"
    KD = "Kd"


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    gene_symbol: Mapped[str | None] = mapped_column(Text, nullable=True)
    organism: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_target_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)

    assays: Mapped[list[Assay]] = relationship(back_populates="target")

    def __repr__(self) -> str:
        return f"<Target {self.gene_symbol or self.name!r}>"


class Assay(Base):
    __tablename__ = "assays"
    __table_args__ = (UniqueConstraint("source", "source_assay_id", name="uq_assay_source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_assay_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True)
    assay_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organism: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assay_format: Mapped[str | None] = mapped_column(Text, nullable=True)

    target: Mapped[Target | None] = relationship(back_populates="assays")
    bioactivities: Mapped[list[Bioactivity]] = relationship(back_populates="assay")


class Bioactivity(Base):
    """A single compound x assay x target bioactivity measurement.

    Ki/IC50/EC50/Kd are never pooled as equivalent (research/exclusion_rules.md Sec. 3).
    p_activity is populated only for relation == '=' (censored >/< values are retained but
    excluded from the point-estimate pActivity per the project's measurement-handling rules).
    """

    __tablename__ = "bioactivities"

    id: Mapped[int] = mapped_column(primary_key=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), nullable=False, index=True)
    assay_id: Mapped[int] = mapped_column(ForeignKey("assays.id"), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"), nullable=False, index=True)

    measurement_type: Mapped[MeasurementType] = mapped_column(nullable=False)
    relation: Mapped[str] = mapped_column(Text, nullable=False, default="=")
    raw_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    raw_units: Mapped[str | None] = mapped_column(Text, nullable=True)
    standardized_value_nm: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    p_activity: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_record_id: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    compound: Mapped["Compound"] = relationship()
    assay: Mapped[Assay] = relationship(back_populates="bioactivities")
    target: Mapped[Target] = relationship()
