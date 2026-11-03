"""HTTP API — `wazn-screen-api` script. Needs the `[api]` extra."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from .loader import load_default_universe
from .refresh import refresh_universe
from .rules import (
    check_fx_transaction,
    check_metals_transaction,
    classify_sukuk,
    nisab_value,
)
from .screening import Financials, purification_amount, screen
from .sources import EgxBff, FxRates, Metals, Mubasher, ShariaRatings

if TYPE_CHECKING:
    from fastapi import FastAPI


def _make_app() -> FastAPI:
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ModuleNotFoundError as e:
        raise SystemExit(
            "wazn-screen-api requires the [api] extra: pip install 'wazn-screen[api]'"
        ) from e

    universe = load_default_universe()
    app = FastAPI(title="Wazn Screen", version="0.1.0")

    class FinancialsIn(BaseModel):
        symbol: str
        interest_bearing_debt: Decimal
        interest_bearing_cash_and_investments: Decimal
        non_compliant_income: Decimal
        total_income: Decimal
        market_cap: Decimal

    class PurificationIn(BaseModel):
        dividends_received: Decimal
        non_compliant_income: Decimal
        total_income: Decimal

    class FxIn(BaseModel):
        kind: str
        settlement_days: int = 0
        uses_margin: bool = False
        same_currency: bool = False

    class MetalsIn(BaseModel):
        metal: str
        form: str
        settlement_days: int = 0
        uses_margin: bool = False

    class SukukIn(BaseModel):
        structure: str
        tradable_after_delivery: bool = True

    class ZakatIn(BaseModel):
        wealth: Decimal
        gold_price_per_gram: Decimal
        silver_price_per_gram: Decimal
        prefer: str = "silver"

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/universe")
    def get_universe(on: date | None = None) -> dict[str, Any]:
        snap = universe.snapshot_on(on or date.today())
        if snap is None:
            raise HTTPException(status_code=404, detail="no snapshot effective on that date")
        return {
            "effective_date": snap.effective_date.isoformat(),
            "review_effective_date": (
                snap.review_effective_date.isoformat() if snap.review_effective_date else None
            ),
            "source": snap.source,
            "members": sorted(snap.symbols),
        }

    @app.get("/can-buy/{symbol}")
    def can_buy(
        symbol: str, security_class: str = "LocalSecurity_IN", on: date | None = None
    ) -> dict[str, Any]:
        d = universe.can_buy(symbol, security_class, on or date.today())
        return {"symbol": symbol.upper(), "allowed": d.allowed, "reasons": list(d.reasons)}

    @app.post("/screen")
    def post_screen(payload: FinancialsIn) -> dict[str, Any]:
        r = screen(Financials(**payload.model_dump()))
        return {
            "symbol": r.symbol,
            "passed": r.passed,
            "debt_ratio": str(r.debt_ratio),
            "interest_cash_ratio": str(r.interest_cash_ratio),
            "non_compliant_income_ratio": str(r.non_compliant_income_ratio),
            "failures": list(r.failures),
        }

    @app.post("/purification")
    def post_purification(payload: PurificationIn) -> dict[str, str]:
        amount = purification_amount(
            payload.dividends_received, payload.non_compliant_income, payload.total_income
        )
        return {"purification_amount": str(amount)}

    @app.post("/rules/fx")
    def rule_fx(payload: FxIn) -> dict[str, Any]:
        d = check_fx_transaction(
            kind=payload.kind,
            settlement_days=payload.settlement_days,
            uses_margin=payload.uses_margin,
            same_currency=payload.same_currency,
        )
        return {"allowed": d.allowed, "reasons": list(d.reasons)}

    @app.post("/rules/metals")
    def rule_metals(payload: MetalsIn) -> dict[str, Any]:
        d = check_metals_transaction(
            metal=payload.metal,
            form=payload.form,
            settlement_days=payload.settlement_days,
            uses_margin=payload.uses_margin,
        )
        return {"allowed": d.allowed, "reasons": list(d.reasons)}

    @app.post("/rules/sukuk")
    def rule_sukuk(payload: SukukIn) -> dict[str, Any]:
        d = classify_sukuk(
            structure=payload.structure, tradable_after_delivery=payload.tradable_after_delivery
        )
        return {
            "allowed": d.allowed,
            "reasons": list(d.reasons),
            "needs_fatwa_review": d.needs_fatwa_review,
        }

    @app.post("/rules/zakat")
    def rule_zakat(payload: ZakatIn) -> dict[str, Any]:
        r = nisab_value(
            wealth=payload.wealth,
            gold_price_per_gram=payload.gold_price_per_gram,
            silver_price_per_gram=payload.silver_price_per_gram,
            prefer=payload.prefer,
        )
        return {
            "gold_nisab_value": str(r.gold_nisab_value),
            "silver_nisab_value": str(r.silver_nisab_value),
            "chosen_nisab": str(r.chosen_nisab),
            "chosen_metal": r.chosen_metal,
            "due_amount": str(r.due_amount),
            "is_zakat_due": r.is_zakat_due,
        }

    # Live data pass-throughs (opt-in; call out to third-party origins).
    @app.get("/live/egx-shariah")
    def live_shariah() -> dict[str, Any]:
        bff = EgxBff()
        return {"symbols": bff.shariah_symbols()}

    @app.get("/live/prices")
    def live_prices() -> list[dict[str, Any]]:
        return Mubasher().prices()

    @app.get("/live/ratings")
    def live_ratings() -> dict[str, Any]:
        rows = ShariaRatings().consensus_all()
        return {
            k: {
                "halal": v.halal,
                "haram": v.haram,
                "doubtful": v.doubtful,
                "unknown": v.unknown,
                "majority": v.majority,
                "any_haram": v.any_haram,
                "verdicts": v.verdicts,
            }
            for k, v in rows.items()
        }

    @app.get("/live/fx")
    def live_fx() -> dict[str, str]:
        return {k: str(v) for k, v in FxRates().latest().items()}

    @app.get("/live/metals")
    def live_metals() -> dict[str, str]:
        return {k: str(v) for k, v in Metals().rates_per_gram().items()}

    @app.post("/refresh-universe")
    def post_refresh_universe(write: bool = False, force: bool = False) -> dict[str, Any]:
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

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wazn-screen-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    try:
        import uvicorn
    except ModuleNotFoundError as e:
        raise SystemExit(
            "wazn-screen-api requires the [api] extra: pip install 'wazn-screen[api]'"
        ) from e
    uvicorn.run(_make_app(), host=args.host, port=args.port)
    return 0


def __getattr__(name: str) -> Any:
    if name == "app":
        return _make_app()
    raise AttributeError(name)


if __name__ == "__main__":
    raise SystemExit(main())
