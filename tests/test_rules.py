from decimal import Decimal

from wazn_screen.rules import (
    check_fx_transaction,
    check_metals_transaction,
    classify_sukuk,
    nisab_value,
)


# FX
def test_fx_spot_ok():
    d = check_fx_transaction(kind="spot")
    assert d.allowed


def test_fx_forward_blocked():
    d = check_fx_transaction(kind="forward")
    assert not d.allowed
    assert any("not Sharia-permissible" in r for r in d.reasons)


def test_fx_margin_blocked_even_if_spot():
    d = check_fx_transaction(kind="spot", uses_margin=True)
    assert not d.allowed


def test_fx_deferred_spot_blocked():
    d = check_fx_transaction(kind="spot", settlement_days=5)
    assert not d.allowed
    assert any("forward" in r for r in d.reasons)


# Metals
def test_metals_physical_same_session_ok():
    d = check_metals_transaction(metal="gold", form="physical", settlement_days=0)
    assert d.allowed


def test_metals_etf_leveraged_blocked():
    d = check_metals_transaction(metal="gold", form="etf_leveraged")
    assert not d.allowed


def test_metals_deferral_blocked():
    d = check_metals_transaction(metal="silver", form="allocated", settlement_days=1)
    assert not d.allowed


def test_metals_margin_blocked():
    d = check_metals_transaction(metal="gold", form="physical", uses_margin=True)
    assert not d.allowed


def test_metals_non_monetary_metal_informs():
    d = check_metals_transaction(metal="copper", form="physical")
    assert not d.allowed
    assert any("monetary metal" in r for r in d.reasons)


# Sukuk
def test_sukuk_ijara_allowed_needs_fatwa_review():
    d = classify_sukuk(structure="ijara")
    assert d.allowed
    assert d.needs_fatwa_review


def test_sukuk_murabaha_tradable_blocked():
    d = classify_sukuk(structure="murabaha", tradable_after_delivery=True)
    assert not d.allowed


def test_sukuk_murabaha_held_to_maturity_allowed():
    d = classify_sukuk(structure="murabaha", tradable_after_delivery=False)
    assert d.allowed


def test_sukuk_conventional_bond_blocked():
    assert not classify_sukuk(structure="conventional_bond").allowed


def test_sukuk_unknown_structure_fail_closed():
    assert not classify_sukuk(structure="exotic_thing").allowed


# Zakat
def test_zakat_below_nisab_nothing_due():
    r = nisab_value(
        wealth=Decimal("1000"),
        gold_price_per_gram=Decimal("4500"),
        silver_price_per_gram=Decimal("55"),
    )
    # silver nisab = 595 * 55 = 32,725 — far above 1000
    assert not r.is_zakat_due
    assert r.due_amount == Decimal(0)


def test_zakat_above_nisab_rate_is_2_5_percent():
    r = nisab_value(
        wealth=Decimal("100000"),
        gold_price_per_gram=Decimal("4500"),
        silver_price_per_gram=Decimal("55"),
    )
    assert r.is_zakat_due
    assert r.due_amount == Decimal("2500.00")


def test_zakat_prefer_gold_uses_gold_threshold():
    r = nisab_value(
        wealth=Decimal("100000"),
        gold_price_per_gram=Decimal("4500"),
        silver_price_per_gram=Decimal("55"),
        prefer="gold",
    )
    # gold nisab = 85 * 4500 = 382,500 — above 100000, so NOT due by gold threshold
    assert not r.is_zakat_due
    assert r.chosen_metal == "gold"
