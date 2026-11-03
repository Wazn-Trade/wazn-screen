"""EGX33 Shariah universe and the whitelist that every BUY must pass.

Design rules (fail-closed):

- A symbol is buyable only if it is in the EGX33 snapshot effective on that date
  AND its security class is explicitly allowed. Unknown class -> denied.
- No snapshot for the date, or a stale one (older than ``max_age_days``) -> every
  BUY denied until someone loads the latest semi-annual review.
- Some security classes are banned outright (T-bills, bonds, derivatives) even if
  they somehow appear in the list.
- SELL is never blocked here — exiting a stock that fell out of the index must
  always be possible. Short-selling is a separate concern (not this layer).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

BANNED_SECURITY_CLASSES: frozenset[str] = frozenset(
    {
        "Tbills",
        "PrivateBond_IN",
        "FuturesDerivativeContracts",
        "OTC",
    }
)
DEFAULT_ALLOWED_SECURITY_CLASSES: frozenset[str] = frozenset({"LocalSecurity_IN"})


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    effective_date: date
    symbols: frozenset[str]
    source: str
    review_effective_date: date | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class ShariaUniverse:
    snapshots: list[UniverseSnapshot]
    max_age_days: int = 200
    allowed_security_classes: frozenset[str] = DEFAULT_ALLOWED_SECURITY_CLASSES
    watchlist_no_buy: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        self.snapshots = sorted(self.snapshots, key=lambda s: s.effective_date)
        overlap = self.allowed_security_classes & BANNED_SECURITY_CLASSES
        if overlap:
            raise ValueError(f"banned security classes cannot be allowed: {sorted(overlap)}")

    @classmethod
    def from_yaml(cls, path: str | Path) -> ShariaUniverse:
        raw: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        snapshots = [
            UniverseSnapshot(
                effective_date=_as_date(s["effective_date"]),
                symbols=frozenset(_normalise(s.get("symbols") or [])),
                source=str(s.get("source", "")),
                review_effective_date=(
                    _as_date(s["review_effective_date"])
                    if s.get("review_effective_date")
                    else None
                ),
            )
            for s in raw.get("snapshots") or []
        ]
        return cls(
            snapshots=snapshots,
            max_age_days=int(raw.get("max_age_days", 200)),
            allowed_security_classes=frozenset(
                raw.get("allowed_security_classes") or DEFAULT_ALLOWED_SECURITY_CLASSES
            ),
            watchlist_no_buy=frozenset(_normalise(raw.get("watchlist_no_buy") or [])),
        )

    def snapshot_on(self, day: date) -> UniverseSnapshot | None:
        eligible = [s for s in self.snapshots if s.effective_date <= day]
        return eligible[-1] if eligible else None

    def members_on(self, day: date) -> frozenset[str]:
        snap = self.snapshot_on(day)
        return snap.symbols if snap else frozenset()

    def can_buy(self, symbol: str, security_class: str | None, day: date) -> Decision:
        symbol = symbol.strip().upper()
        reasons: list[str] = []
        snap = self.snapshot_on(day)
        if snap is None or not snap.symbols:
            reasons.append(f"no EGX33 snapshot effective on {day}")
        else:
            age = (day - snap.effective_date).days
            if age > self.max_age_days:
                reasons.append(
                    f"EGX33 snapshot from {snap.effective_date} is {age} days old "
                    f"(max {self.max_age_days}); load the latest review"
                )
            if symbol not in snap.symbols:
                reasons.append(f"{symbol} is not an EGX33 constituent on {day}")
        if security_class is None:
            reasons.append(f"{symbol} has unknown security class")
        elif security_class in BANNED_SECURITY_CLASSES:
            reasons.append(f"{symbol} security class {security_class} is banned")
        elif security_class not in self.allowed_security_classes:
            reasons.append(f"{symbol} security class {security_class} is not whitelisted")
        if symbol in self.watchlist_no_buy:
            reasons.append(f"{symbol} is on the AAOIFI no-buy watchlist")
        return Decision(allowed=not reasons, reasons=tuple(reasons))


def _normalise(symbols: Iterable[Any]) -> list[str]:
    return [str(s).strip().upper() for s in symbols if str(s).strip()]


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
