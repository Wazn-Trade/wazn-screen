"""Precious metals (gold, silver) — spot only, physical delivery, no deferral.

Reference: AAOIFI Shari'ah Standard No. 57 (Gold and its Trading Controls).
Gold and silver are ``athman`` (monetary metals); their exchange must be
hand-to-hand and equal when of the same kind.
"""

from __future__ import annotations

from dataclasses import dataclass

PROHIBITED_FORMS: frozenset[str] = frozenset(
    {"future", "forward", "cfd", "etf_leveraged", "margin", "paper_unallocated"}
)


@dataclass(frozen=True, slots=True)
class MetalsDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()


def check_metals_transaction(
    *,
    metal: str,
    form: str,
    settlement_days: int = 0,
    uses_margin: bool = False,
) -> MetalsDecision:
    """Evaluate a gold/silver transaction.

    - ``metal`` ∈ {"gold", "silver"} (anything else returns an informational message).
    - ``form`` ∈ {"physical", "allocated", "paper_unallocated", "etf_physical",
      "etf_leveraged", "future", "forward", "cfd", "margin"}.
    - Physical / allocated / 100%-physical-backed ETFs with same-day delivery = OK.
    - Anything deferred, unallocated, or leveraged = not permissible.
    """
    reasons: list[str] = []
    m = metal.strip().lower()
    if m not in {"gold", "silver"}:
        # Base metals (copper, etc.) have different rules; this function doesn't opine.
        reasons.append(f"{m} is not a monetary metal under AAOIFI SS 57")
    f = form.strip().lower()
    if f in PROHIBITED_FORMS:
        reasons.append(f"{f} metals are not Sharia-permissible (deferral/leverage)")
    if settlement_days > 0:
        reasons.append(
            f"settlement T+{settlement_days} is not hand-to-hand (must be same session)"
        )
    if uses_margin:
        reasons.append("metals on margin are not Sharia-permissible")
    return MetalsDecision(allowed=not reasons, reasons=tuple(reasons))
