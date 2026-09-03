"""Minimal ChEMBL web-services REST client for the molecule/target/activity/assay data this
project needs.

Docs: https://www.ebi.ac.uk/chembl/api/data/docs

Rate limiting: ChEMBL does not publish a strict per-IP rate limit, but this client still
throttles conservatively (default ~3 req/s) and retries transient transport errors, consistent
with the PubChem client (pipelines/pubchem/client.py) and out of courtesy to a shared public
service. No API key is required.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pipelines.http_retry import is_retryable_http_error

ROOT_URL = "https://www.ebi.ac.uk"
BASE_URL = f"{ROOT_URL}/chembl/api/data"
MIN_REQUEST_INTERVAL_SECONDS = 0.34
QUALIFYING_MEASUREMENT_TYPES = "Ki,IC50,EC50,Kd"


class ChemblLookupError(Exception):
    """Raised when a ChEMBL API request fails after retries, or returns an unexpected shape.
    Never silently returns a partial/guessed result."""


class ChemblClient:
    def __init__(self, *, min_request_interval: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        self._min_request_interval = min_request_interval
        self._last_request_at: float | None = None
        self._client = httpx.Client(timeout=30.0)
        self._assay_cache: dict[str, dict] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ChemblClient":
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
    def _get_absolute(self, url: str, params: dict | None = None) -> dict:
        self._throttle()
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._get_absolute(f"{BASE_URL}{path}", params=params)

    def get_molecule_chembl_id_by_inchikey(self, inchikey: str) -> str | None:
        """Exact InChIKey match only -- no name-based fallback, to avoid a false-positive match
        on a different stereoisomer or salt form. Returns None (not raises) when no ChEMBL entry
        exists for this exact structure; the caller decides how to log that."""
        data = self._get(
            "/molecule.json", params={"molecule_structures__standard_inchi_key": inchikey}
        )
        molecules = data.get("molecules", [])
        if len(molecules) == 0:
            return None
        if len(molecules) > 1:
            raise ChemblLookupError(
                f"InChIKey {inchikey!r} matched {len(molecules)} ChEMBL molecules (expected 0 or 1)."
            )
        return molecules[0]["molecule_chembl_id"]

    def iterate_activities(self, molecule_chembl_id: str, target_chembl_id: str) -> Iterator[dict]:
        """Yields raw activity records for Ki/IC50/EC50/Kd measurements of one molecule against
        one target, following pagination. Does NOT apply potential_duplicate / data_validity
        filtering -- that's an ingestion-layer decision (pipelines/chembl/ingest.py), kept
        separate so this client stays a faithful, unopinionated wrapper over the raw API."""
        params = {
            "molecule_chembl_id": molecule_chembl_id,
            "target_chembl_id": target_chembl_id,
            "standard_type__in": QUALIFYING_MEASUREMENT_TYPES,
            "limit": 100,
            "offset": 0,
        }
        data = self._get("/activity.json", params=params)
        while True:
            yield from data.get("activities", [])
            next_url = data.get("page_meta", {}).get("next")
            if not next_url:
                return
            # `next_url` is a full, already-encoded relative URL (e.g.
            # "/chembl/api/data/activity.json?limit=100&offset=100&..."); fetch it directly
            # rather than re-splitting and re-encoding its query string ourselves, which would
            # risk mangling percent-encoded characters (e.g. the comma in standard_type__in).
            data = self._get_absolute(f"{ROOT_URL}{next_url}")

    def get_assay(self, assay_chembl_id: str) -> dict:
        """Cached: an assay is typically shared across many activity records within and across
        compounds, so we fetch its metadata (notably confidence_score) at most once per run."""
        if assay_chembl_id not in self._assay_cache:
            data = self._get("/assay.json", params={"assay_chembl_id": assay_chembl_id})
            assays = data.get("assays", [])
            if len(assays) != 1:
                raise ChemblLookupError(
                    f"Assay {assay_chembl_id!r} returned {len(assays)} records (expected 1)."
                )
            self._assay_cache[assay_chembl_id] = assays[0]
        return self._assay_cache[assay_chembl_id]
