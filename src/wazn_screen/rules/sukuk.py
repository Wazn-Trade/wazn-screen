"""Sukuk classifier.

Sukuk ≠ bonds. A sukuk represents fractional ownership in an underlying asset
or venture (``ijara``, ``mudaraba``, ``musharaka``, ``istisna'``) and is
permissible when the structure is sound. ``Murabaha`` sukuk are permissible
only if the certificates are not sold in the secondary market after goods are
delivered (because they then represent monetary debt).

This classifier maps a known structure name to a decision. The authoritative
check for a specific issuance is a Sharia board fatwa; this helper surfaces
the common cases.
"""

from __future__ import annotations

from dataclasses import dataclass

PERMISSIBLE_STRUCTURES: frozenset[str] = frozenset(
    {"ijara", "mudaraba", "musharaka", "istisna", "istisna'", "wakala", "salam"}
)
CONDITIONAL_STRUCTURES: frozenset[str] = frozenset({"murabaha"})
IMPERMISSIBLE_STRUCTURES: frozenset[str] = frozenset({"conventional_bond", "interest_bearing"})


@dataclass(frozen=True, slots=True)
class SukukDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()
    needs_fatwa_review: bool = False


def classify_sukuk(*, structure: str, tradable_after_delivery: bool = True) -> SukukDecision:
    s = structure.strip().lower().replace("-", "_")
    if s in IMPERMISSIBLE_STRUCTURES:
        return SukukDecision(False, (f"{structure} is an interest-bearing instrument",))
    if s in PERMISSIBLE_STRUCTURES:
        return SukukDecision(True, (), needs_fatwa_review=True)
    if s in CONDITIONAL_STRUCTURES:
        if tradable_after_delivery:
            return SukukDecision(
                False,
                (
                    "murabaha sukuk sold on the secondary market after goods are "
                    "delivered represent monetary debt",
                ),
            )
        return SukukDecision(True, (), needs_fatwa_review=True)
    return SukukDecision(False, (f"unknown sukuk structure {structure!r}",))
