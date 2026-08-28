"""Import every ORM model module so backend.app.db.base.Base.metadata is fully populated
before Alembic autogenerate or Base.metadata.create_all() run.
"""

from backend.app.models.compounds import Compound, CompoundAlias, Formulation
from backend.app.models.etl import EtlRun
from backend.app.models.faers import FaersDrug, FaersReaction, FaersReport, ReportClassification
from backend.app.models.pharmacology import Assay, Bioactivity, Target

__all__ = [
    "Compound",
    "CompoundAlias",
    "Formulation",
    "Target",
    "Assay",
    "Bioactivity",
    "FaersReport",
    "FaersDrug",
    "FaersReaction",
    "ReportClassification",
    "EtlRun",
]
