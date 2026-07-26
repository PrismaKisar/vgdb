"""One-shot helper: pull missing covers from SteamGridDB, falling back to Steam.

SteamGridDB is preferred: it has square artwork and it indexes console
exclusives that Steam simply does not list. It needs a free API key
(steamgriddb.com -> Preferences -> API), read from VGDB_SGDB_KEY in the
environment or from the untracked .env file at the project root.

    uv run scripts/fetch_covers.py            # only games without a cover
    uv run scripts/fetch_covers.py --force    # refetch everything
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
from difflib import SequenceMatcher

import sgdb
from sgdb import fetch

from vgdb import covers, store

STEAM_SEARCH = "https://store.steampowered.com/api/storesearch/?term={}&l=english&cc=us"
STEAM_CAPSULE = "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/library_600x900.jpg"
STEAM_HEADER = "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/header.jpg"
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


def from_steam(title: str) -> tuple[bytes, str] | None:
    """Poster artwork from Steam's keyless store API.

    The fallback when there is no SteamGridDB key: no authentication needed,
    but the art is 2:3 and console exclusives are simply absent.
    """
    term = searchable(title)
    items = json.loads(
        fetch(STEAM_SEARCH.format(urllib.parse.quote(term)))
    ).get("items", [])
    if not items:
        return None

    app = max(items, key=lambda i: closeness(term, i["name"]))
    if closeness(term, app["name"]) < CONFIDENT:
        return None

    try:
        art = fetch(STEAM_CAPSULE.format(app["id"]))
    except Exception:
        art = fetch(STEAM_HEADER.format(app["id"]))
    return art, f"{app['name']} [steam {app['id']}]"


def artwork_for(title: str, key: str | None) -> tuple[bytes, str] | None:
    """The best artwork available for this title, or None if unresolved."""
    sources = ([lambda: from_steamgriddb(title, key)] if key else []) + [
        lambda: from_steam(title)
    ]
    for source in sources:
        try:
            if found := source():
                return found
        except Exception as error:
            print(f"  !  {title}: {error}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="refetch existing covers")
    args = parser.parse_args()

    key = sgdb.api_key()
    print("Fonte: SteamGridDB" if key else "Fonte: Steam (nessuna chiave in .env)")

    archive = store.archive_path()
    games = store.load(archive)
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
            game["cover"] = covers.store_for(archive, title, art)
        except Exception as error:
            print(f"  !  {title}: immagine illeggibile ({error})")
            missing.append(title)
            continue

        size = (covers.directory(archive) / game["cover"]).stat().st_size
        print(f"  ok {title}  <-  {source}, {size // 1024} KB")
        time.sleep(0.3)

    store.save(archive, games)

    print(f"\n{len(games) - len(missing)}/{len(games)} copertine presenti.")
    if missing:
        print("Da aggiungere a mano trascinandole nella pagina:")
        for title in missing:
            print(f"  - {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
