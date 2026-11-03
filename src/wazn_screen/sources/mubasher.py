"""Mubasher.info — Egypt stock prices and listed companies."""

from __future__ import annotations

from typing import Any

from .http import HttpClient

PRICES_URL = "https://www.mubasher.info/api/1/stocks/prices/all?country=eg"
COMPANIES_URL = "https://www.mubasher.info/api/1/listed-companies?country=eg&size=400"


class Mubasher:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient()

    def prices(self) -> list[dict[str, Any]]:
        data = self._http.get_json(
            PRICES_URL,
            validate=lambda d: isinstance(d, dict) and isinstance(d.get("prices"), list),
        )
        prices = data["prices"]
        return [p for p in prices if isinstance(p, dict)]

    def companies(self) -> list[dict[str, Any]]:
        data = self._http.get_json(
            COMPANIES_URL,
            validate=lambda d: isinstance(d, dict) and isinstance(d.get("rows"), list),
        )
        rows = data["rows"]
        return [r for r in rows if isinstance(r, dict)]
