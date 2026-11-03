from datetime import date, timedelta

import pytest

from wazn_screen import load_default_universe
from wazn_screen.universe import ShariaUniverse, UniverseSnapshot


def test_bundled_snapshot_has_members() -> None:
    u = load_default_universe()
    members = u.members_on(date(2026, 11, 3))
    assert "ETEL" in members
    assert "ADIB" in members
    assert len(members) >= 30


def test_known_member_allowed() -> None:
    u = load_default_universe()
    d = u.can_buy("ETEL", "LocalSecurity_IN", date(2026, 11, 3))
    assert d.allowed, d.reasons


def test_non_member_denied() -> None:
    u = load_default_universe()
    d = u.can_buy("ZZZZ", "LocalSecurity_IN", date(2026, 11, 3))
    assert not d.allowed
    assert any("not an EGX33 constituent" in r for r in d.reasons)


def test_banned_security_class_denied_even_if_member() -> None:
    u = load_default_universe()
    d = u.can_buy("ETEL", "Tbills", date(2026, 11, 3))
    assert not d.allowed
    assert any("banned" in r for r in d.reasons)


def test_unknown_security_class_denied() -> None:
    u = load_default_universe()
    d = u.can_buy("ETEL", None, date(2026, 11, 3))
    assert not d.allowed
    assert any("unknown security class" in r for r in d.reasons)


def test_sell_is_never_blocked_by_this_layer() -> None:
    # can_buy models BUY only; the universe never gates SELL (asymmetric by design).
    # This is a contract test — the module exposes no "can_sell", on purpose.
    u = load_default_universe()
    assert not hasattr(u, "can_sell")


def test_stale_snapshot_blocks() -> None:
    u = load_default_universe()
    snap_date = u.snapshots[-1].effective_date
    d = u.can_buy(
        "ETEL",
        "LocalSecurity_IN",
        snap_date + timedelta(days=u.max_age_days + 1),
    )
    assert not d.allowed
    assert any("snapshot from" in r and "days old" in r for r in d.reasons)


def test_empty_universe_fails_closed() -> None:
    u = ShariaUniverse(snapshots=[])
    d = u.can_buy("ETEL", "LocalSecurity_IN", date(2026, 11, 3))
    assert not d.allowed


def test_banned_cannot_be_whitelisted() -> None:
    with pytest.raises(ValueError):
        ShariaUniverse(
            snapshots=[UniverseSnapshot(date(2026, 1, 1), frozenset({"X"}), "test")],
            allowed_security_classes=frozenset({"Tbills"}),
        )


def test_watchlist_blocks_buy() -> None:
    u = ShariaUniverse(
        snapshots=[UniverseSnapshot(date(2026, 11, 1), frozenset({"ETEL"}), "test")],
        watchlist_no_buy=frozenset({"ETEL"}),
    )
    d = u.can_buy("ETEL", "LocalSecurity_IN", date(2026, 11, 3))
    assert not d.allowed
    assert any("watchlist" in r for r in d.reasons)
