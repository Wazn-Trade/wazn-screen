"""`wazn-screen` command — one-shot screening and data lookups."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from .loader import load_default_universe
from .refresh import refresh_universe, write_patch
from .rules import (
    check_fx_transaction,
    check_metals_transaction,
    classify_sukuk,
    nisab_value,
)
from .screening import Financials, purification_amount, screen


def _parse_date(s: str | None) -> date:
    return date.fromisoformat(s) if s else date.today()


def _emit(obj: Any) -> None:
    json.dump(obj, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wazn-screen", description="Sharia screening for EGX33 and Egypt."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("symbol", help="Check whether a symbol is buyable.")
    p.add_argument("symbol")
    p.add_argument("--security-class", default="LocalSecurity_IN")
    p.add_argument("--date", dest="on")

    p = sub.add_parser("universe", help="List members of the index on a given date.")
    p.add_argument("--date", dest="on")

    p = sub.add_parser("screen", help="Run AAOIFI financial screen.")
    p.add_argument("--symbol", required=True)
    p.add_argument("--debt", required=True, type=Decimal)
    p.add_argument("--interest-cash", required=True, type=Decimal)
    p.add_argument("--non-compliant-income", required=True, type=Decimal)
    p.add_argument("--total-income", required=True, type=Decimal)
    p.add_argument("--market-cap", required=True, type=Decimal)

    p = sub.add_parser("purify", help="Compute dividend purification amount.")
    p.add_argument("--dividends", required=True, type=Decimal)
    p.add_argument("--non-compliant-income", required=True, type=Decimal)
    p.add_argument("--total-income", required=True, type=Decimal)

    p = sub.add_parser(
        "refresh-universe",
        help="Fetch EGX_SHARIAH constituents from the BFF and append a snapshot.",
    )
    p.add_argument(
        "--write", action="store_true", help="Persist the new snapshot (default: dry-run)."
    )
    p.add_argument("--force", action="store_true", help="Append even if symbols are unchanged.")
    p.add_argument("--path", help="YAML path; defaults to the bundled snapshot.")
    p.add_argument("--date", dest="on", help="Observation date (default: today).")
    p.add_argument("--source", help="Source string recorded in the snapshot.")

    p = sub.add_parser("fx", help="Check an FX transaction for Sharia permissibility.")
    p.add_argument("--kind", required=True, choices=["spot", "forward", "future", "swap", "option", "ndf", "margin"])
    p.add_argument("--settlement-days", type=int, default=0)
    p.add_argument("--margin", action="store_true")

    p = sub.add_parser("metals", help="Check a gold/silver transaction.")
    p.add_argument("--metal", required=True, choices=["gold", "silver"])
    p.add_argument(
        "--form",
        required=True,
        choices=[
            "physical", "allocated", "paper_unallocated", "etf_physical",
            "etf_leveraged", "future", "forward", "cfd", "margin",
        ],
    )
    p.add_argument("--settlement-days", type=int, default=0)
    p.add_argument("--margin", action="store_true")

    p = sub.add_parser("sukuk", help="Classify a sukuk structure.")
    p.add_argument("--structure", required=True)
    p.add_argument(
        "--tradable-after-delivery", action="store_true",
        help="Whether certificates are sold in secondary market post-delivery (murabaha).",
    )

    p = sub.add_parser("zakat", help="Compute nisab and zakat due on wealth.")
    p.add_argument("--wealth", required=True, type=Decimal)
    p.add_argument("--gold-price-per-gram", required=True, type=Decimal)
    p.add_argument("--silver-price-per-gram", required=True, type=Decimal)
    p.add_argument("--prefer", choices=["gold", "silver"], default="silver")

    args = parser.parse_args(argv)

    if args.cmd == "symbol":
        u = load_default_universe()
        d = u.can_buy(args.symbol, args.security_class, _parse_date(args.on))
        _emit({"allowed": d.allowed, "reasons": list(d.reasons)})
        return 0 if d.allowed else 1

    if args.cmd == "universe":
        u = load_default_universe()
        snap = u.snapshot_on(_parse_date(args.on))
        if snap is None:
            _emit({"members": [], "effective_date": None})
            return 1
        _emit(
            {
                "effective_date": snap.effective_date.isoformat(),
                "review_effective_date": (
                    snap.review_effective_date.isoformat() if snap.review_effective_date else None
                ),
                "source": snap.source,
                "members": sorted(snap.symbols),
            }
        )
        return 0

    if args.cmd == "screen":
        r = screen(
            Financials(
                symbol=args.symbol,
                interest_bearing_debt=args.debt,
                interest_bearing_cash_and_investments=args.interest_cash,
                non_compliant_income=args.non_compliant_income,
                total_income=args.total_income,
                market_cap=args.market_cap,
            )
        )
        _emit(
            {
                "symbol": r.symbol,
                "passed": r.passed,
                "debt_ratio": str(r.debt_ratio),
                "interest_cash_ratio": str(r.interest_cash_ratio),
                "non_compliant_income_ratio": str(r.non_compliant_income_ratio),
                "failures": list(r.failures),
            }
        )
        return 0 if r.passed else 1

    if args.cmd == "purify":
        amount = purification_amount(args.dividends, args.non_compliant_income, args.total_income)
        _emit({"purification_amount": str(amount)})
        return 0

    if args.cmd == "refresh-universe":
        result = refresh_universe(
            path=Path(args.path) if args.path else None,
            on=_parse_date(args.on) if args.on else None,
            source=args.source,
            force=args.force,
        )
        if args.write and result.yaml_patch:
            write_patch(result)
        _emit(
            {
                "path": str(result.path),
                "observed": result.observed.isoformat(),
                "fetched_symbol_count": len(result.fetched_symbols),
                "added": result.added,
                "unchanged": result.unchanged,
                "written": bool(args.write and result.yaml_patch),
                "reason": result.reason,
                "patch": result.yaml_patch,
            }
        )
        return 0

    if args.cmd == "fx":
        d = check_fx_transaction(
            kind=args.kind, settlement_days=args.settlement_days, uses_margin=args.margin
        )
        _emit({"allowed": d.allowed, "reasons": list(d.reasons)})
        return 0 if d.allowed else 1

    if args.cmd == "metals":
        d = check_metals_transaction(
            metal=args.metal,
            form=args.form,
            settlement_days=args.settlement_days,
            uses_margin=args.margin,
        )
        _emit({"allowed": d.allowed, "reasons": list(d.reasons)})
        return 0 if d.allowed else 1

    if args.cmd == "sukuk":
        d = classify_sukuk(
            structure=args.structure, tradable_after_delivery=args.tradable_after_delivery
        )
        _emit(
            {
                "allowed": d.allowed,
                "reasons": list(d.reasons),
                "needs_fatwa_review": d.needs_fatwa_review,
            }
        )
        return 0 if d.allowed else 1

    if args.cmd == "zakat":
        r = nisab_value(
            wealth=args.wealth,
            gold_price_per_gram=args.gold_price_per_gram,
            silver_price_per_gram=args.silver_price_per_gram,
            prefer=args.prefer,
        )
        _emit(
            {
                "gold_nisab_value": str(r.gold_nisab_value),
                "silver_nisab_value": str(r.silver_nisab_value),
                "chosen_nisab": str(r.chosen_nisab),
                "chosen_metal": r.chosen_metal,
                "due_amount": str(r.due_amount),
                "is_zakat_due": r.is_zakat_due,
            }
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
