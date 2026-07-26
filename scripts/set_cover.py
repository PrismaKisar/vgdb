"""Set the cover of one or more games by hand.

Accepts a SteamGridDB grid link, a bare grid id, or any direct image URL —
for when the automatic pick from fetch_covers.py is not the artwork you want.

    uv run scripts/set_cover.py "Clair Obscur: Expedition 33" https://www.steamgriddb.com/grid/801236
    uv run scripts/set_cover.py "Cuphead" 801236 "Hollow Knight" https://example.com/art.png

Titles are matched the way the archive matches them: case-insensitively, and
a unique partial match is enough ("Expedition" finds the full title).
"""

import re
import sys

import sgdb

from vgdb import config, covers
from vgdb.archive import Ambiguous, Archive


def looks_like_reference(argument: str) -> bool:
    """A grid link, a bare grid id, or an image URL — as opposed to a title."""
    argument = argument.strip()
    return bool(re.fullmatch(r"\d+", argument)) or argument.startswith("http")


def main(argv: list[str]) -> int:
    if not argv or len(argv) % 2:
        print(__doc__)
        return 2

    key = config.steamgriddb_key()
    archive = Archive()
    failed = 0

    for pair in zip(argv[::2], argv[1::2]):
        # Either order: whichever half looks like a link or an id is the artwork.
        reference, wanted = sorted(pair, key=looks_like_reference, reverse=True)

        try:
            game = archive.resolve(wanted)
        except Ambiguous as unclear:
            print(f"  !  '{wanted}' è ambiguo: {', '.join(unclear.matches)}")
            failed += 1
            continue
        if game is None:
            print(f"  -  '{wanted}' non è in archivio")
            failed += 1
            continue

        try:
            art = sgdb.artwork_from(reference, key)
            name = covers.store_for(archive.path, game["title"], art)
            archive.set_cover(game["title"], name)
        except Exception as error:
            print(f"  !  {game['title']}: {error}")
            failed += 1
            continue

        size = (archive.covers_directory / name).stat().st_size
        print(f"  ok {game['title']}  <-  {reference}, {size // 1024} KB")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
