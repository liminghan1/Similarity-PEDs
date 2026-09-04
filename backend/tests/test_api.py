"""API endpoint tests against the live local database and artifacts (docker-compose Postgres,
migrated and ingested; artifacts/matrices/ populated by `make build-datasets analyze`). These are
integration tests, not isolated unit tests -- consistent with this project's general preference
for testing against real data (see e.g. backend/tests/test_faers_parsing.py's real fixtures)
rather than mocks, now extended to the API layer that serves that real data.

Run `make db-up && make db-migrate && make ingest && make build-datasets && make analyze` before
these will pass.
"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


class TestHealth:
    def test_health_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestCompoundsEndpoint:
    def test_list_compounds_returns_all_ten(self):
        response = client.get("/api/compounds")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        names = {c["canonical_name"] for c in data}
        assert "testosterone" in names
        assert "trenbolone" in names

    def test_list_compounds_has_expected_fields(self):
        response = client.get("/api/compounds")
        compound = response.json()[0]
        for field in ("canonical_name", "molecular_formula", "molecular_weight", "n_aliases", "n_faers_reports"):
            assert field in compound

    def test_get_compound_detail(self):
        response = client.get("/api/compounds/testosterone")
        assert response.status_code == 200
        data = response.json()
        assert data["canonical_name"] == "testosterone"
        assert data["molecular_formula"] == "C19H28O2"
        assert data["smiles"] is not None
        assert data["n_faers_reports"] > 0
        assert len(data["aliases"]) > 0

    def test_get_compound_detail_includes_bioactivities_for_testosterone(self):
        response = client.get("/api/compounds/testosterone")
        data = response.json()
        assert len(data["bioactivities"]) > 0
        assert all("target_name" in b for b in data["bioactivities"])

    def test_get_unknown_compound_404s(self):
        response = client.get("/api/compounds/not-a-real-compound")
        assert response.status_code == 404


class TestPhenotypesEndpoints:
    def test_molecular_phenotype_matrix(self):
        response = client.get("/api/phenotypes/molecular")
        assert response.status_code == 200
        data = response.json()
        assert len(data["labels"]) == 10
        assert "molecular_weight" in data["columns"]

    def test_safety_phenotype_matrix_has_null_for_sparse_cells(self):
        response = client.get("/api/phenotypes/safety")
        assert response.status_code == 200
        data = response.json()
        flat_values = [v for row in data["values"] for v in row]
        assert None in flat_values  # real sparse/below-threshold cells exist

    def test_safety_signal_table_long_format(self):
        response = client.get("/api/phenotypes/safety/signal-table")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 110  # 10 compounds x 11 categories
        row = data[0]
        for field in ("a", "b", "c", "d", "log_ror", "sparse_cell"):
            assert field in row


class TestSimilarityEndpoint:
    def test_structure_similarity_fully_defined(self):
        response = client.get("/api/similarity/structure")
        assert response.status_code == 200
        data = response.json()
        flat_values = [v for row in data["values"] for v in row]
        assert None not in flat_values  # structure distance is fully computable (Phase 9)

    def test_combined_similarity_is_mostly_null(self):
        # Real finding, not a bug: combined structure+receptor distance is 0/45 pairs defined
        # with current data (Phase 9) -- the API must surface this honestly.
        response = client.get("/api/similarity/combined")
        assert response.status_code == 200
        data = response.json()
        off_diagonal = [
            data["values"][i][j] for i in range(len(data["labels"])) for j in range(len(data["labels"])) if i != j
        ]
        assert all(v is None for v in off_diagonal)

    def test_unknown_representation_404s(self):
        response = client.get("/api/similarity/not-a-real-representation")
        assert response.status_code == 404


class TestAnalysisEndpoints:
    def test_matrix_association_shows_primary_not_computable(self):
        response = client.get("/api/analysis/matrix-association")
        assert response.status_code == 200
        data = response.json()
        primary = next(r for r in data["results"] if r["label"] == "PRIMARY")
        assert primary["computable"] is False

    def test_matrix_association_shows_h2_result(self):
        response = client.get("/api/analysis/matrix-association")
        data = response.json()
        h2 = next(r for r in data["results"] if "structure-only" in r["description"])
        assert h2["computable"] is True
        assert h2["n_objects"] == 10

    def test_clustering_endpoint(self):
        response = client.get("/api/analysis/clustering")
        assert response.status_code == 200
        data = response.json()
        assert "cluster_agreement" in data

    def test_misuse_endpoint(self):
        response = client.get("/api/analysis/misuse")
        assert response.status_code == 200
        data = response.json()
        assert data["group_sizes"]["misuse"] > 0

    def test_misuse_ae_categories_endpoint(self):
        response = client.get("/api/analysis/misuse/ae-categories")
        assert response.status_code == 200
        assert len(response.json()) == 11

    def test_sensitivity_endpoint(self):
        response = client.get("/api/analysis/sensitivity")
        assert response.status_code == 200
        assert len(response.json()) == 10

    def test_dataset_manifest_endpoint(self):
        response = client.get("/api/analysis/dataset-manifest")
        assert response.status_code == 200
        assert response.json()["compounds"]


class TestOverviewEndpoint:
    def test_overview_has_research_question_and_aims(self):
        response = client.get("/api/overview")
        assert response.status_code == 200
        data = response.json()
        assert "similar real-world adverse-event reporting" in data["research_question"]
        assert len(data["aims"]) == 4
        assert len(data["hypotheses"]) == 5  # H1, H2a, H2b, H3, H4

    def test_overview_dataset_sizes_reflect_real_data(self):
        response = client.get("/api/overview")
        data = response.json()
        assert data["dataset_sizes"]["n_compounds"] == 10
        assert data["dataset_sizes"]["n_faers_reports"] > 1000

    def test_overview_does_not_recommend_dosing_or_cycles(self):
        response = client.get("/api/overview")
        data = response.json()
        notice = data["not_a_ped_tool_notice"].lower()
        assert "cycle" in notice and "dose" in notice
