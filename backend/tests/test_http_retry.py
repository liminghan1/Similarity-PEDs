"""Tests for pipelines/http_retry.py.

Regression coverage for a real production failure (2026-09-03, GitHub Actions CI): all four
pipeline clients (pubchem, chembl, bindingdb, faers) retried only httpx.TransportError, so a
transient 500 from ChEMBL's API aborted the entire `make ingest` step instead of being retried --
confirmed the query itself was fine by replaying the exact failing URL moments later (200 OK).
"""

from __future__ import annotations

import httpx
import pytest

from pipelines.http_retry import is_retryable_http_error


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError("error", request=None, response=_FakeResponse(status_code))  # type: ignore[arg-type]


class TestTransportErrors:
    def test_connect_error_is_retryable(self):
        assert is_retryable_http_error(httpx.ConnectError("connection refused")) is True

    def test_read_timeout_is_retryable(self):
        assert is_retryable_http_error(httpx.ReadTimeout("timed out")) is True


class TestServerAndRateLimitStatusCodes:
    @pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
    def test_retryable_status_codes(self, status_code):
        assert is_retryable_http_error(_http_status_error(status_code)) is True


class TestNonRetryableStatusCodes:
    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
    def test_client_error_status_codes_are_not_retried(self, status_code):
        assert is_retryable_http_error(_http_status_error(status_code)) is False


class TestUnrelatedExceptions:
    def test_non_http_exception_is_not_retryable(self):
        assert is_retryable_http_error(ValueError("not an HTTP error at all")) is False
