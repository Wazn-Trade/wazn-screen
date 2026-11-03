"""FX permissibility — spot only, hand-to-hand, no margin, no forwards.

Reference: AAOIFI Shari'ah Standard No. 1 (Trading in Currencies). Deferred
exchange of two different currencies is impermissible; same-currency deferral
with equality (``mithlan bi-mithlin``) is permitted but not an FX trade.
"""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_KINDS: frozenset[str] = frozenset({"spot"})
PROHIBITED_KINDS: frozenset[str] = frozenset(
    {"forward", "future", "swap", "option", "ndf", "margin"}
)


@dataclass(frozen=True, slots=True)
class FxDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()


def check_fx_transaction(
    *,
    kind: str,
    settlement_days: int = 0,
    uses_margin: bool = False,
    same_currency: bool = False,
) -> FxDecision:
    """Evaluate an FX transaction.

    - ``kind`` ∈ {"spot", "forward", "future", "swap", "option", "ndf", "margin"}
    - ``settlement_days`` for a spot deal is T+0..T+2 (operational); anything
      longer is treated as a forward.
    - ``uses_margin`` → blocks (riba exposure).
    - ``same_currency`` → not an FX trade; returns an informational message.
    """
    reasons: list[str] = []
    k = kind.strip().lower()
    if same_currency:
        reasons.append("same-currency transfer is not an FX trade")
    if k in PROHIBITED_KINDS:
        reasons.append(f"{k} FX is not Sharia-permissible (deferral or margin involved)")
    elif k not in ALLOWED_KINDS:
        reasons.append(f"unknown FX kind {k!r}")
    if uses_margin:
        reasons.append("FX on margin is not Sharia-permissible (riba)")
    if settlement_days > 2:
        reasons.append(
            f"settlement T+{settlement_days} exceeds spot (T+0..T+2); treated as a forward"
        )
    return FxDecision(allowed=not reasons, reasons=tuple(reasons))
