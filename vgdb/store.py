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
