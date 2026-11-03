"""Refresh the EGX_SHARIAH universe snapshot from the EGX BFF.

Design rules the engine depends on:

- Append-only: a refresh never edits a past snapshot. If today's symbols differ
  from the latest snapshot, a NEW entry is appended. If they're identical,
  the file is left untouched (unless ``force=True`` is passed).
- Point-in-time integrity: ``effective_date`` is the observation date (today),
  not whatever the BFF believes the "review" date is.
- Default source for the ``source:`` field is the exact URL hit.

The YAML is edited line-by-line to preserve human comments. If the file is
empty or malformed, we bail — operators should intervene rather than lose
history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from pathlib import Path

from .sources import EgxBff
from .sources.http import HttpClient
from .universe import ShariaUniverse

DEFAULT_URL = (
    "https://beta.egx.com.eg/api/bff/egx"
    "/index-constituents?indexName=EGX_SHARIAH"
)


@dataclass(frozen=True, slots=True)
class RefreshResult:
    path: Path
    observed: date
    fetched_symbols: list[str]
    added: bool
    unchanged: bool
    yaml_patch: str
    reason: str


def default_universe_path() -> Path:
    """Resolve the path of the shipped YAML inside the installed package."""
    traversable = files("wazn_screen").joinpath("data/egx33.yaml")
    # importlib.resources returns a Traversable; .path or .joinpath doesn't
    # expose Path directly on namespace packages. The hatch build places this
    # file on disk, so this works for editable + wheel installs.
    with traversable.open("r", encoding="utf-8") as fh:
        fh.read()  # ensure it exists
    return Path(str(traversable))


def refresh_universe(
    *,
    path: Path | str | None = None,
    http: HttpClient | None = None,
    on: date | None = None,
    source: str | None = None,
    force: bool = False,
) -> RefreshResult:
    """Fetch EGX_SHARIAH from the BFF and build a new snapshot block.

    Returns a :class:`RefreshResult`. The caller decides whether to persist
    (via :func:`write_patch`) — this keeps the fetch pure for tests.
    """
    yaml_path = Path(path) if path else default_universe_path()
    on = on or date.today()
    bff = EgxBff(http=http)
    symbols = bff.shariah_symbols()
    if not symbols:
        raise RuntimeError(
            "EGX BFF returned no EGX_SHARIAH constituents; refusing to write an empty snapshot"
        )
    text = yaml_path.read_text(encoding="utf-8") if yaml_path.exists() else ""
    universe = ShariaUniverse.from_yaml(yaml_path) if text.strip() else ShariaUniverse(snapshots=[])
    latest = universe.snapshots[-1] if universe.snapshots else None
    same_as_latest = latest is not None and latest.symbols == frozenset(symbols)
    if same_as_latest and not force:
        return RefreshResult(
            path=yaml_path,
            observed=on,
            fetched_symbols=symbols,
            added=False,
            unchanged=True,
            yaml_patch="",
            reason=f"symbols identical to snapshot {latest.effective_date}; no change",
        )
    patch = _build_snapshot_block(
        on=on, symbols=symbols, source=source or f"{DEFAULT_URL} (observed {on})"
    )
    return RefreshResult(
        path=yaml_path,
        observed=on,
        fetched_symbols=symbols,
        added=True,
        unchanged=False,
        yaml_patch=patch,
        reason=(
            "new snapshot: no prior data" if latest is None
            else f"symbols differ from snapshot {latest.effective_date}"
        ),
    )


def write_patch(result: RefreshResult) -> None:
    """Append ``result.yaml_patch`` under the ``snapshots:`` list in-place.

    If the file has no ``snapshots:`` key yet, we bail — the YAML is expected
    to already have the preamble (``max_age_days``, ``allowed_security_classes``).
    """
    if not result.yaml_patch:
        return
    text = result.path.read_text(encoding="utf-8")
    if "\nsnapshots:" not in text and not text.lstrip().startswith("snapshots:"):
        raise RuntimeError(
            f"{result.path} has no 'snapshots:' section; initialise it before refreshing"
        )
    # Append to end — YAML list continues at the same indent, so adding another
    # top-level ``- effective_date: ...`` block works as long as the file ends
    # on a newline. Normalise trailing whitespace first.
    if not text.endswith("\n"):
        text += "\n"
    text += result.yaml_patch
    result.path.write_text(text, encoding="utf-8")


def _build_snapshot_block(*, on: date, symbols: list[str], source: str) -> str:
    """Emit a YAML snapshot block that fits the hand-written preamble style."""
    lines: list[str] = []
    # JSON strings are valid YAML double-quoted scalars; avoids PyYAML's
    # ``...`` document-end marker contaminating the appended block.
    lines.append(f"  - effective_date: {on.isoformat()}")
    lines.append(f"    source: {json.dumps(source, ensure_ascii=False)}")
    lines.append("    symbols:")
    for s in sorted(symbols):
        lines.append(f"      - {s}")
    lines.append("")  # trailing newline for cleanliness
    return "\n".join(lines)
