from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AliasType(str, enum.Enum):
    BRAND = "brand"
    COMMON_NAME = "common_name"
    CHEMICAL_NAME = "chemical_name"
    MISSPELLING = "misspelling"
    ABBREVIATION = "abbreviation"
    OTHER = "other"


class Compound(Base):
    """Canonical chemistry/identity registry entry.

    A row with parent_compound_id IS NULL is a root parent compound (e.g. nandrolone).
    Ester/salt/formulation variants are NOT separate Compound rows — they live in
    `Formulation`, preserving the parent/derivative distinction (docs/database_schema.md).
    """

    __tablename__ = "compounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    parent_compound_id: Mapped[int | None] = mapped_column(ForeignKey("compounds.id"), nullable=True)

    pubchem_cid: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    chembl_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    isomeric_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchikey: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    molecular_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    molecular_weight: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    drug_class: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped[Compound | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[Compound]] = relationship(back_populates="parent")
    aliases: Mapped[list[CompoundAlias]] = relationship(back_populates="compound")
    formulations: Mapped[list[Formulation]] = relationship(back_populates="compound")

    def __repr__(self) -> str:
        return f"<Compound {self.canonical_name!r}>"


class CompoundAlias(Base):
    __tablename__ = "compound_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_type: Mapped[AliasType] = mapped_column(nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    compound: Mapped[Compound] = relationship(back_populates="aliases")


class Formulation(Base):
    __tablename__ = "formulations"
    __table_args__ = (UniqueConstraint("compound_id", "formulation_name", name="uq_formulation_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), nullable=False, index=True)
    formulation_name: Mapped[str] = mapped_column(Text, nullable=False)
    ester_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    route: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    compound: Mapped[Compound] = relationship(back_populates="formulations")
