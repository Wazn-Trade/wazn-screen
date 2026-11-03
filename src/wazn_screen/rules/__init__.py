"""Shari'ah rule helpers for instrument types other than listed equities.

Equities go through :mod:`wazn_screen.universe` and :mod:`wazn_screen.screening`.
These modules cover the surrounding instrument classes a Sharia-aware app has
to answer questions about.
"""

from __future__ import annotations

from .fx import FxDecision, check_fx_transaction
from .metals import MetalsDecision, check_metals_transaction
from .sukuk import SukukDecision, classify_sukuk
from .zakat import NisabResult, nisab_gold_grams, nisab_silver_grams, nisab_value

__all__ = [
    "FxDecision",
    "MetalsDecision",
    "NisabResult",
    "SukukDecision",
    "check_fx_transaction",
    "check_metals_transaction",
    "classify_sukuk",
    "nisab_gold_grams",
    "nisab_silver_grams",
    "nisab_value",
]
