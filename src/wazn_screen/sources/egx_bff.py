"""EGX BFF — official backend-for-frontend at ``beta.egx.com.eg/api/bff/egx``.

Endpoint map taken from the JS terminal's inventory (``endpoints.txt``). The
raw envelope has shape ``{"data": ...}``; methods return the ``data`` payload
directly after a cheap sanity check.
"""

from __future__ import annotations

from typing import Any

from .http import HttpClient

BASE_URL = "https://beta.egx.com.eg/api/bff/egx"

ENDPOINTS: dict[str, str] = {
    "marketStatus": "/market-status",
    "stockInfo": "/stock-info",
    "marketSummaries": "/market-summaries",
    "marketIndicators": "/market-indicators",
    "case30": "/index-data?interval=1&indexName=CASE30",
    "shariahSummary": "/indices-summary?indexName=EGX_SHARIAH",
    "shariahConstituents": "/index-constituents?indexName=EGX_SHARIAH",
    "topVolume": "/market-watch?Page=1&PageSize=10&SortBy=Volume&SortDescending=true",
    "topGainers": "/market-watch?Page=1&PageSize=10&SortBy=ChgPer&SortDescending=true",
    "topLosers": "/market-watch?Page=1&PageSize=10&SortBy=ChgPer&SortDescending=false",
    "gold": "/gold-market-watch",
    "silver": "/silver-market-watch",
    "listedSukuks": "/listed-sukuks?includeBlobs=false",
    "sovereignSukuk": "/sovereign-sukuk",
    "treasuryBonds": "/treasury-bonds",
    "listedBills": "/listed-bills",
    "derivatives": "/derivatives-watch",
    "investorStatistics": "/investor-statistics",
    "investorFullStatistics": "/investor-full-statistics",
    "stockCategories": "/stock-categories",
}


class EgxBff:
    """Typed access to every endpoint in ``ENDPOINTS``.

    ``http`` is a shared :class:`HttpClient`; passing one in is how tests
    inject ``httpx.MockTransport``.
    """

    def __init__(self, http: HttpClient | None = None, base_url: str = BASE_URL) -> None:
        self._http = http or HttpClient()
        self._base = base_url.rstrip("/")

    def _get(self, key: str) -> Any:
        path = ENDPOINTS[key]
        data = self._http.get_json(f"{self._base}{path}", validate=_has_data)
        return data.get("data")

    # Market
    def market_status(self) -> Any:
        return self._get("marketStatus")

    def stock_info(self) -> Any:
        return self._get("stockInfo")

    def market_summaries(self) -> Any:
        return self._get("marketSummaries")

    def market_indicators(self) -> Any:
        return self._get("marketIndicators")

    def case30(self) -> Any:
        return self._get("case30")

    # Shariah
    def shariah_summary(self) -> Any:
        return self._get("shariahSummary")

    def shariah_constituents(self) -> Any:
        """Returns the current EGX_SHARIAH membership list from the BFF."""
        return self._get("shariahConstituents")

    def shariah_symbols(self) -> list[str]:
        """Convenience: just the normalised list of tickers.

        Tolerant of a few known response shapes — the BFF has historically
        returned either ``[{"symbol": "..."}]`` or ``{"constituents": [...]}``,
        and sometimes a bare list of strings.
        """
        payload = self.shariah_constituents()
        return _extract_symbols(payload)

    # Market-watch
    def top_volume(self) -> Any:
        return self._get("topVolume")

    def top_gainers(self) -> Any:
        return self._get("topGainers")

    def top_losers(self) -> Any:
        return self._get("topLosers")

    # Metals (official EGX reference)
    def gold(self) -> Any:
        return self._get("gold")

    def silver(self) -> Any:
        return self._get("silver")

    # Fixed income — all banned under Sharia, exposed for context/visibility.
    def listed_sukuks(self) -> Any:
        return self._get("listedSukuks")

    def sovereign_sukuk(self) -> Any:
        return self._get("sovereignSukuk")

    def treasury_bonds(self) -> Any:
        return self._get("treasuryBonds")

    def listed_bills(self) -> Any:
        return self._get("listedBills")

    def derivatives(self) -> Any:
        return self._get("derivatives")

    # Statistics
    def investor_statistics(self) -> Any:
        return self._get("investorStatistics")

    def investor_full_statistics(self) -> Any:
        return self._get("investorFullStatistics")

    def stock_categories(self) -> Any:
        return self._get("stockCategories")


def _has_data(d: Any) -> bool:
    return isinstance(d, dict) and "data" in d


def _extract_symbols(payload: Any) -> list[str]:
    rows: Any
    if isinstance(payload, dict):
        rows = payload.get("constituents") or payload.get("symbols") or payload.get("items") or []
    else:
        rows = payload or []
    out: list[str] = []
    for row in rows:
        if isinstance(row, str):
            s = row
        elif isinstance(row, dict):
            s = str(row.get("symbol") or row.get("code") or row.get("ticker") or "")
        else:
            continue
        s = s.strip().upper()
        if s:
            out.append(s)
    # De-dupe preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique
