"""Minimal PubChem PUG REST client for the compound identifiers/structure this project needs.

Docs: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest

Rate limiting: PubChem's usage policy caps requests at 5/second and 400/minute per IP; this
client throttles well under that (default ~3 req/s) since our cohort is small (~10 compounds)
and there is no benefit to going faster. No API key is required for this volume.

Property names: as of 2024, PubChem deprecated `CanonicalSMILES`/`IsomericSMILES` in favor of
`ConnectivitySMILES` (2D, no stereochemistry) and `SMILES` (includes stereochemistry when known).
This was confirmed against the live API on 2026-08-27 (see pipelines/pubchem/README.md) rather
than assumed from documentation that may be stale.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pipelines.http_retry import is_retryable_http_error

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
MIN_REQUEST_INTERVAL_SECONDS = 0.34  # ~3 req/s, under PubChem's 5 req/s cap
PROPERTIES = "MolecularFormula,MolecularWeight,SMILES,ConnectivitySMILES,InChIKey"


class PubChemLookupError(Exception):
    """Raised when a compound name does not resolve to exactly one PubChem CID, or the API
    request fails after retries. Never silently returns a partial/guessed result."""


@dataclass(frozen=True)
class PubChemCompoundRecord:
    query_name: str
    pubchem_cid: int
    molecular_formula: str
    molecular_weight: float
    isomeric_smiles: str
    canonical_smiles: str
    inchikey: str


class PubChemClient:
    def __init__(self, *, min_request_interval: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        self._min_request_interval = min_request_interval
        self._last_request_at: float | None = None
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PubChemClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _throttle(self) -> None:
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            remaining = self._min_request_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()

    @retry(
        retry=retry_if_exception(is_retryable_http_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _get(self, path: str) -> dict:
        self._throttle()
        response = self._client.get(f"{BASE_URL}{path}")
        if response.status_code == 404:
            raise PubChemLookupError(f"PubChem returned 404 for {path!r}")
        response.raise_for_status()
        return response.json()

    def get_cid_by_name(self, name: str) -> int:
        data = self._get(f"/compound/name/{name}/cids/JSON")
        cids = data.get("IdentifierList", {}).get("CID", [])
        if len(cids) != 1:
            raise PubChemLookupError(
                f"Name {name!r} resolved to {len(cids)} CIDs (expected exactly 1): {cids}. "
                "Ambiguous or unresolved names must be reviewed manually, not guessed."
            )
        return cids[0]

    def get_properties(self, cid: int) -> dict:
        data = self._get(f"/compound/cid/{cid}/property/{PROPERTIES}/JSON")
        props = data.get("PropertyTable", {}).get("Properties", [])
        if len(props) != 1:
            raise PubChemLookupError(f"CID {cid} returned {len(props)} property records (expected 1).")
        return props[0]

    def fetch_compound(self, query_name: str) -> PubChemCompoundRecord:
        cid = self.get_cid_by_name(query_name)
        props = self.get_properties(cid)
        required = ("MolecularFormula", "MolecularWeight", "SMILES", "ConnectivitySMILES", "InChIKey")
        missing = [k for k in required if k not in props]
        if missing:
            raise PubChemLookupError(f"CID {cid} property response missing fields: {missing}")
        return PubChemCompoundRecord(
            query_name=query_name,
            pubchem_cid=cid,
            molecular_formula=props["MolecularFormula"],
            molecular_weight=float(props["MolecularWeight"]),
            isomeric_smiles=props["SMILES"],
            canonical_smiles=props["ConnectivitySMILES"],
            inchikey=props["InChIKey"],
        )
