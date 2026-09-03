"""Unit tests for the PubChem client (pipelines/pubchem/client.py) and the structure-validation
logic used by the ingestion script (pipelines/pubchem/ingest.py).

These tests mock the HTTP layer with fixture JSON captured from real PubChem PUG REST responses
(see pipelines/pubchem/README.md) rather than hitting the live network in the test suite --
network I/O in tests would be flaky/slow and is unnecessary once we know the response shape.
"""

from __future__ import annotations

import httpx
import pytest

from backend.app.analytics.chemistry import InvalidStructureError
from pipelines.pubchem.client import PubChemClient, PubChemLookupError

# Captured verbatim from a live GET to
# /compound/name/testosterone/property/MolecularFormula,MolecularWeight,SMILES,ConnectivitySMILES,InChIKey/JSON
# on 2026-08-27.
TESTOSTERONE_PROPERTY_RESPONSE = {
    "PropertyTable": {
        "Properties": [
            {
                "CID": 6013,
                "MolecularFormula": "C19H28O2",
                "MolecularWeight": "288.4",
                "SMILES": "C[C@]12CC[C@H]3[C@H]([C@@H]1CC[C@@H]2O)CCC4=CC(=O)CC[C@]34C",
                "ConnectivitySMILES": "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C",
                "InChIKey": "MUMGGOZAMZWBJJ-DYKIIFRCSA-N",
            }
        ]
    }
}
TESTOSTERONE_CID_RESPONSE = {"IdentifierList": {"CID": [6013]}}


class _FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]


@pytest.fixture
def client():
    with PubChemClient(min_request_interval=0.0) as c:
        yield c


class TestGetCidByName:
    def test_single_cid_returned(self, client, monkeypatch):
        monkeypatch.setattr(client._client, "get", lambda url: _FakeResponse(TESTOSTERONE_CID_RESPONSE))
        assert client.get_cid_by_name("testosterone") == 6013

    def test_ambiguous_name_raises(self, client, monkeypatch):
        monkeypatch.setattr(
            client._client, "get", lambda url: _FakeResponse({"IdentifierList": {"CID": [1, 2, 3]}})
        )
        with pytest.raises(PubChemLookupError):
            client.get_cid_by_name("ambiguous-name")

    def test_not_found_raises(self, client, monkeypatch):
        monkeypatch.setattr(client._client, "get", lambda url: _FakeResponse({}, status_code=404))
        with pytest.raises(PubChemLookupError):
            client.get_cid_by_name("not-a-real-compound")


class TestGetProperties:
    def test_properties_parsed(self, client, monkeypatch):
        monkeypatch.setattr(client._client, "get", lambda url: _FakeResponse(TESTOSTERONE_PROPERTY_RESPONSE))
        props = client.get_properties(6013)
        assert props["MolecularFormula"] == "C19H28O2"
        assert props["InChIKey"] == "MUMGGOZAMZWBJJ-DYKIIFRCSA-N"

    def test_missing_required_field_raises(self, client, monkeypatch):
        incomplete = {"PropertyTable": {"Properties": [{"CID": 6013, "MolecularFormula": "C19H28O2"}]}}
        # get_properties itself doesn't validate required fields -- fetch_compound does.
        monkeypatch.setattr(client._client, "get", lambda url: _FakeResponse(TESTOSTERONE_CID_RESPONSE)
                             if "cids" in url else _FakeResponse(incomplete))
        with pytest.raises(PubChemLookupError):
            client.fetch_compound("testosterone")


class TestFetchCompound:
    def test_full_fetch_assembles_record(self, client, monkeypatch):
        def fake_get(url: str):
            if "cids" in url:
                return _FakeResponse(TESTOSTERONE_CID_RESPONSE)
            return _FakeResponse(TESTOSTERONE_PROPERTY_RESPONSE)

        monkeypatch.setattr(client._client, "get", fake_get)
        record = client.fetch_compound("testosterone")
        assert record.pubchem_cid == 6013
        assert record.canonical_smiles == "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C"
        assert record.molecular_weight == pytest.approx(288.4)


class TestRetryBehavior:
    """Regression coverage: the @retry decorator on _get previously only retried
    httpx.TransportError, so a transient 5xx from the live API aborted ingestion instead of
    being retried (found in CI against ChEMBL; pipelines/http_retry.py fixes all four clients).
    """

    def test_transient_500_is_retried_then_succeeds(self, client, monkeypatch):
        calls = {"n": 0}

        def flaky_get(url: str):
            calls["n"] += 1
            if calls["n"] == 1:
                return _FakeResponse({}, status_code=500)
            return _FakeResponse(TESTOSTERONE_CID_RESPONSE)

        monkeypatch.setattr(client._client, "get", flaky_get)
        assert client.get_cid_by_name("testosterone") == 6013
        assert calls["n"] == 2

    def test_404_is_not_retried(self, client, monkeypatch):
        calls = {"n": 0}

        def always_404(url: str):
            calls["n"] += 1
            return _FakeResponse({}, status_code=404)

        monkeypatch.setattr(client._client, "get", always_404)
        with pytest.raises(PubChemLookupError):
            client.get_cid_by_name("not-a-real-compound")
        assert calls["n"] == 1


class TestValidateStructure:
    def test_valid_testosterone_structure_passes(self):
        from pipelines.pubchem.ingest import validate_structure

        validate_structure("CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C", "C19H28O2", 288.4)

    def test_formula_mismatch_rejected(self):
        from pipelines.pubchem.ingest import validate_structure

        with pytest.raises(InvalidStructureError):
            validate_structure("CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C", "C99H99O9", 288.4)

    def test_weight_mismatch_beyond_tolerance_rejected(self):
        from pipelines.pubchem.ingest import validate_structure

        with pytest.raises(InvalidStructureError):
            validate_structure("CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C", "C19H28O2", 500.0)

    def test_invalid_smiles_rejected(self):
        from pipelines.pubchem.ingest import validate_structure

        with pytest.raises(InvalidStructureError):
            validate_structure("not-a-smiles(", "C19H28O2", 288.4)
