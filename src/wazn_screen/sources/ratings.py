"""Per-ticker Sharia ratings aggregator.

Pulls the eight-methodology aggregation hosted at
``whatsapp-sharia-bot.stockmarketeg.workers.dev/api/all`` and normalises each
ticker's verdict so callers can ask simple questions: "do most sources call
this halal?", "any source call it haram?".

This source is informational — the authoritative gate is the EGX_SHARIAH
whitelist. These ratings are useful for the early-warning watchlist and for
UI surfacing. Methodology names are preserved verbatim so audit trails stay
honest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .http import HttpClient

ALL_URL = "https://whatsapp-sharia-bot.stockmarketeg.workers.dev/api/all"

# From endpoints.txt. Keep this list; new keys the aggregator adds will show
# up in ``verdicts`` but won't be counted toward consensus unless added here.
METHODOLOGIES: tuple[str, ...] = (
    "halal_bourse",
    "musaffa",
    "kashif",
    "halal_invest",
    "faisal_bank",
    "osoul",
    "thndr",
    "mohamed_ramadan_sharia",
)

_PERMISSIBLE = {"halal", "compliant", "pass", "permissible", "yes", "true", "حلال"}
_PROHIBITED = {"haram", "non_compliant", "non-compliant", "fail", "prohibited", "no", "false", "حرام"}
_DOUBTFUL = {"doubtful", "mixed", "warning", "watchlist", "مشبوه"}


@dataclass(frozen=True, slots=True)
class RatingConsensus:
    symbol: str
    halal: int
    haram: int
    doubtful: int
    unknown: int
    verdicts: dict[str, str]

    @property
    def total(self) -> int:
        return self.halal + self.haram + self.doubtful + self.unknown

    @property
    def majority(self) -> str:
        """halal | haram | doubtful | unknown — strict majority, else 'doubtful'."""
        scores = {"halal": self.halal, "haram": self.haram, "doubtful": self.doubtful}
        best = max(scores, key=lambda k: scores[k])
        if scores[best] * 2 > self.total:
            return best
        return "doubtful"

    @property
    def any_haram(self) -> bool:
        return self.haram > 0


class ShariaRatings:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient()

    def all(self) -> dict[str, dict[str, Any]]:
        """Raw aggregator response, keyed by ticker."""
        data = self._http.get_json(ALL_URL, validate=lambda d: isinstance(d, (dict, list)))
        return _as_mapping(data)

    def consensus(self, symbol: str) -> RatingConsensus | None:
        """Return a normalised consensus for ``symbol`` or None if absent."""
        all_data = self.all()
        return self._consensus_from(symbol, all_data)

    def consensus_all(self) -> dict[str, RatingConsensus]:
        all_data = self.all()
        return {k: _summarise(k, v) for k, v in all_data.items() if isinstance(v, dict)}

    def _consensus_from(
        self, symbol: str, all_data: dict[str, dict[str, Any]]
    ) -> RatingConsensus | None:
        key = symbol.strip().upper()
        row = all_data.get(key) or all_data.get(symbol)
        if not isinstance(row, dict):
            return None
        return _summarise(key, row)


def _as_mapping(data: Any) -> dict[str, dict[str, Any]]:
    if isinstance(data, dict):
        return {str(k).strip().upper(): v for k, v in data.items() if isinstance(v, dict)}
    if isinstance(data, list):
        out: dict[str, dict[str, Any]] = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
            if sym:
                out[sym] = row
        return out
    return {}


def _summarise(symbol: str, row: dict[str, Any]) -> RatingConsensus:
    halal = haram = doubtful = unknown = 0
    verdicts: dict[str, str] = {}
    for m in METHODOLOGIES:
        raw = row.get(m)
        label = _label(raw)
        if label == "halal":
            halal += 1
        elif label == "haram":
            haram += 1
        elif label == "doubtful":
            doubtful += 1
        else:
            unknown += 1
        verdicts[m] = label
    return RatingConsensus(
        symbol=symbol,
        halal=halal,
        haram=haram,
        doubtful=doubtful,
        unknown=unknown,
        verdicts=verdicts,
    )


def _label(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, dict):
        # Common shape: {"verdict": "halal", "pdf_path": "..."}
        value = value.get("verdict") or value.get("rating") or value.get("status")
    s = str(value).strip().lower()
    if not s:
        return "unknown"
    if s in _PERMISSIBLE:
        return "halal"
    if s in _PROHIBITED:
        return "haram"
    if s in _DOUBTFUL:
        return "doubtful"
    return "unknown"
