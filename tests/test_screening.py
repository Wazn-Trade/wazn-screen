from decimal import Decimal

from wazn_screen import Financials, purification_amount, screen


def _f(**overrides: Decimal) -> Financials:
    defaults: dict[str, Decimal] = dict(
        interest_bearing_debt=Decimal("100"),
        interest_bearing_cash_and_investments=Decimal("50"),
        non_compliant_income=Decimal("1"),
        total_income=Decimal("1000"),
        market_cap=Decimal("1000"),
    )
    defaults.update(overrides)
    return Financials(symbol="ACME", **defaults)  # type: ignore[arg-type]


def test_clean_balance_sheet_passes() -> None:
    r = screen(_f())
    assert r.passed, r.failures


def test_debt_at_threshold_fails() -> None:
    # strict >= semantics: exactly 30% is a failure
    r = screen(_f(interest_bearing_debt=Decimal("300")))
    assert not r.passed
    assert any("interest-bearing debt" in f for f in r.failures)


def test_interest_cash_breach() -> None:
    r = screen(_f(interest_bearing_cash_and_investments=Decimal("400")))
    assert not r.passed
    assert any("interest-bearing cash" in f for f in r.failures)


def test_non_compliant_income_breach() -> None:
    r = screen(_f(non_compliant_income=Decimal("60"), total_income=Decimal("1000")))
    assert not r.passed
    assert any("non-compliant income" in f for f in r.failures)


def test_zero_market_cap_fails_closed() -> None:
    r = screen(_f(market_cap=Decimal("0")))
    assert not r.passed


def test_purification_rounds_up_to_piastre() -> None:
    # 5% of 100 EGP = 5.00 exactly, no rounding
    assert purification_amount(Decimal("100"), Decimal("5"), Decimal("100")) == Decimal("5.00")
    # Non-integer piastre must round UP (ceiling), never down
    assert purification_amount(Decimal("100"), Decimal("1"), Decimal("300")) == Decimal("0.34")


def test_purification_unknown_composition_purifies_everything() -> None:
    # total_income <= 0 but non_compliant_income > 0 => purify the whole dividend
    assert purification_amount(Decimal("50"), Decimal("1"), Decimal("0")) == Decimal("50")


def test_purification_zero_dividend() -> None:
    assert purification_amount(Decimal("0"), Decimal("1"), Decimal("100")) == Decimal("0")
