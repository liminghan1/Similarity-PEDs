"""Minimal openFDA `/drug/event` REST client.

Docs: https://open.fda.gov/apis/drug/event/, https://open.fda.gov/apis/authentication/

Rate limits (confirmed live, 2026-08-28, via open.fda.gov/apis/authentication/):
    without an API key: 240 requests/minute, 1,000 requests/day, per IP.
    with a key (OPENFDA_API_KEY in .env): 240 requests/minute, 120,000 requests/day.
This client throttles to ~2 req/s by default, comfortably under 240/min, and passes an API key
if one is configured (backend.app.core.config) without requiring one.

Pagination: classic `skip`/`limit`. Empirically confirmed live: `skip` beyond 25,000 is rejected
("Skip value must 25000 or less") -- an Elasticsearch-backed constraint, not something we can
paginate around with a bigger page size. `limit` up to 999 works without a key; `limit=1000`
exactly returned an API_KEY_MISSING error even though smaller limits (1, 100, 500, 999) did not --
an undocumented quirk confirmed empirically, not assumed. We use limit=500 as a safe default.
"""

from __future__ import annotations

import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.app.core.config import get_settings

BASE_URL = "https://api.fda.gov/drug/event.json"
MIN_REQUEST_INTERVAL_SECONDS = 0.5
MAX_SKIP = 25_000
SAFE_PAGE_LIMIT = 500


class OpenFdaLookupError(Exception):
    """Raised when an openFDA API request fails after retries or returns an unexpected shape."""


class OpenFdaClient:
    def __init__(self, *, min_request_interval: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        self._min_request_interval = min_request_interval
        self._last_request_at: float | None = None
        self._client = httpx.Client(timeout=60.0)
        self._api_key = get_settings().openfda_api_key or None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenFdaClient":
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
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )
    def _get(self, params: dict) -> dict:
        self._throttle()
        if self._api_key:
            params = {**params, "api_key": self._api_key}
        response = self._client.get(BASE_URL, params=params)
        if response.status_code == 404:
            # openFDA returns 404 (with a JSON body {"error": {"code": "NOT_FOUND", ...}}) for a
            # search with zero results, rather than 200 + empty list -- treat as "no results".
            return {"meta": {"results": {"total": 0}}, "results": []}
        response.raise_for_status()
        return response.json()

    def count(self, search: str) -> int:
        """Cheap total-result-count query (limit=1), used to size a fetch before paginating."""
        data = self._get({"search": search, "limit": 1})
        return data.get("meta", {}).get("results", {}).get("total", 0)

    def search(self, search: str, *, skip: int, limit: int = SAFE_PAGE_LIMIT) -> list[dict]:
        if skip > MAX_SKIP:
            raise OpenFdaLookupError(f"skip={skip} exceeds openFDA's documented max of {MAX_SKIP}")
        data = self._get({"search": search, "skip": skip, "limit": limit})
        return data.get("results", [])

    def iterate_all(self, search: str, *, max_records: int | None = None, page_size: int = SAFE_PAGE_LIMIT):
        """Yields records for `search`, paginating via skip/limit, stopping at `max_records` (if
        given) or openFDA's skip=25000 ceiling, whichever comes first. Callers that need more than
        ~25,500 records for one search term must split it (e.g. by date range) -- not attempted
        here since no cohort compound currently needs it (see pipelines/faers/README.md)."""
        skip = 0
        fetched = 0
        while skip <= MAX_SKIP:
            remaining = None if max_records is None else max_records - fetched
            if remaining is not None and remaining <= 0:
                return
            limit = page_size if remaining is None else min(page_size, remaining)
            records = self.search(search, skip=skip, limit=limit)
            if not records:
                return
            for record in records:
                yield record
                fetched += 1
            skip += len(records)
