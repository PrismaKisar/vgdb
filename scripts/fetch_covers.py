"""One-shot helper: pull missing covers from SteamGridDB.

SteamGridDB is the only source: square artwork, and it indexes console
exclusives that storefronts like Steam do not list. It needs a free API key
(steamgriddb.com -> Preferences -> API), read from VGDB_SGDB_KEY in the
environment or from the untracked .env file at the project root.

    uv run scripts/fetch_covers.py            # only games without a cover
    uv run scripts/fetch_covers.py --force    # refetch everything
"""

import argparse
import re
import sys
import time
import urllib.parse
from difflib import SequenceMatcher

import sgdb
from sgdb import fetch

from vgdb import config
from vgdb.archive import Archive

CONFIDENT = 0.75

# Titles the archive records differently from the storefronts.
ALIASES = {
    "Uncharted 4: A Thief's End": "UNCHARTED: Legacy of Thieves Collection",
    "Spyro the Dragon (Reignited)": "Spyro Reignited Trilogy",
    "Spyro 2: Ripto's Rage! (Reignited)": "Spyro Reignited Trilogy",
    "Spyro: Year of the Dragon (Reignited)": "Spyro Reignited Trilogy",
    "Crash Bandicoot (N. Sane Trilogy)": "Crash Bandicoot N. Sane Trilogy",
    "Crash Bandicoot 2: Cortex Strikes Back (N. Sane Trilogy)": "Crash Bandicoot N. Sane Trilogy",
    "FIFA (la serie, tutti insieme)": "EA SPORTS FC 25",
}


def searchable(title: str) -> str:
    """Storefronts do not know about our parenthetical edition notes."""
    return ALIASES.get(title) or re.sub(r"\s*\([^)]*\)", "", title).strip()


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def closeness(term: str, name: str) -> float:
    """How confidently a storefront listing matches what we asked for."""
    return SequenceMatcher(None, normalise(term), normalise(name)).ratio()


def from_steamgriddb(title: str, key: str) -> tuple[bytes, str] | None:
    """Square artwork, if SteamGridDB knows this game."""
    term = searchable(title)
    found = sgdb.get(
        f"/search/autocomplete/{urllib.parse.quote(term)}", key
    ).get("data", [])
    if not found:
        return None

    game = max(found, key=lambda g: closeness(term, g["name"]))
    # A weak match must be reported as unresolved rather than silently
    # attaching the artwork of a different game.
    if closeness(term, game["name"]) < CONFIDENT:
        return None

    # 1:1 only; SteamGridDB also serves 2:3 and 92:43, which we do not want.
    grids = sgdb.get(
        f"/grids/game/{game['id']}?dimensions=512x512,1024x1024", key
    ).get("data", [])
    if not grids:
        return None

    return fetch(grids[0]["url"]), f"{game['name']} [sgdb {game['id']}]"


def artwork_for(title: str, key: str) -> tuple[bytes, str] | None:
    """The best artwork available for this title, or None if unresolved."""
    try:
        return from_steamgriddb(title, key)
    except Exception as error:
        print(f"  !  {title}: {error}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="refetch existing covers")
    args = parser.parse_args()

    key = config.steamgriddb_key()
    if not key:
        print("Serve una chiave SteamGridDB: VGDB_SGDB_KEY nell'ambiente o in .env")
        return 2

    archive = Archive()
    games = archive.games()
    missing = []

    for game in games:
        title = game["title"]
        if game.get("cover") and not args.force:
            continue

        found = artwork_for(title, key)
        if found is None:
            print(f"  -  {title}: nessuna copertina trovata")
            missing.append(title)
            continue

        art, source = found
        try:
            # Recorded one at a time: a network failure halfway through keeps
            # everything fetched so far instead of discarding the run.
            archive.attach_cover(title, art)
        except Exception as error:
            print(f"  !  {title}: immagine illeggibile ({error})")
            missing.append(title)
            continue

        print(f"  ok {title}  <-  {source}, {archive.cover_size(title) // 1024} KB")
        time.sleep(0.3)

    print(f"\n{len(games) - len(missing)}/{len(games)} copertine presenti.")
    if missing:
        print("Da aggiungere a mano trascinandole nella pagina:")
        for title in missing:
            print(f"  - {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
