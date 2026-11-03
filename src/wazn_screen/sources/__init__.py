"""Data sources for Egyptian markets.

Thin, typed clients over the third-party endpoints that feed Sharia screening.
All clients are synchronous (``httpx.Client``) so they're usable from CLIs,
scripts, and the engine without an event loop.

Public re-exports:
"""

from __future__ import annotations

from .egx_bff import EgxBff
from .fx import FxRates
from .http import DEFAULT_UA, HttpClient, HttpError
from .funds import Funds
from .metals import Metals
from .mubasher import Mubasher
from .ratings import ShariaRatings
from .stockastic import Stockastic

__all__ = [
    "DEFAULT_UA",
    "EgxBff",
    "Funds",
    "FxRates",
    "HttpClient",
    "HttpError",
    "Metals",
    "Mubasher",
    "ShariaRatings",
    "Stockastic",
]
