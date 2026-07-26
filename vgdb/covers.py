"""Cover thumbnails: small WebP files stored next to the archive."""

import io
import re
from pathlib import Path

from PIL import Image

DIRNAME = "covers"
SIZE = 192
SUFFIX = ".webp"


def directory(archive: Path) -> Path:
    """Where the covers for this archive live."""
    return Path(archive).parent / DIRNAME


def name_for(title: str) -> str:
    """A filesystem-safe cover name derived from the game title."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{slug or 'cover'}{SUFFIX}"


def thumbnail(data: bytes) -> bytes:
    """A small WebP, at most SIZE on its longest side.

    The aspect ratio is kept: cropping to a square would cut the title off
    the top and bottom of a 2:3 store poster. Covers are shown around 48px,
    so anything larger is bytes committed to the repository for no visible
    gain — a store poster drops from ~90 KB to ~5 KB.
    """
    with Image.open(io.BytesIO(data)) as source:
        image = source.convert("RGB")
        image.thumbnail((SIZE, SIZE), Image.LANCZOS)

        out = io.BytesIO()
        image.save(out, format="WEBP", quality=80, method=6)
        return out.getvalue()


def store_for(archive: Path, title: str, data: bytes) -> str:
    """Save a cover for this game and return its filename."""
    folder = directory(archive)
    folder.mkdir(parents=True, exist_ok=True)
    name = name_for(title)
    (folder / name).write_bytes(thumbnail(data))
    return name
