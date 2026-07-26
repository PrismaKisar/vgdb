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


def _checked_rating(rating) -> int | float:
    """A rating is how much the game was enjoyed: 1 to 10, half points allowed."""
    # bool is an int in Python, and True would otherwise pass as a rating of 1.
    numeric = not isinstance(rating, bool) and isinstance(rating, (int, float))
    if not numeric or not 1 <= rating <= 10:
        raise Invalid("The rating must be a number from 1 to 10")
    return rating


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

    def resolve(self, title: str) -> dict | None:
        """The game this title refers to, allowing a unique partial match.

        For the cover scripts, where typing "Clair Obscur: Expedition 33" in
        full at a shell prompt is a nuisance. Raises Ambiguous rather than
        picking one, since attaching artwork to the wrong game is silent.
        """
        if found := self.find(title):
            return found

        needle = title.strip().casefold()
        partial = [g for g in self.games() if needle in g["title"].casefold()]
        if len(partial) > 1:
            raise Ambiguous(title, [g["title"] for g in partial])
        return partial[0] if partial else None

    def record(
        self,
        title: str,
        rating,
        notes: str | None = None,
        platinum: bool | None = None,
        previous_title: str | None = None,
    ) -> dict:
        """Add a game to the archive, or recalibrate the one it supersedes.

        `previous_title` covers renaming: the entry keeps its position in the
        archive instead of being deleted and re-appended at the end.
        """
        title = title.strip()
        if not title:
            raise Invalid("The title cannot be empty")

        game = {"title": title, "rating": _checked_rating(rating)}
        # Stored as sent, not tidied: normalising the notes is a change to what
        # the owner wrote, and the page already trims before it gets here.
        if notes:
            game["notes"] = notes
        # Three states, not two: "not won" and "there is no platinum" are
        # different facts, and only the second one means absent.
        if isinstance(platinum, bool):
            game["platinum"] = platinum

        # The cover is attached by its own operation, so recalibrating a rating
        # or fixing a typo in the title must not drop it.
        superseded = self.find(previous_title or title)
        if superseded and superseded.get("cover"):
            game["cover"] = superseded["cover"]

        self._replace(previous_title or title, game)
        return game
