from __future__ import annotations

import datetime as dt
import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.compounds import Compound, Formulation


class MappingMethod(str, enum.Enum):
    EXACT_ALIAS = "exact_alias"
    CURATED_MATCH = "curated_match"
    NORMALIZED_STRING_MATCH = "normalized_string_match"
    FUZZY_HIGH_CONFIDENCE = "fuzzy_high_confidence"
    MANUAL_REVIEW = "manual_review"
    UNMAPPED = "unmapped"


class UseClassification(str, enum.Enum):
    THERAPEUTIC = "therapeutic"
    MISUSE = "misuse"
    MULTI_AAS_EXPOSURE = "multi_aas_exposure"
    # v2 classifier (pipelines/faers/classification.py): reports whose only positive evidence is
    # an "ambiguous" reaction term (e.g. "accidental overdose", "product use in unapproved
    # indication") that is consistent with misuse but has a legitimate non-misuse explanation too,
    # and so is not on its own sufficient to classify MISUSE. Tracked separately rather than
    # folded into UNKNOWN so this real, non-trivial evidence stays visible and auditable.
    AMBIGUOUS_EXPOSURE = "ambiguous_exposure"
    UNKNOWN = "unknown"


class FaersReport(Base):
    """One FAERS case-version. Deduplication never deletes rows (docs/faers_deduplication.md);
    superseded versions are retained with is_deduplicated_latest = False and a dedup_reason.
    """

    __tablename__ = "faers_reports"
    __table_args__ = (UniqueConstraint("case_id", "version", name="uq_faers_case_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_report_id: Mapped[str] = mapped_column(Text, nullable=False)
    received_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True, index=True)
    age: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    age_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    sex: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    serious: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seriousness_death: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seriousness_hospitalization: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    is_deduplicated_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dedup_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    drugs: Mapped[list["FaersDrug"]] = relationship(back_populates="report")
    reactions: Mapped[list["FaersReaction"]] = relationship(back_populates="report")
    classification: Mapped["ReportClassification | None"] = relationship(back_populates="report")


class FaersDrug(Base):
    __tablename__ = "faers_drugs"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("faers_reports.id"), nullable=False, index=True)
    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_compound_id: Mapped[int | None] = mapped_column(
        ForeignKey("compounds.id"), nullable=True, index=True
    )
    formulation_id: Mapped[int | None] = mapped_column(ForeignKey("formulations.id"), nullable=True)
    role: Mapped[str | None] = mapped_column(Text, nullable=True)
    indication: Mapped[str | None] = mapped_column(Text, nullable=True)

    mapping_method: Mapped[MappingMethod] = mapped_column(nullable=False)
    mapping_confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    mapping_version: Mapped[str] = mapped_column(Text, nullable=False)

    report: Mapped[FaersReport] = relationship(back_populates="drugs")
    compound: Mapped["Compound | None"] = relationship()
    formulation: Mapped["Formulation | None"] = relationship()


class FaersReaction(Base):
    __tablename__ = "faers_reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("faers_reports.id"), nullable=False, index=True)
    meddra_term: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped[FaersReport] = relationship(back_populates="reactions")


class ReportClassification(Base):
    """Conservative therapeutic-use-vs-misuse classification for one report (Aim 4).

    `evidence` stores the structured list of evidence items that drove the label, so every
    classification is auditable — never a silent inference from "multiple drugs present."
    """

    __tablename__ = "report_classifications"

    report_id: Mapped[int] = mapped_column(ForeignKey("faers_reports.id"), primary_key=True)
    use_classification: Mapped[UseClassification] = mapped_column(nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    evidence: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    classifier_version: Mapped[str] = mapped_column(Text, nullable=False)

    report: Mapped[FaersReport] = relationship(back_populates="classification")
