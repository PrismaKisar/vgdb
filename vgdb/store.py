"""Reading and writing the game archive (a single JSON file)."""

import json
import os
import tempfile
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


def save(path: Path, games: list[dict]) -> None:
    """Rewrite the archive.

    The write is atomic: if the process dies halfway through, the previous
    archive survives intact instead of being left truncated.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(games, ensure_ascii=False, indent=2) + "\n"

    fd, scratch = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(scratch, path)
    except BaseException:
        Path(scratch).unlink(missing_ok=True)
        raise


def _same_title(one: str, other: str) -> bool:
    """The title identifies the game, ignoring case and surrounding spaces."""
    return one.strip().casefold() == other.strip().casefold()


def find(path: Path, title: str) -> dict | None:
    """The archived game with this title, or None."""
    return next((g for g in load(path) if _same_title(g["title"], title)), None)


def upsert(path: Path, game: dict, previous_title: str | None = None) -> None:
    """Add a game to the archive, replacing the one it supersedes.

    `previous_title` covers renaming: the entry keeps its position in the
    archive instead of being deleted and re-appended at the end.
    """
    games = load(path)
    replaces = previous_title or game["title"]
    for i, existing in enumerate(games):
        if _same_title(existing["title"], replaces):
            games[i] = game
            break
    else:
        games.append(game)
    save(path, games)


def delete(path: Path, title: str) -> bool:
    """Remove a game from the archive. False if it was not there."""
    games = load(path)
    remaining = [g for g in games if not _same_title(g["title"], title)]
    if len(remaining) == len(games):
        return False
    save(path, remaining)
    return True
