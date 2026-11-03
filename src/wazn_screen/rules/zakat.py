"""Zakat helpers — nisab in gold / silver.

Classical nisab:

- Gold:   85 grams of pure gold (20 mithqal × 4.25 g, following AAOIFI SS 35).
- Silver: 595 grams of pure silver (200 dirhams × 2.975 g).

The silver nisab is more generous (lower value threshold) and is generally
preferred for cash and trade-goods zakat because it protects more poor
beneficiaries. Zakat rate on monetary wealth is 2.5% once a lunar year
(``hawl``) has passed on wealth above nisab.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

GOLD_NISAB_GRAMS = Decimal("85")
SILVER_NISAB_GRAMS = Decimal("595")
ZAKAT_RATE = Decimal("0.025")


def nisab_gold_grams() -> Decimal:
    return GOLD_NISAB_GRAMS


def nisab_silver_grams() -> Decimal:
    return SILVER_NISAB_GRAMS


@dataclass(frozen=True, slots=True)
class NisabResult:
    gold_nisab_value: Decimal
    silver_nisab_value: Decimal
    chosen_nisab: Decimal
    chosen_metal: str  # "gold" or "silver"
    due_amount: Decimal
    is_zakat_due: bool


def nisab_value(
    *,
    wealth: Decimal,
    gold_price_per_gram: Decimal,
    silver_price_per_gram: Decimal,
    prefer: str = "silver",
) -> NisabResult:
    """Return nisab values and whether zakat is due on ``wealth``.

    ``prefer`` picks which metal's threshold to use for the ``is_zakat_due``
    decision — ``"silver"`` is the fiqh-conservative default.
    """
    gold_v = GOLD_NISAB_GRAMS * gold_price_per_gram
    silver_v = SILVER_NISAB_GRAMS * silver_price_per_gram
    chosen = silver_v if prefer.lower() == "silver" else gold_v
    due = (wealth * ZAKAT_RATE).quantize(Decimal("0.01")) if wealth >= chosen else Decimal(0)
    return NisabResult(
        gold_nisab_value=gold_v,
        silver_nisab_value=silver_v,
        chosen_nisab=chosen,
        chosen_metal="silver" if prefer.lower() == "silver" else "gold",
        due_amount=due,
        is_zakat_due=wealth >= chosen,
    )
