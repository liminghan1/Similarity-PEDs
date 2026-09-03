"""Minimal BindingDB RESTful API client.

Docs: https://www.bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp

Endpoint used: getLigandsByUniprot -- "return all binding data for a protein, within some
affinity cutoff." A cutoff of 1,000,000 nM (1 mM) is used by default to be maximally inclusive
(effectively "no cutoff" for any physiologically plausible receptor affinity) rather than risk
silently excluding a weak-but-real measurement, since our compound-matching step (not the
affinity value) determines what gets kept.

Response format note (confirmed against the live API, not assumed from docs): despite the
endpoint name, the JSON root key is `getLindsByUniprotResponse` (sic -- a typo in BindingDB's own
API, not ours) containing `bdb.affinities`, a list of {bdb.monomerid, bdb.smile, bdb.affinity_type,
bdb.affinity} records. `bdb.affinity` is a free-text numeric string, sometimes prefixed with
">"/"<" for a censored value (e.g. ">10000"), always in nM per the API documentation's "affinity
cutoff in nM" framing.
"""

from __future__ import annotations

import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pipelines.http_retry import is_retryable_http_error

BASE_URL = "https://bindingdb.org/rest"
MIN_REQUEST_INTERVAL_SECONDS = 0.5
DEFAULT_CUTOFF_NM = 1_000_000


class BindingDbLookupError(Exception):
    """Raised when a BindingDB API request fails after retries or returns an unexpected shape."""


class BindingDbClient:
    def __init__(self, *, min_request_interval: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        self._min_request_interval = min_request_interval
        self._last_request_at: float | None = None
        self._client = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BindingDbClient":
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
    def get_ligands_by_uniprot(self, uniprot_id: str, *, cutoff_nm: int = DEFAULT_CUTOFF_NM) -> list[dict]:
        self._throttle()
        response = self._client.get(
            f"{BASE_URL}/getLigandsByUniprot",
            params={"uniprot": f"{uniprot_id};{cutoff_nm}", "response": "application/json"},
        )
        response.raise_for_status()
        if not response.text.strip():
            return []  # documented behavior: empty string when the UniProt ID has no data
        data = response.json()
        payload = data.get("getLindsByUniprotResponse")
        if payload is None:
            raise BindingDbLookupError(f"Unexpected response shape for UniProt {uniprot_id!r}: {data!r}")
        return payload.get("bdb.affinities", [])
