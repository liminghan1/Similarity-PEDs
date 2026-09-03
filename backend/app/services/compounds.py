"""Compound-registry query service. Pure DB-reading logic, separated from the FastAPI route
handlers (backend/app/api/compounds.py) so it is independently testable and reusable."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import Bioactivity, Compound, CompoundAlias, FaersDrug, Formulation
from backend.app.schemas.compounds import AliasOut, BioactivityOut, CompoundDetail, CompoundSummary


def list_compound_summaries(db: Session) -> list[CompoundSummary]:
    compounds = db.query(Compound).order_by(Compound.canonical_name).all()
    summaries = []
    for c in compounds:
        n_aliases = db.query(CompoundAlias).filter_by(compound_id=c.id).count()
        n_formulations = db.query(Formulation).filter_by(compound_id=c.id).count()
        n_bioactivities = db.query(Bioactivity).filter_by(compound_id=c.id).count()
        n_faers_reports = (
            db.query(func.count(func.distinct(FaersDrug.report_id)))
            .filter(FaersDrug.normalized_compound_id == c.id)
            .scalar()
            or 0
        )
        summaries.append(
            CompoundSummary(
                canonical_name=c.canonical_name,
                pubchem_cid=c.pubchem_cid,
                chembl_id=c.chembl_id,
                molecular_formula=c.molecular_formula,
                molecular_weight=float(c.molecular_weight) if c.molecular_weight is not None else None,
                drug_class=c.drug_class,
                n_aliases=n_aliases,
                n_formulations=n_formulations,
                n_bioactivities=n_bioactivities,
                n_faers_reports=n_faers_reports,
            )
        )
    return summaries


def get_compound_detail(db: Session, canonical_name: str) -> CompoundDetail | None:
    compound = db.query(Compound).filter_by(canonical_name=canonical_name).one_or_none()
    if compound is None:
        return None

    aliases = [
        AliasOut(
            alias=a.alias,
            alias_type=a.alias_type.value if hasattr(a.alias_type, "value") else a.alias_type,
            formulation_id=a.formulation_id,
            source=a.source,
            verified=a.verified,
        )
        for a in compound.aliases
    ]
    formulations = [
        {
            "id": f.id, "formulation_name": f.formulation_name, "ester_name": f.ester_name,
            "route": f.route, "source": f.source,
        }
        for f in compound.formulations
    ]
    bioactivities = [
        BioactivityOut(
            target_name=b.target.name,
            target_gene_symbol=b.target.gene_symbol,
            measurement_type=b.measurement_type.value if hasattr(b.measurement_type, "value") else b.measurement_type,
            relation=b.relation,
            standardized_value_nm=float(b.standardized_value_nm) if b.standardized_value_nm is not None else None,
            p_activity=float(b.p_activity) if b.p_activity is not None else None,
            source=b.source,
            assay_confidence_score=b.assay.confidence_score if b.assay else None,
        )
        for b in db.query(Bioactivity).filter_by(compound_id=compound.id).all()
    ]
    n_faers_reports = (
        db.query(func.count(func.distinct(FaersDrug.report_id)))
        .filter(FaersDrug.normalized_compound_id == compound.id)
        .scalar()
        or 0
    )

    return CompoundDetail(
        canonical_name=compound.canonical_name,
        pubchem_cid=compound.pubchem_cid,
        chembl_id=compound.chembl_id,
        smiles=compound.smiles,
        isomeric_smiles=compound.isomeric_smiles,
        inchikey=compound.inchikey,
        molecular_formula=compound.molecular_formula,
        molecular_weight=float(compound.molecular_weight) if compound.molecular_weight is not None else None,
        drug_class=compound.drug_class,
        source=compound.source,
        retrieved_at=compound.retrieved_at,
        aliases=aliases,
        formulations=formulations,
        bioactivities=bioactivities,
        n_faers_reports=n_faers_reports,
    )
