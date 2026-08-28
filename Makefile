.PHONY: help venv db-up db-down db-migrate db-revision api test lint ingest build-datasets analyze figures report clean

help:
	@echo "Structure-to-Safety -- common commands"
	@echo "  make venv            Create the uv-managed virtual environment and install dependencies"
	@echo "  make db-up           Start PostgreSQL (docker-compose)"
	@echo "  make db-down         Stop PostgreSQL"
	@echo "  make db-migrate      Apply Alembic migrations (upgrade head)"
	@echo "  make db-revision m='message'   Autogenerate a new Alembic revision"
	@echo "  make api             Run the FastAPI dev server"
	@echo "  make test            Run the pytest suite"
	@echo "  make lint            Run ruff"
	@echo "  make ingest          Run all data-source ingestion pipelines (pipelines/) [Phase 4-6, not yet implemented]"
	@echo "  make build-datasets  Build phenotype matrices from ingested data [Phase 8, not yet implemented]"
	@echo "  make analyze         Run the primary + secondary analyses [Phase 9-11, not yet implemented]"
	@echo "  make figures         Generate publication figures [Phase 12, not yet implemented]"
	@echo "  make report          Build reports/research_report.md and reports/data_quality.md [Phase 13, not yet implemented]"

venv:
	uv sync --extra dev

db-up:
	docker compose up -d db
	@echo "Waiting for Postgres to be healthy..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' structure_to_safety_db 2>/dev/null)" = "healthy" ]; do sleep 1; done
	@echo "Postgres is up."

db-down:
	docker compose down

db-migrate:
	uv run alembic upgrade head

db-revision:
	uv run alembic revision --autogenerate -m "$(m)"

api:
	uv run uvicorn backend.app.main:app --reload

test:
	uv run pytest -v

lint:
	uv run ruff check backend

ingest:
	@echo "== PubChem (Phase 4) =="
	uv run python -m pipelines.pubchem.ingest
	@echo "== Compound registry: formulations + aliases (Phase 3) =="
	uv run python -m pipelines.normalization.seed_registry
	@echo "== ChEMBL receptor bioactivity (Phase 5) =="
	uv run python -m pipelines.chembl.ingest
	@echo "== BindingDB receptor bioactivity, optional complementary source (Phase 5) =="
	uv run python -m pipelines.bindingdb.ingest
	@echo "NOTE: FAERS ingestion (Phase 6) is not yet implemented -- see TODO.md."

build-datasets:
	@echo "Not yet implemented -- see TODO.md Phase 8 (analysis/phenotype_matrix.py)."
	@exit 1

analyze:
	@echo "Not yet implemented -- see TODO.md Phase 9-11 (analysis/similarity_analysis.py, matrix_association.py, clustering.py, misuse_analysis.py, sensitivity.py)."
	@exit 1

figures:
	@echo "== Figure 2: data-coverage heatmap (Phase 5) =="
	uv run python -m analysis.missingness_analysis
	@echo "NOTE: Figures 1, 3-10 are not yet implemented -- see TODO.md Phase 12."

report:
	@echo "Not yet implemented -- see TODO.md Phase 13."
	@exit 1

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
