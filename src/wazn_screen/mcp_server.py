"""MCP server — `wazn-screen-mcp`. Needs the `[mcp]` extra.

Read-only screening tools: no broker, no trade intent.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from .loader import load_default_universe
from .refresh import refresh_universe
from .rules import (
    check_fx_transaction,
    check_metals_transaction,
    classify_sukuk,
    nisab_value,
)
from .screening import Financials, purification_amount, screen
from .sources import EgxBff, FxRates, Metals, ShariaRatings


def _build_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as e:
        raise SystemExit(
            "wazn-screen-mcp requires the [mcp] extra: pip install 'wazn-screen[mcp]'"
        ) from e

    universe = load_default_universe()
    mcp = FastMCP("wazn-screen")

    @mcp.tool()
    def can_buy(
        symbol: str,
        security_class: str = "LocalSecurity_IN",
        on: str | None = None,
    ) -> dict[str, Any]:
        """Check whether a symbol passes the Sharia whitelist on a given date (ISO)."""
        day = date.fromisoformat(on) if on else date.today()
        d = universe.can_buy(symbol, security_class, day)
        return {
            "symbol": symbol.upper(),
            "security_class": security_class,
            "date": day.isoformat(),
            "allowed": d.allowed,
            "reasons": list(d.reasons),
        }

    @mcp.tool()
    def list_universe(on: str | None = None) -> dict[str, Any]:
        """List EGX_SHARIAH members effective on a given date."""
        day = date.fromisoformat(on) if on else date.today()
        snap = universe.snapshot_on(day)
        if snap is None:
            return {"date": day.isoformat(), "effective_date": None, "members": []}
        return {
            "date": day.isoformat(),
            "effective_date": snap.effective_date.isoformat(),
            "review_effective_date": (
                snap.review_effective_date.isoformat() if snap.review_effective_date else None
            ),
            "source": snap.source,
            "members": sorted(snap.symbols),
        }

    @mcp.tool()
    def screen_financials(
        symbol: str,
        interest_bearing_debt: float,
        interest_bearing_cash_and_investments: float,
        non_compliant_income: float,
        total_income: float,
        market_cap: float,
    ) -> dict[str, Any]:
        """AAOIFI Standard #21 financial screen (ratios + pass/fail)."""
        r = screen(
            Financials(
                symbol=symbol,
                interest_bearing_debt=Decimal(str(interest_bearing_debt)),
                interest_bearing_cash_and_investments=Decimal(
                    str(interest_bearing_cash_and_investments)
                ),
                non_compliant_income=Decimal(str(non_compliant_income)),
                total_income=Decimal(str(total_income)),
                market_cap=Decimal(str(market_cap)),
            )
        )
        return {
            "symbol": r.symbol,
            "passed": r.passed,
            "debt_ratio": str(r.debt_ratio),
            "interest_cash_ratio": str(r.interest_cash_ratio),
            "non_compliant_income_ratio": str(r.non_compliant_income_ratio),
            "failures": list(r.failures),
        }

    @mcp.tool()
    def purification(
        dividends_received: float, non_compliant_income: float, total_income: float
    ) -> dict[str, str]:
        """Share of a dividend to give away (purification)."""
        amount = purification_amount(
            Decimal(str(dividends_received)),
            Decimal(str(non_compliant_income)),
            Decimal(str(total_income)),
        )
        return {"purification_amount": str(amount)}

    @mcp.tool()
    def check_fx(
        kind: str,
        settlement_days: int = 0,
        uses_margin: bool = False,
        same_currency: bool = False,
    ) -> dict[str, Any]:
        """Is an FX transaction Sharia-permissible? Spot-only, no margin, no deferral."""
        d = check_fx_transaction(
            kind=kind,
            settlement_days=settlement_days,
            uses_margin=uses_margin,
            same_currency=same_currency,
        )
        return {"allowed": d.allowed, "reasons": list(d.reasons)}

    @mcp.tool()
    def check_metals(
        metal: str, form: str, settlement_days: int = 0, uses_margin: bool = False
    ) -> dict[str, Any]:
        """Is a gold/silver transaction Sharia-permissible? Physical, same-session."""
        d = check_metals_transaction(
            metal=metal, form=form, settlement_days=settlement_days, uses_margin=uses_margin
        )
        return {"allowed": d.allowed, "reasons": list(d.reasons)}

    @mcp.tool()
    def check_sukuk(structure: str, tradable_after_delivery: bool = True) -> dict[str, Any]:
        """Classify a sukuk structure (ijara, mudaraba, murabaha, ...)."""
        d = classify_sukuk(
            structure=structure, tradable_after_delivery=tradable_after_delivery
        )
        return {
            "allowed": d.allowed,
            "reasons": list(d.reasons),
            "needs_fatwa_review": d.needs_fatwa_review,
        }

    @mcp.tool()
    def zakat(
        wealth: float,
        gold_price_per_gram: float,
        silver_price_per_gram: float,
        prefer: str = "silver",
    ) -> dict[str, Any]:
        """Compute nisab and the zakat amount due on monetary wealth."""
        r = nisab_value(
            wealth=Decimal(str(wealth)),
            gold_price_per_gram=Decimal(str(gold_price_per_gram)),
            silver_price_per_gram=Decimal(str(silver_price_per_gram)),
            prefer=prefer,
        )
        return {
            "gold_nisab_value": str(r.gold_nisab_value),
            "silver_nisab_value": str(r.silver_nisab_value),
            "chosen_nisab": str(r.chosen_nisab),
            "chosen_metal": r.chosen_metal,
            "due_amount": str(r.due_amount),
            "is_zakat_due": r.is_zakat_due,
        }

    @mcp.tool()
    def live_egx_shariah() -> dict[str, Any]:
        """Fetch the current EGX_SHARIAH constituents from the EGX BFF (live)."""
        return {"symbols": EgxBff().shariah_symbols()}

    @mcp.tool()
    def live_ratings(symbol: str | None = None) -> dict[str, Any]:
        """Fetch Sharia ratings aggregator (eight methodologies). Optionally for one symbol."""
        if symbol:
            c = ShariaRatings().consensus(symbol)
            if c is None:
                return {"symbol": symbol.upper(), "found": False}
            return {
                "symbol": c.symbol,
                "found": True,
                "halal": c.halal,
                "haram": c.haram,
                "doubtful": c.doubtful,
                "unknown": c.unknown,
                "majority": c.majority,
                "any_haram": c.any_haram,
                "verdicts": c.verdicts,
            }
        return {
            k: {
                "halal": v.halal,
                "haram": v.haram,
                "doubtful": v.doubtful,
                "unknown": v.unknown,
                "majority": v.majority,
            }
            for k, v in ShariaRatings().consensus_all().items()
        }

    @mcp.tool()
    def live_fx() -> dict[str, str]:
        """Spot FX rates (EGP base). Reference only — see /rules/fx for permissibility."""
        return {k: str(v) for k, v in FxRates().latest().items()}

    @mcp.tool()
    def live_metals() -> dict[str, str]:
        """Spot gold/silver prices (EGP per gram)."""
        return {k: str(v) for k, v in Metals().rates_per_gram().items()}

    @mcp.tool()
    def refresh_universe_tool(write: bool = False, force: bool = False) -> dict[str, Any]:
        """Fetch EGX_SHARIAH from the BFF and (optionally) append a new snapshot."""
        result = refresh_universe(force=force)
        if write and result.yaml_patch:
            from .refresh import write_patch

            write_patch(result)
        return {
            "path": str(result.path),
            "observed": result.observed.isoformat(),
            "fetched_symbol_count": len(result.fetched_symbols),
            "added": result.added,
            "unchanged": result.unchanged,
            "written": bool(write and result.yaml_patch),
            "reason": result.reason,
            "patch": result.yaml_patch,
        }

    return mcp


def main(argv: list[str] | None = None) -> int:
    _build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
