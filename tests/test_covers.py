import io

from PIL import Image

from vgdb import covers


def image_bytes(width, height, colour="teal"):
    out = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(out, format="PNG")
    return out.getvalue()


def test_the_cover_name_comes_from_the_title():
    assert covers.name_for("Hollow Knight: Silksong") == "hollow-knight-silksong.webp"


def test_a_title_without_usable_characters_still_gets_a_name():
    assert covers.name_for("!!!") == "cover.webp"


def test_a_large_image_is_shrunk_to_a_few_kilobytes(tmp_path):
    archive = tmp_path / "games.json"

    name = covers.store_for(archive, "Celeste", image_bytes(2000, 2000))

    saved = covers.directory(archive) / name
    assert saved.stat().st_size < 20_000


def test_a_poster_keeps_its_shape(tmp_path):
    """Cropping to a square would cut the title off a 2:3 store poster."""
    archive = tmp_path / "games.json"

    name = covers.store_for(archive, "Celeste", image_bytes(600, 900))

    with Image.open(covers.directory(archive) / name) as thumb:
        assert thumb.size == (128, 192)


def test_covers_sit_next_to_the_archive(tmp_path):
    archive = tmp_path / "games.json"

    assert covers.directory(archive) == tmp_path / "covers"
