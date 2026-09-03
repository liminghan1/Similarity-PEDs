from fastapi import APIRouter

from backend.app.services.artifacts import load_long_table_csv, load_matrix_csv

router = APIRouter(prefix="/api/phenotypes", tags=["phenotypes"])


@router.get("/molecular")
def molecular_phenotype() -> dict:
    """Molecular descriptor matrix (Phase 8) -- OBSERVED/DERIVED chemistry, fully populated."""
    return load_matrix_csv("molecular_descriptor_matrix")


@router.get("/receptor")
def receptor_phenotype() -> dict:
    """Receptor pActivity matrix (Phase 8, primary/confidence>=8 variant). Missing cells are
    real missingness (7/10 compounds have zero receptor measurements), not zero activity."""
    return load_matrix_csv("receptor_phenotype_matrix_primary")


@router.get("/safety")
def safety_phenotype() -> dict:
    """Wide-format logROR matrix (Phase 8) -- DERIVED STATISTIC. Sparse/below-threshold cells
    are null, never a plausible-looking-but-unreliable number (research/exclusion_rules.md Sec. 4)."""
    return load_matrix_csv("safety_phenotype_matrix_logror")


@router.get("/safety/signal-table")
def safety_signal_table() -> list[dict]:
    """Long-format safety signal table: every compound x AE category with the full a/b/c/d
    contingency counts, ROR, logROR, CI, and sparse-cell flag -- always shown together per
    research/analysis_plan.md Sec. 1, never a bare logROR number."""
    return load_long_table_csv("safety_signal_table_long")
