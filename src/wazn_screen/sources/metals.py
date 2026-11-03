"""Gold / silver spot prices (nagmadin.com).

Used for both metals quotes and the nisab calculation in
:mod:`wazn_screen.rules.zakat`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .http import HttpClient

CATALOG_URL = "https://nagmadin.com/api/metals?status=1"
LIVE_URL = "https://nagmadin.com/api/live-prices"


class Metals:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient()

    def catalog(self) -> list[dict[str, Any]]:
        data = self._http.get_json(
            CATALOG_URL,
            validate=lambda d: isinstance(d, dict) and isinstance(d.get("data"), list),
        )
        rows: Any = data["data"]
        return [r for r in rows if isinstance(r, dict)]

    def live(self) -> dict[str, Any]:
        data = self._http.get_json(
            LIVE_URL,
            validate=lambda d: isinstance(d, dict)
            and isinstance(d.get("data", {}), dict)
            and isinstance(d["data"].get("market_data", {}).get("rates_per_gram"), dict),
        )
        return data["data"]

    def rates_per_gram(self) -> dict[str, Decimal]:
        """Return a dict like ``{"gold_24k": Decimal("4500"), "silver": Decimal("55")}``."""
        payload: Any = self.live()["market_data"]["rates_per_gram"]
        return {str(k): Decimal(str(v)) for k, v in payload.items()}
