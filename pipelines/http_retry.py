"""Shared retry predicate for the pipelines/*/client.py HTTP clients (pubchem, chembl,
bindingdb, faers).

A transient connection failure (httpx.TransportError) or a 5xx/429 HTTP response should be
retried. Any other HTTP error (400, 401, 404, ...) is a real, non-retryable problem -- retrying
it would just waste time and mask the actual issue (see project brief: fix errors, don't hide
them). Found in production (2026-09-03): all four clients previously retried only
httpx.TransportError, so a single transient 500 from ChEMBL aborted the entire `make ingest`
pipeline in CI instead of being retried.
"""

from __future__ import annotations

import httpx

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable_http_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return False
