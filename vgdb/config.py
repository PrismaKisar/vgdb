"""Everything vgdb reads from its surroundings.

Two settings, documented together in the README and now read in one place:
where the archive lives, and the SteamGridDB key the cover scripts want.
"""

import os
from pathlib import Path

DEFAULT_ARCHIVE = Path.home() / ".vgdb" / "games.json"
ENV_FILE = ".env"


def archive_path() -> Path:
    """Where the archive lives, always absolute.

    Outside the code repository on purpose: the ratings are personal and the
    repository is public. `vgdb` also runs from any directory, so a path
    relative to the working directory would silently produce empty archives.
    """
    chosen = os.environ.get("VGDB_FILE")
    return Path(chosen).expanduser().resolve() if chosen else DEFAULT_ARCHIVE


def steamgriddb_key() -> str | None:
    """The SteamGridDB key, or None — in which case Steam is the fallback.

    Read from the environment first, then from an untracked `.env` in the
    working directory, which is where the README says to run the scripts from.
    """
    if key := os.environ.get("VGDB_SGDB_KEY"):
        return key
    return _from_env_file("VGDB_SGDB_KEY")


def _from_env_file(wanted: str) -> str | None:
    env = Path(ENV_FILE)
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == wanted:
            return value.strip().strip("\"'") or None
    return None
