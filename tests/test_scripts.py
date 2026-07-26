"""The cover scripts. Where the SteamGridDB key comes from is in test_config.py,
and how a title resolves to a game is in test_archive.py."""

import io
import sys

import pytest
from PIL import Image

import fetch_covers
import set_cover
import sgdb
from vgdb.archive import Archive


def png_bytes():
    out = io.BytesIO()
    Image.new("RGB", (600, 900), "teal").save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def archive(tmp_path, monkeypatch):
    """An archive the scripts will find, since they place themselves."""
    monkeypatch.setenv("VGDB_FILE", str(tmp_path / "games.json"))
    monkeypatch.setenv("VGDB_SGDB_KEY", "pretend-key")
    written = Archive(tmp_path / "games.json")
    written.record("Clair Obscur: Expedition 33", rating=10)
    written.record("Celeste", rating=8)
    return written


def test_a_grid_page_is_resolved_through_the_api(monkeypatch):
    """A grid page is HTML, so its id has to become an image URL first."""
    monkeypatch.setattr(sgdb, "get", lambda path, key: {"data": {"url": "cdn/art.png"}})
    monkeypatch.setattr(sgdb, "fetch", lambda url, key=None: f"downloaded {url}".encode())

    assert sgdb.artwork_from("https://www.steamgriddb.com/grid/801236", "k") == b"downloaded cdn/art.png"


def test_a_bare_grid_id_is_resolved_too(monkeypatch):
    monkeypatch.setattr(sgdb, "get", lambda path, key: {"data": {"url": "cdn/art.png"}})
    monkeypatch.setattr(sgdb, "fetch", lambda url, key=None: f"downloaded {url}".encode())

    assert sgdb.artwork_from("801236", "k") == b"downloaded cdn/art.png"


def test_a_plain_image_url_is_downloaded_as_is(monkeypatch):
    monkeypatch.setattr(sgdb, "fetch", lambda url, key=None: f"downloaded {url}".encode())

    assert sgdb.artwork_from("https://example.com/a.png", "k") == b"downloaded https://example.com/a.png"


def test_edition_notes_are_dropped_before_searching():
    assert fetch_covers.searchable("Shadow of the Colossus (Remake 2018)") == "Shadow of the Colossus"


def test_a_title_the_storefronts_spell_differently_uses_its_alias():
    assert fetch_covers.searchable("Spyro 2: Ripto's Rage! (Reignited)") == "Spyro Reignited Trilogy"


def test_an_exact_listing_is_fully_confident():
    assert fetch_covers.closeness("Hollow Knight", "Hollow Knight™") > fetch_covers.CONFIDENT


def test_a_different_game_is_not_confident_enough():
    assert fetch_covers.closeness("Ghost of Yotei", "Ghostrunner") < fetch_covers.CONFIDENT


def test_a_link_is_told_apart_from_a_title():
    assert set_cover.looks_like_reference("https://www.steamgriddb.com/grid/801236")
    assert set_cover.looks_like_reference("801236")
    assert not set_cover.looks_like_reference("Hollow Knight")


# Both scripts write through the Archive rather than editing the file themselves,
# so the rules of the archive hold whichever writer is running.


def test_fetch_covers_records_what_it_downloads(archive, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fetch_covers.py"])
    monkeypatch.setattr(
        fetch_covers, "artwork_for", lambda title, key: (png_bytes(), "somewhere")
    )
    monkeypatch.setattr(fetch_covers.time, "sleep", lambda _: None)

    assert fetch_covers.main() == 0

    assert [g["cover"] for g in archive.games()] == [
        "clair-obscur-expedition-33.webp",
        "celeste.webp",
    ]
    assert (archive.covers_directory / "celeste.webp").exists()


def test_fetch_covers_leaves_the_ratings_alone(archive, monkeypatch):
    """A cover run must not disturb the judgements it passes over."""
    monkeypatch.setattr(sys, "argv", ["fetch_covers.py"])
    monkeypatch.setattr(
        fetch_covers, "artwork_for", lambda title, key: (png_bytes(), "somewhere")
    )
    monkeypatch.setattr(fetch_covers.time, "sleep", lambda _: None)

    fetch_covers.main()

    assert [g["rating"] for g in archive.games()] == [10, 8]


def test_fetch_covers_keeps_what_it_already_fetched_when_one_fails(
    archive, monkeypatch
):
    monkeypatch.setattr(sys, "argv", ["fetch_covers.py"])
    monkeypatch.setattr(fetch_covers.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        fetch_covers,
        "artwork_for",
        lambda title, key: (png_bytes(), "ok") if title == "Celeste" else None,
    )

    fetch_covers.main()

    recorded = {g["title"]: g.get("cover") for g in archive.games()}
    assert recorded == {"Clair Obscur: Expedition 33": None, "Celeste": "celeste.webp"}


def test_set_cover_records_the_artwork_against_a_partial_title(archive, monkeypatch):
    monkeypatch.setattr(sgdb, "artwork_from", lambda reference, key: png_bytes())

    assert set_cover.main(["expedition", "801236"]) == 0

    assert archive.find("Clair Obscur: Expedition 33")["cover"] == (
        "clair-obscur-expedition-33.webp"
    )


def test_set_cover_writes_nothing_for_a_title_it_cannot_place(archive, monkeypatch):
    monkeypatch.setattr(sgdb, "artwork_from", lambda reference, key: png_bytes())

    assert set_cover.main(["Hades", "801236"]) == 1

    assert all("cover" not in g for g in archive.games())
