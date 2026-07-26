"""The archive of played games, and the rules a game has to satisfy to enter it.

One JSON file, but the file is an implementation detail: callers ask the
Archive to record a game and it decides what a game is. Both writers — the web
page and the cover scripts — come through here, so the rules hold whichever
one is running.
"""

import json
from pathlib import Path

from vgdb import config, covers


class Invalid(ValueError):
    """A game that breaks the rules of the archive."""


class Ambiguous(LookupError):
    """A partial title that names more than one game."""

    def __init__(self, wanted: str, matches: list[str]):
        super().__init__(f"{wanted!r} matches {', '.join(matches)}")
        self.wanted = wanted
        self.matches = matches


def _same_title(one: str, other: str) -> bool:
    """The title identifies the game, ignoring case and surrounding spaces."""
    return one.strip().casefold() == other.strip().casefold()


class Archive:
    """The games played and the judgements passed on them."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path).expanduser() if path is not None else config.archive_path()

    @property
    def covers_directory(self) -> Path:
        return covers.directory(self.path)

    def games(self) -> list[dict]:
        """Every archived game, or nothing if there is no archive yet."""
        if not self.path.exists():
            return []
        # An empty archive (first run, or an interrupted write) must not leave
        # the page blank.
        text = self.path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else []

    def find(self, title: str) -> dict | None:
        """The game with exactly this title, or None."""
        return next((g for g in self.games() if _same_title(g["title"], title)), None)
