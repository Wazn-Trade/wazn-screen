"""AAOIFI-style financial screening (Shari'ah Standard No. 21) and purification.

EGX33 membership is the primary rule. This module recomputes the ratios from
quarterly statements so a stock drifting out of compliance is caught before the
next semi-annual review; a failing stock belongs on the no-buy watchlist.

The denominator choice (market cap vs. total assets) and the purification
methodology are fiqh decisions — record them in a decision log; don't change
them silently in code.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

DEBT_LIMIT = Decimal("0.30")
INTEREST_CASH_LIMIT = Decimal("0.30")
NON_COMPLIANT_INCOME_LIMIT = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class Financials:
    symbol: str
    interest_bearing_debt: Decimal
    interest_bearing_cash_and_investments: Decimal
    non_compliant_income: Decimal
    total_income: Decimal
    market_cap: Decimal


@dataclass(frozen=True, slots=True)
class ScreenResult:
    symbol: str
    debt_ratio: Decimal
    interest_cash_ratio: Decimal
    non_compliant_income_ratio: Decimal
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def screen(f: Financials) -> ScreenResult:
    if f.market_cap <= 0 or f.total_income <= 0:
        return ScreenResult(
            f.symbol, Decimal(0), Decimal(0), Decimal(0), ("insufficient data to screen",)
        )
    debt = f.interest_bearing_debt / f.market_cap
    cash = f.interest_bearing_cash_and_investments / f.market_cap
    income = f.non_compliant_income / f.total_income
    failures: list[str] = []
    if debt >= DEBT_LIMIT:
        failures.append(f"interest-bearing debt {debt:.1%} >= {DEBT_LIMIT:.0%} of market cap")
    if cash >= INTEREST_CASH_LIMIT:
        failures.append(f"interest-bearing cash {cash:.1%} >= {INTEREST_CASH_LIMIT:.0%}")
    if income >= NON_COMPLIANT_INCOME_LIMIT:
        failures.append(
            f"non-compliant income {income:.1%} >= {NON_COMPLIANT_INCOME_LIMIT:.0%} of revenue"
        )
    return ScreenResult(f.symbol, debt, cash, income, tuple(failures))


def purification_amount(
    dividends_received: Decimal, non_compliant_income: Decimal, total_income: Decimal
) -> Decimal:
    """Share of a dividend that must be given away (rounded up to the piastre)."""
    if dividends_received <= 0 or non_compliant_income <= 0:
        return Decimal(0)
    if total_income <= 0:
        return dividends_received
    ratio = min(non_compliant_income / total_income, Decimal(1))
    return (dividends_received * ratio).quantize(Decimal("0.01"), rounding="ROUND_CEILING")
