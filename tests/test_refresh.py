from datetime import date
from pathlib import Path

import httpx
import pytest

from wazn_screen.refresh import refresh_universe, write_patch
from wazn_screen.sources.http import HttpClient
from wazn_screen.universe import ShariaUniverse

SEED_YAML = """\
max_age_days: 200

allowed_security_classes:
  - LocalSecurity_IN

watchlist_no_buy: []

snapshots:
  - effective_date: 2026-11-03
    source: "seed"
    symbols:
      - ETEL
      - ADIB
"""


def _bff_returning(symbols: list[str]):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": {"constituents": [{"symbol": s} for s in symbols]}},
        )

    return HttpClient(transport=httpx.MockTransport(handler))


def _write(tmp_path: Path) -> Path:
    p = tmp_path / "universe.yaml"
    p.write_text(SEED_YAML, encoding="utf-8")
    return p


def test_refresh_identical_is_unchanged(tmp_path: Path):
    p = _write(tmp_path)
    r = refresh_universe(
        path=p, http=_bff_returning(["ETEL", "ADIB"]), on=date(2026, 11, 10)
    )
    assert r.unchanged
    assert not r.added
    assert r.yaml_patch == ""


def test_refresh_different_builds_patch_without_writing(tmp_path: Path):
    p = _write(tmp_path)
    before = p.read_text()
    r = refresh_universe(
        path=p,
        http=_bff_returning(["ETEL", "ADIB", "ORAS"]),
        on=date(2026, 11, 10),
    )
    assert r.added
    assert "ORAS" in r.yaml_patch
    assert "effective_date: 2026-11-10" in r.yaml_patch
    # Dry-run — file is unchanged until write_patch is called.
    assert p.read_text() == before


def test_refresh_write_appends_and_preserves_history(tmp_path: Path):
    p = _write(tmp_path)
    r = refresh_universe(
        path=p,
        http=_bff_returning(["ETEL", "ADIB", "ORAS"]),
        on=date(2026, 11, 10),
        source="unit-test",
    )
    write_patch(r)
    u = ShariaUniverse.from_yaml(p)
    assert len(u.snapshots) == 2
    assert u.snapshots[0].effective_date == date(2026, 11, 3)
    assert u.snapshots[1].effective_date == date(2026, 11, 10)
    assert "ORAS" in u.snapshots[1].symbols
    # Old snapshot was NOT modified.
    assert u.snapshots[0].symbols == frozenset({"ETEL", "ADIB"})


def test_refresh_force_appends_even_if_identical(tmp_path: Path):
    p = _write(tmp_path)
    r = refresh_universe(
        path=p,
        http=_bff_returning(["ETEL", "ADIB"]),
        on=date(2026, 11, 10),
        force=True,
    )
    assert r.added
    assert r.yaml_patch


def test_refresh_bff_empty_raises(tmp_path: Path):
    p = _write(tmp_path)
    with pytest.raises(RuntimeError, match="refusing to write an empty snapshot"):
        refresh_universe(path=p, http=_bff_returning([]), on=date(2026, 11, 10))
