"""Stockastic — EGX 30 / 70 / 100 index dashboards (benchmarks only)."""

from __future__ import annotations

from typing import Any

from .http import HttpClient

INDICES = {
    "egx_30": "https://authapi.stockastic.app/api/dashboards/egx_index_30_v1",
    "egx_70": "https://authapi.stockastic.app/api/dashboards/egx_index_70_v1",
    "egx_100": "https://authapi.stockastic.app/api/dashboards/egx_index_100_v1",
}


class Stockastic:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient()

    def dashboard(self, name: str) -> Any:
        if name not in INDICES:
            raise ValueError(f"unknown index {name!r}; expected one of {sorted(INDICES)}")
        return self._http.get_json(INDICES[name])

    def all_dashboards(self) -> dict[str, Any]:
        return {k: self.dashboard(k) for k in INDICES}
