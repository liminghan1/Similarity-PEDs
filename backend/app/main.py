from fastapi import FastAPI

from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Structure-to-Safety API",
    description=(
        "Research API for the Structure-to-Safety project: multimodal computational "
        "pharmacology of anabolic-androgenic steroids. Serves pre-computed research "
        "artifacts (molecular/receptor phenotypes, FAERS safety phenotypes, similarity "
        "and matrix-association results) for the companion dashboard. This API does not "
        "provide dosing, cycle, or product-safety recommendations."
    ),
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app_env": settings.app_env}
