"""Wazn Screen — public Sharia screening for Egypt (EGX33 and beyond)."""

from __future__ import annotations

from .loader import DEFAULT_UNIVERSE_YAML, load_default_universe
from .refresh import RefreshResult, refresh_universe, write_patch
from .rules import (
    FxDecision,
    MetalsDecision,
    NisabResult,
    SukukDecision,
    check_fx_transaction,
    check_metals_transaction,
    classify_sukuk,
    nisab_gold_grams,
    nisab_silver_grams,
    nisab_value,
)
from .screening import (
    DEBT_LIMIT,
    INTEREST_CASH_LIMIT,
    NON_COMPLIANT_INCOME_LIMIT,
    Financials,
    ScreenResult,
    purification_amount,
    screen,
)
from .sources import (
    EgxBff,
    Funds,
    FxRates,
    HttpClient,
    HttpError,
    Metals,
    Mubasher,
    ShariaRatings,
    Stockastic,
)
from .universe import (
    BANNED_SECURITY_CLASSES,
    DEFAULT_ALLOWED_SECURITY_CLASSES,
    Decision,
    ShariaUniverse,
    UniverseSnapshot,
)

__all__ = [
    "BANNED_SECURITY_CLASSES",
    "DEBT_LIMIT",
    "DEFAULT_ALLOWED_SECURITY_CLASSES",
    "DEFAULT_UNIVERSE_YAML",
    "Decision",
    "EgxBff",
    "Financials",
    "Funds",
    "FxDecision",
    "FxRates",
    "HttpClient",
    "HttpError",
    "INTEREST_CASH_LIMIT",
    "Metals",
    "MetalsDecision",
    "Mubasher",
    "NisabResult",
    "NON_COMPLIANT_INCOME_LIMIT",
    "RefreshResult",
    "ScreenResult",
    "ShariaRatings",
    "ShariaUniverse",
    "Stockastic",
    "SukukDecision",
    "UniverseSnapshot",
    "check_fx_transaction",
    "check_metals_transaction",
    "classify_sukuk",
    "load_default_universe",
    "nisab_gold_grams",
    "nisab_silver_grams",
    "nisab_value",
    "purification_amount",
    "refresh_universe",
    "screen",
    "write_patch",
]

__version__ = "0.1.0"
