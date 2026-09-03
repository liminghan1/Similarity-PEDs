from fastapi import APIRouter

from backend.app.services.artifacts import load_json_artifact, load_long_table_csv

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/matrix-association")
def matrix_association() -> dict:
    """H1 (PRIMARY, not computable with current data) and H2 (SECONDARY) matrix-association
    results (Phase 9)."""
    return load_json_artifact("matrix_association_results")


@router.get("/clustering")
def clustering() -> dict:
    """Independent structure/safety clustering + ARI/NMI agreement (Phase 10, SECONDARY)."""
    return load_json_artifact("clustering_results")


@router.get("/misuse")
def misuse_analysis() -> dict:
    """Therapeutic-vs-misuse comparison (Phase 10, SECONDARY, H3)."""
    return load_json_artifact("misuse_analysis_results")


@router.get("/misuse/ae-categories")
def misuse_ae_categories() -> list[dict]:
    return load_long_table_csv("misuse_vs_therapeutic_ae_categories")


@router.get("/multivariate")
def multivariate_association() -> dict:
    """Ridge-regression molecular-descriptor association per AE category (Phase 10, EXPLORATORY, H4)."""
    return load_json_artifact("multivariate_association_results")


@router.get("/sensitivity")
def sensitivity_analyses() -> dict:
    """All 8 pre-specified sensitivity variants re-running the H2 test (Phase 11)."""
    return load_json_artifact("sensitivity_results")


@router.get("/dataset-manifest")
def dataset_manifest() -> dict:
    return load_json_artifact("dataset_manifest")
