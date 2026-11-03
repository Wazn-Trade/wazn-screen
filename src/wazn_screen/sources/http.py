"""Shared HTTP client for the data sources.

Why not plain ``httpx.get``:

- Several origins (EGX BFF in particular) are protected by a WAF that rejects
  non-browser User-Agents; one spot to spoof the UA across every call.
- EGX BFF middleware also requires a specific ``x-egx-origin`` header; add it
  unconditionally — benign for other hosts.
- Transient 5xx and connect errors are retried with exponential backoff.
- Transport is injectable so tests can plug ``httpx.MockTransport`` instead of
  touching the network. Tests MUST never rely on the real internet.

Browser CORS is not our problem — Python requests from a user's machine or a
server don't need the race-based proxy chain documented in the JS terminal.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)
# EGX middleware wants this header. Harmless elsewhere.
DEFAULT_HEADERS: dict[str, str] = {
    "user-agent": DEFAULT_UA,
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,ar;q=0.8",
    "x-egx-origin": "https://beta.egx.com.eg",
    "referer": "https://beta.egx.com.eg/",
}


class HttpError(RuntimeError):
    """Raised when a source call cannot be served (status, timeout, or validation)."""

    def __init__(self, message: str, *, url: str, status: int | None = None) -> None:
        super().__init__(message)
        self.url = url
        self.status = status


class HttpClient:
    """Small wrapper around ``httpx.Client`` with retries + validation hook."""

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        max_retries: int = 2,
        backoff: float = 0.5,
        headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        merged = dict(DEFAULT_HEADERS)
        if headers:
            merged.update(headers)
        self._client = httpx.Client(
            headers=merged,
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )
        self._max_retries = max_retries
        self._backoff = backoff

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_json(
        self,
        url: str,
        *,
        validate: Callable[[Any], bool] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """GET + parse JSON + validate. Retries 5xx and connect errors."""
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                r = self._client.get(url, params=params)
            except httpx.HTTPError as e:
                last_exc = e
                self._sleep(attempt)
                continue
            if r.status_code >= 500:
                last_exc = HttpError(
                    f"{r.status_code} from {url}", url=url, status=r.status_code
                )
                self._sleep(attempt)
                continue
            if r.status_code >= 400:
                raise HttpError(
                    f"{r.status_code} from {url}: {r.text[:200]}",
                    url=url,
                    status=r.status_code,
                )
            try:
                data = r.json()
            except ValueError as e:
                raise HttpError(f"non-JSON response from {url}", url=url) from e
            if validate is not None and not validate(data):
                raise HttpError(f"validation failed for {url}", url=url)
            return data
        assert last_exc is not None
        raise HttpError(f"GET {url} failed after retries: {last_exc}", url=url) from last_exc

    def _sleep(self, attempt: int) -> None:
        if attempt < self._max_retries:
            time.sleep(self._backoff * (2**attempt))
