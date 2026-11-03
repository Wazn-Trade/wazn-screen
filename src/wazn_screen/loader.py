"""Load the bundled EGX33 universe snapshot shipped with the package."""

from __future__ import annotations

from importlib.resources import files

from .universe import ShariaUniverse

DEFAULT_UNIVERSE_YAML = "wazn_screen/data/egx33.yaml"


def load_default_universe() -> ShariaUniverse:
    """Return the ShariaUniverse built from the bundled snapshot file."""
    data_file = files("wazn_screen").joinpath("data/egx33.yaml")
    with data_file.open("r", encoding="utf-8") as fh:
        import yaml

        raw = yaml.safe_load(fh.read()) or {}
    from .universe import DEFAULT_ALLOWED_SECURITY_CLASSES, UniverseSnapshot, _as_date, _normalise

    snapshots = [
        UniverseSnapshot(
            effective_date=_as_date(s["effective_date"]),
            symbols=frozenset(_normalise(s.get("symbols") or [])),
            source=str(s.get("source", "")),
            review_effective_date=(
                _as_date(s["review_effective_date"]) if s.get("review_effective_date") else None
            ),
        )
        for s in raw.get("snapshots") or []
    ]
    return ShariaUniverse(
        snapshots=snapshots,
        max_age_days=int(raw.get("max_age_days", 200)),
        allowed_security_classes=frozenset(
            raw.get("allowed_security_classes") or DEFAULT_ALLOWED_SECURITY_CLASSES
        ),
        watchlist_no_buy=frozenset(_normalise(raw.get("watchlist_no_buy") or [])),
    )
