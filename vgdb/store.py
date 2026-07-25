"""Reading the game archive (a single JSON file)."""

import json
import os
from pathlib import Path

DEFAULT_ARCHIVE = Path.home() / "Documents" / "videogame" / "games.json"


def archive_path() -> Path:
    """The archive location, always absolute.

    `vgdb` runs from any directory, so a path relative to the working
    directory would silently produce empty archives.
    """
    chosen = os.environ.get("VGDB_FILE")
    return Path(chosen).expanduser().resolve() if chosen else DEFAULT_ARCHIVE


def load(path: Path) -> list[dict]:
    """The archived games, or an empty list if there is no archive yet."""
    if not Path(path).exists():
        return []
    # An empty archive (first run, or an interrupted write) must not leave
    # the page blank.
    text = Path(path).read_text(encoding="utf-8").strip()
    return json.loads(text) if text else []
