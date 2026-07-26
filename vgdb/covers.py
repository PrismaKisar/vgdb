"""Cover thumbnails: small WebP files stored next to the archive.

Implementation of one Archive operation, not an interface of its own: only
`Archive.attach_cover` calls in here.
"""

import hashlib
import io
import re
from pathlib import Path

from PIL import Image

DIRNAME = "covers"
SIZE = 192
SUFFIX = ".webp"
FINGERPRINT = 6


def directory(archive: Path) -> Path:
    """Where the covers for this archive live."""
    return Path(archive).parent / DIRNAME


def name_for(title: str) -> str:
    """A filesystem-safe cover name, unique to the game it belongs to.

    The readable part comes from the title, for anyone browsing the folder.
    The fingerprint is what makes it a name: two titles that reduce to the
    same slug ("Hollow Knight" and "Hollow: Knight!") would otherwise
    overwrite each other's artwork. It is taken over the title as the archive
    identifies it, so a change of case alone is not a different game.
    """
    identity = title.strip().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", identity).strip("-") or "cover"
    fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:FINGERPRINT]
    return f"{slug}-{fingerprint}{SUFFIX}"


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
