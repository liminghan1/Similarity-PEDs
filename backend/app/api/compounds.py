from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.compounds import CompoundDetail, CompoundSummary
from backend.app.services import compounds as compounds_service

router = APIRouter(prefix="/api/compounds", tags=["compounds"])


@router.get("", response_model=list[CompoundSummary])
def list_compounds(db: Session = Depends(get_db)) -> list[CompoundSummary]:
    return compounds_service.list_compound_summaries(db)


@router.get("/{canonical_name}", response_model=CompoundDetail)
def get_compound(canonical_name: str, db: Session = Depends(get_db)) -> CompoundDetail:
    detail = compounds_service.get_compound_detail(db, canonical_name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No compound named {canonical_name!r}")
    return detail
