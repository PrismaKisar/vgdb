"""The archive of played games, and the rules a game has to satisfy to enter it.

One JSON file, but the file is an implementation detail: callers ask the
Archive to record a game and it decides what a game is. Both writers — the web
page and the cover scripts — come through here, so the rules hold whichever
one is running.
"""

import contextlib
import copy
import fcntl
import json
import os
import tempfile
from pathlib import Path

from vgdb import config, covers


class Invalid(ValueError):
    """A game that breaks the rules of the archive."""


class Unreadable(ValueError):
    """Bytes offered as a cover that are not an image we can open."""


class Ambiguous(LookupError):
    """A partial title that names more than one game."""

    def __init__(self, wanted: str, matches: list[str]):
        super().__init__(f"{wanted!r} matches {', '.join(matches)}")
        self.wanted = wanted
        self.matches = matches


def _same_title(one: str, other: str) -> bool:
    """The title identifies the game, ignoring case and surrounding spaces."""
    return one.strip().casefold() == other.strip().casefold()


def _game_named(games: list[dict], title: str) -> dict | None:
    """The game this title names, in a list already read from the archive."""
    return next((g for g in games if _same_title(g["title"], title)), None)


def _replace(games: list[dict], superseded: str, game: dict) -> None:
    """Put the game where the one it supersedes was, or at the end."""
    for i, existing in enumerate(games):
        if _same_title(existing["title"], superseded):
            games[i] = game
            break
    else:
        games.append(game)


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
            game["cover"] = self._carried_cover(superseded["cover"], title)

        self._replace(previous_title or title, game)
        return game

    def attach_cover(self, title: str, image: bytes) -> dict:
        """Give this game a cover, and return the game it now belongs to.

        The caller brings a title and the bytes of an image; the thumbnail,
        the file name and the folder it lands in are ours. Raises Unreadable
        if the bytes are not an image — nothing is written in that case, since
        the thumbnail is made before anything touches the disk. A failure of
        the disk itself is nobody's fault but ours and comes out as OSError.
        """
        game = self.find(title)
        if game is None:
            raise LookupError(f"{title} is not in the archive")

        try:
            thumbnail = covers.thumbnail(image)
        except OSError as unopenable:
            raise Unreadable(f"{title}: not a readable image") from unopenable

        folder = self.covers_directory
        folder.mkdir(parents=True, exist_ok=True)

        name = covers.name_for(game["title"])
        (folder / name).write_bytes(thumbnail)

        superseded = game.get("cover")
        game["cover"] = name
        self._replace(game["title"], game)

        # A renamed game keeps its old cover until a new one is attached; the
        # file it used to point at would otherwise stay behind for good.
        if superseded and superseded != name:
            (folder / superseded).unlink(missing_ok=True)
        return game

    def _carried_cover(self, filename: str, title: str) -> str:
        """The cover of a game that has just been renamed.

        The file name is derived from the title, so a rename would leave the
        artwork under the old one: orphaned, and free for a later game taking
        that title to claim or overwrite. The file follows the game instead.
        """
        wanted = covers.name_for(title)
        stored = self.covers_directory / filename
        if filename == wanted or not stored.exists():
            return filename
        os.replace(stored, self.covers_directory / wanted)
        return wanted

    def cover_size(self, title: str) -> int:
        """How many bytes the cover of this game takes on disk."""
        game = self.find(title)
        if game is None:
            raise LookupError(f"{title} is not in the archive")
        if not game.get("cover"):
            raise LookupError(f"{title} has no cover")
        return (self.covers_directory / game["cover"]).stat().st_size

    def remove(self, title: str) -> bool:
        """Take a game out of the archive. False if it was not there."""
        games = self.games()
        remaining = [g for g in games if not _same_title(g["title"], title)]
        if len(remaining) == len(games):
            return False
        self._write(remaining)
        return True

    def _replace(self, superseded: str, game: dict) -> None:
        games = self.games()
        for i, existing in enumerate(games):
            if _same_title(existing["title"], superseded):
                games[i] = game
                break
        else:
            games.append(game)
        self._write(games)

    @contextlib.contextmanager
    def _rewritten(self):
        """Read the archive, let the caller change it, write it back.

        The one way to change the archive, and the reason it is a private
        seam: a caller given the games and left to write them back would be
        reading and writing as two steps, and another writer landing between
        them loses its judgement with no error and no way to notice. So the
        whole read-modify-write happens under an exclusive lock and a second
        writer waits, rather than starting from games about to go stale. That
        covers everything coming through here — the page and the cover
        scripts; a text editor rewriting the file knows nothing of the lock.

        Nothing is written if the caller raises, or if it changed nothing. The
        lock is not re-entrant: one of these inside another deadlocks.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # A lock on the archive itself would not hold: every write replaces
        # the file, so the next writer would lock a different inode. The lock
        # lives in a file of its own, which is never replaced.
        with open(self._lock_path, "w") as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            games = self.games()
            unchanged = copy.deepcopy(games)
            yield games
            if games != unchanged:
                self._write(games)

    @property
    def _lock_path(self) -> Path:
        """Hidden: it is ours, and the owner's folder holds their data."""
        return self.path.with_name(f".{self.path.name}.lock")

    def _write(self, games: list[dict]) -> None:
        """Rewrite the archive.

        The write is atomic: if the process dies halfway through, the previous
        archive survives intact instead of being left truncated.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(games, ensure_ascii=False, indent=2) + "\n"

        fd, scratch = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(scratch, self.path)
        except BaseException:
            Path(scratch).unlink(missing_ok=True)
            raise
