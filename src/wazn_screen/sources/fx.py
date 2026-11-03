"""Spot FX rates (EGP base) from open.er-api.com."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .http import HttpClient

URL = "https://open.er-api.com/v6/latest/EGP"


class FxRates:
    """Reference spot rates only — forwards/futures/margin FX are not Sharia-permissible.

    See :mod:`wazn_screen.rules.fx` for the rule check.
    """

    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient()

    def latest(self) -> dict[str, Decimal]:
        data = self._http.get_json(
            URL,
            validate=lambda d: isinstance(d, dict) and isinstance(d.get("rates"), dict),
        )
        rates: Any = data["rates"]
        return {str(k).upper(): Decimal(str(v)) for k, v in rates.items()}

    def rate(self, currency: str) -> Decimal:
        return self.latest()[currency.upper()]
