"""Shared SteamGridDB access for the cover scripts."""

import json
import os
import re
import urllib.request
from pathlib import Path

API = "https://www.steamgriddb.com/api/v2"
PROJECT = Path(__file__).resolve().parent.parent


def api_key() -> str | None:
    """The SteamGridDB key, from the environment or the gitignored .env file."""
    if key := os.environ.get("VGDB_SGDB_KEY"):
        return key

    env = PROJECT / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "VGDB_SGDB_KEY":
            return value.strip().strip("\"'") or None
    return None


def fetch(url: str, key: str | None = None, timeout: int = 25) -> bytes:
    headers = {"User-Agent": "vgdb/0.1"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get(path: str, key: str) -> dict:
    return json.loads(fetch(f"{API}{path}", key))


GRID = re.compile(r"(?:https?://www\.steamgriddb\.com/grid/)?(\d+)")


def artwork_from(reference: str, key: str) -> bytes:
    """The image behind a SteamGridDB grid link, a grid id, or a plain URL.

    A grid page (steamgriddb.com/grid/801236) is not an image, so its id has
    to be resolved through the API before anything can be downloaded.
    """
    if match := GRID.fullmatch(reference.strip()):
        return fetch(get(f"/grids/{match.group(1)}", key)["data"]["url"])
    return fetch(reference)
