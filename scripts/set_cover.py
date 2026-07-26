"""Set the cover of one or more games by hand.

Accepts a SteamGridDB grid link, a bare grid id, or any direct image URL —
for when the automatic pick from fetch_covers.py is not the artwork you want.

    uv run scripts/set_cover.py "Clair Obscur: Expedition 33" https://www.steamgriddb.com/grid/801236
    uv run scripts/set_cover.py "Cuphead" 801236 "Hollow Knight" https://example.com/art.png

Titles are matched the way the archive matches them: case-insensitively, and
a unique partial match is enough ("Expedition" finds the full title).
"""

import re


def looks_like_reference(argument: str) -> bool:
    """A grid link, a bare grid id, or an image URL — as opposed to a title."""
    argument = argument.strip()
    return bool(re.fullmatch(r"\d+", argument)) or argument.startswith("http")


def resolve(games: list[dict], wanted: str) -> dict | None:
    """The single game this title refers to, or None if it is not unambiguous."""
    needle = wanted.strip().casefold()
    exact = [g for g in games if g["title"].casefold() == needle]
    if exact:
        return exact[0]

    partial = [g for g in games if needle in g["title"].casefold()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        print(f"  !  '{wanted}' è ambiguo: {', '.join(g['title'] for g in partial)}")
    return None
