"""One-shot helper: pull missing covers from SteamGridDB, falling back to Steam.

SteamGridDB is preferred: it has square artwork and it indexes console
exclusives that Steam simply does not list. It needs a free API key
(steamgriddb.com -> Preferences -> API), read from VGDB_SGDB_KEY in the
environment or from the untracked .env file at the project root.

    uv run scripts/fetch_covers.py            # only games without a cover
    uv run scripts/fetch_covers.py --force    # refetch everything
"""

import re
import urllib.parse
from difflib import SequenceMatcher

import sgdb
from sgdb import fetch

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
