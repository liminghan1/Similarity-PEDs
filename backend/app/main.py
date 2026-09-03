from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import analysis, compounds, overview, phenotypes, similarity
from backend.app.core.config import get_settings
from backend.app.services.artifacts import ArtifactNotFoundError

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

# The dashboard (Next.js dev server) runs on a different origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(ArtifactNotFoundError)
def artifact_not_found_handler(request: Request, exc: ArtifactNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(compounds.router)
app.include_router(phenotypes.router)
app.include_router(similarity.router)
app.include_router(analysis.router)
app.include_router(overview.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app_env": settings.app_env}
