from fastapi import APIRouter, HTTPException

from backend.app.services.artifacts import load_matrix_csv

router = APIRouter(prefix="/api/similarity", tags=["similarity"])

VALID_REPRESENTATIONS = {
    # Maps the API's representation names to the actual filenames analysis/similarity_analysis.py
    # writes (each ends in "_matrix.csv", not just "_distance.csv" -- a mismatch here previously
    # made every one of these routes 404, caught by test_api.py, not by inspection).
    "structure": "structure_distance_matrix",
    "descriptor": "descriptor_distance_matrix",
    "fingerprint": "fingerprint_distance_matrix",
    "receptor": "receptor_distance_matrix",
    "combined": "combined_distance_matrix",
    "safety": "safety_distance_matrix",
}


@router.get("/{representation}")
def get_distance_matrix(representation: str) -> dict:
    """Pairwise distance matrix for one representation (Phase 9). `combined` and `receptor` are
    real, current-data results, not placeholders: with current ChEMBL/BindingDB coverage they are
    almost entirely null (see `research/analysis_plan.md` Deviations, 2026-08-28) -- the API
    returns that missingness as-is rather than hiding it."""
    if representation not in VALID_REPRESENTATIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown representation {representation!r}; valid values: {sorted(VALID_REPRESENTATIONS)}",
        )
    return load_matrix_csv(VALID_REPRESENTATIONS[representation])
