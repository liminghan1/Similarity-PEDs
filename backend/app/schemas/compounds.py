"""Pydantic response schemas for the compound-registry API endpoints.

Field naming and presence deliberately mirror docs/database_schema.md -- this layer serves
already-computed/ingested data (Sec. 37: OBSERVED DATA), it never derives a new statistic.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class AliasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alias: str
    alias_type: str
    formulation_id: int | None
    source: str | None
    verified: bool


class FormulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    formulation_name: str
    ester_name: str | None
    route: str | None
    source: str | None


class BioactivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_name: str
    target_gene_symbol: str | None
    measurement_type: str
    relation: str
    standardized_value_nm: float | None
    p_activity: float | None
    source: str
    assay_confidence_score: int | None


class CompoundSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    canonical_name: str
    pubchem_cid: int | None
    chembl_id: str | None
    molecular_formula: str | None
    molecular_weight: float | None
    drug_class: str | None
    n_aliases: int
    n_formulations: int
    n_bioactivities: int
    n_faers_reports: int


class CompoundDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    canonical_name: str
    pubchem_cid: int | None
    chembl_id: str | None
    smiles: str | None
    isomeric_smiles: str | None
    inchikey: str | None
    molecular_formula: str | None
    molecular_weight: float | None
    drug_class: str | None
    source: str | None
    retrieved_at: dt.datetime | None
    aliases: list[AliasOut]
    formulations: list[FormulationOut]
    bioactivities: list[BioactivityOut]
    n_faers_reports: int
