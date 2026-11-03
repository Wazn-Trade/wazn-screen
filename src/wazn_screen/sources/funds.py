"""Egyptian mutual funds — Railway tRPC endpoint from the terminal's inventory.

The upstream list is mixed; Sharia filtering is a client-side ``isIslamic``
flag per the inventory note. We expose both ``all()`` and the pre-filtered
``islamic()``.
"""

from __future__ import annotations

from typing import Any

from .http import HttpClient

URL = (
    "https://backend-blue.up.railway.app/api/trpc/funds.list"
    "?input=%7B%22json%22%3A%7B%22limit%22%3A500%7D%7D"
)


class Funds:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient()

    def all(self) -> list[dict[str, Any]]:
        data = self._http.get_json(URL, validate=_valid)
        funds: Any = data["result"]["data"]["json"]["funds"]
        return [f for f in funds if isinstance(f, dict)]

    def islamic(self) -> list[dict[str, Any]]:
        return [f for f in self.all() if _is_islamic(f)]


def _valid(d: Any) -> bool:
    try:
        return isinstance(d["result"]["data"]["json"]["funds"], list)
    except (KeyError, TypeError):
        return False


def _is_islamic(f: dict[str, Any]) -> bool:
    v = f.get("isIslamic")
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "islamic", "halal"}
    return False
