import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from vgdb import config
from vgdb.archive import Ambiguous, Archive, Invalid, Unreadable


def image_bytes(width=600, height=900, colour="teal"):
    out = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def archive(tmp_path):
    return Archive(tmp_path / "games.json")


def test_a_missing_archive_holds_no_games(archive):
    assert archive.games() == []


def test_a_blank_archive_does_not_break_the_page(tmp_path):
    (tmp_path / "games.json").write_text("   \n")

    assert Archive(tmp_path / "games.json").games() == []


def test_archived_games_are_read_back(tmp_path):
    games = [{"title": "Hollow Knight", "rating": 9, "notes": "Perfect combat"}]
    (tmp_path / "games.json").write_text(json.dumps(games), encoding="utf-8")

    assert Archive(tmp_path / "games.json").games() == games


def test_a_recorded_game_is_read_back(archive):
    archive.record("Celeste", rating=8, notes="Hard but fair")

    assert archive.games() == [
        {"title": "Celeste", "rating": 8, "notes": "Hard but fair"}
    ]


def test_recording_leaves_no_scratch_files(archive, tmp_path):
    """Only the archive and the lock two writers queue on, nothing half-written."""
    archive.record("Celeste", rating=8)
    archive.record("Celeste", rating=9)

    assert sorted(f.name for f in tmp_path.iterdir()) == [".games.json.lock", "games.json"]


def test_the_archive_stays_readable_by_hand(archive, tmp_path):
    """ADR-0001: the LLM and a human both read this file directly."""
    archive.record("Celeste", rating=8)

    assert (tmp_path / "games.json").read_text(encoding="utf-8") == (
        '[\n  {\n    "title": "Celeste",\n    "rating": 8\n  }\n]\n'
    )


# The Rating: how much the game was enjoyed, 1 to 10, half points allowed.


def test_the_rating_allows_half_points(archive):
    archive.record("Celeste", rating=7.5)

    assert archive.games()[0]["rating"] == 7.5


@pytest.mark.parametrize("rating", [0, 11, -3, "eight", None, True])
def test_a_rating_off_the_scale_is_refused(archive, rating):
    with pytest.raises(Invalid, match="rating"):
        archive.record("Celeste", rating=rating)

    assert archive.games() == []


def test_a_title_of_nothing_but_spaces_is_refused(archive):
    with pytest.raises(Invalid, match="title"):
        archive.record("   ", rating=8)

    assert archive.games() == []


def test_a_title_is_stored_without_its_surrounding_spaces(archive):
    archive.record("  Celeste  ", rating=8)

    assert archive.games()[0]["title"] == "Celeste"


# Notes: absent rather than empty, so the archive stays free of mute fields.


def test_notes_are_kept(archive):
    archive.record("Celeste", rating=8, notes="Hard but fair")

    assert archive.games()[0]["notes"] == "Hard but fair"


def test_empty_notes_leave_no_field_behind(archive):
    archive.record("Celeste", rating=8, notes="")

    assert "notes" not in archive.games()[0]


def test_notes_are_stored_exactly_as_written(archive):
    """The notes are the owner's own words; the archive does not tidy them."""
    archive.record("Celeste", rating=8, notes="  hard, but fair  ")

    assert archive.games()[0]["notes"] == "  hard, but fair  "


def test_notes_can_be_taken_back(archive):
    archive.record("Celeste", rating=8, notes="written in haste")

    archive.record("Celeste", rating=8, notes="")

    assert "notes" not in archive.games()[0]


# The Platinum: three states, and only one of them means absent.


def test_a_won_platinum_is_recorded(archive):
    archive.record("Celeste", rating=8, platinum=True)

    assert archive.games()[0]["platinum"] is True


def test_a_missed_platinum_is_recorded_too(archive):
    """'Not won' says something about the player; it is not the same as 'no platinum'."""
    archive.record("Celeste", rating=8, platinum=False)

    assert archive.games()[0]["platinum"] is False


def test_a_game_with_no_platinum_carries_no_flag(archive):
    archive.record("Celeste", rating=8, platinum=None)

    assert "platinum" not in archive.games()[0]


def test_the_platinum_can_be_taken_back(archive):
    archive.record("Celeste", rating=8, platinum=True)

    archive.record("Celeste", rating=8, platinum=None)

    assert "platinum" not in archive.games()[0]


# Title identity: the title names the game, ignoring case and outer spaces.


def test_a_second_recording_recalibrates_instead_of_duplicating(archive):
    archive.record("Hollow Knight", rating=9, notes="great")

    archive.record("hollow knight", rating=10, notes="replayed")

    assert archive.games() == [
        {"title": "hollow knight", "rating": 10, "notes": "replayed"}
    ]


def test_find_returns_the_game_whatever_the_case(archive):
    archive.record("Hollow Knight", rating=9)

    assert archive.find("  hollow knight ")["rating"] == 9


def test_find_returns_nothing_for_an_absent_game(archive):
    archive.record("Hollow Knight", rating=9)

    assert archive.find("Celeste") is None


def test_find_does_not_settle_for_a_partial_title(archive):
    archive.record("Hollow Knight", rating=9)

    assert archive.find("Hollow") is None


# Renaming: fixing a typo must not leave two entries behind.


def test_renaming_replaces_the_game_instead_of_adding_one(archive):
    archive.record("Celest", rating=8)

    archive.record("Celeste", rating=8, previous_title="Celest")

    assert archive.games() == [{"title": "Celeste", "rating": 8}]


def test_a_renamed_game_keeps_its_position(archive):
    """Rows must not jump during a Recalibration pass."""
    archive.record("Celest", rating=8)
    archive.record("Hades", rating=9)

    archive.record("Celeste", rating=8, previous_title="Celest")

    assert [g["title"] for g in archive.games()] == ["Celeste", "Hades"]


# Attaching a cover: one operation, given a title and the image bytes. The
# thumbnailing, the file name and where it lands are the Archive's business.


def test_attaching_a_cover_points_the_game_at_a_stored_file(archive):
    archive.record("Celeste", rating=8)

    game = archive.attach_cover("Celeste", image_bytes())

    assert archive.find("Celeste")["cover"] == game["cover"]
    assert (archive.covers_directory / game["cover"]).exists()


def test_a_cover_is_a_webp_that_keeps_the_shape_of_the_artwork(archive):
    """Cropping to a square would cut the title off a 2:3 store poster."""
    archive.record("Celeste", rating=8)

    game = archive.attach_cover("Celeste", image_bytes(600, 900))

    with Image.open(archive.covers_directory / game["cover"]) as thumb:
        assert thumb.format == "WEBP"
        assert thumb.size == (128, 192)


def test_a_large_cover_is_shrunk_to_a_few_kilobytes(archive):
    archive.record("Celeste", rating=8)

    game = archive.attach_cover("Celeste", image_bytes(2000, 2000))

    assert (archive.covers_directory / game["cover"]).stat().st_size < 20_000


def test_a_cover_for_an_absent_game_is_refused(archive):
    with pytest.raises(LookupError):
        archive.attach_cover("Missing", image_bytes())


def test_an_unreadable_image_leaves_the_game_as_it_was(archive):
    archive.record("Celeste", rating=8)

    with pytest.raises(Unreadable):
        archive.attach_cover("Celeste", b"not an image")

    assert "cover" not in archive.find("Celeste")
    assert not archive.covers_directory.exists()


def test_the_size_of_a_stored_cover_is_reported_without_asking_for_its_path(archive):
    """What the cover scripts print after a fetch."""
    archive.record("Celeste", rating=8)
    game = archive.attach_cover("Celeste", image_bytes())

    expected = (archive.covers_directory / game["cover"]).stat().st_size
    assert archive.cover_size("Celeste") == expected


# The cover is attached by its own operation, so an edit must not drop it.


def test_recalibrating_a_rating_keeps_the_cover(archive):
    archive.record("Celeste", rating=8)
    stored = archive.attach_cover("Celeste", image_bytes())["cover"]

    archive.record("Celeste", rating=6, notes="aged badly")

    assert archive.games()[0]["cover"] == stored


def test_renaming_a_game_keeps_its_cover(archive):
    archive.record("Celest", rating=8)
    archive.attach_cover("Celest", image_bytes())
    artwork = (archive.covers_directory / archive.find("Celest")["cover"]).read_bytes()

    archive.record("Celeste", rating=8, previous_title="Celest")

    renamed = archive.games()[0]["cover"]
    assert (archive.covers_directory / renamed).read_bytes() == artwork


# One game, one cover file: no orphans on disk, and no two games sharing one.


def test_replacing_a_cover_leaves_a_single_file_behind(archive):
    archive.record("Celeste", rating=8)
    archive.attach_cover("Celeste", image_bytes(600, 900))

    archive.attach_cover("Celeste", image_bytes(400, 400, "crimson"))

    assert len(list(archive.covers_directory.iterdir())) == 1


def test_renaming_a_game_leaves_no_orphaned_cover_behind(archive):
    """The file name follows the title, so the old one would linger."""
    archive.record("Celest", rating=8)
    archive.attach_cover("Celest", image_bytes())

    archive.record("Celeste", rating=8, previous_title="Celest")

    stored = archive.games()[0]["cover"]
    assert [f.name for f in archive.covers_directory.iterdir()] == [stored]


def test_a_game_taking_over_a_freed_title_does_not_take_its_artwork(archive):
    """The renamed game's file would otherwise be there for the taking."""
    archive.record("Celest", rating=8)
    archive.attach_cover("Celest", image_bytes())
    archive.record("Celeste", rating=8, previous_title="Celest")

    archive.record("Celest", rating=3)
    archive.attach_cover("Celest", image_bytes(400, 400, "crimson"))

    renamed, newcomer = archive.games()
    assert renamed["cover"] != newcomer["cover"]
    assert (archive.covers_directory / renamed["cover"]).exists()


def test_renaming_a_game_whose_cover_file_is_gone_still_works(archive):
    archive.record("Celest", rating=8)
    stored = archive.attach_cover("Celest", image_bytes())["cover"]
    (archive.covers_directory / stored).unlink()

    archive.record("Celeste", rating=8, previous_title="Celest")

    assert archive.games() == [{"title": "Celeste", "rating": 8, "cover": stored}]


def test_two_titles_that_read_alike_keep_separate_covers(archive):
    """'Hollow Knight' and 'Hollow: Knight!' must not overwrite each other."""
    archive.record("Hollow Knight", rating=9)
    archive.record("Hollow: Knight!", rating=4)

    one = archive.attach_cover("Hollow Knight", image_bytes())
    other = archive.attach_cover("Hollow: Knight!", image_bytes(400, 400, "crimson"))

    assert one["cover"] != other["cover"]
    assert len(list(archive.covers_directory.iterdir())) == 2


def test_a_title_of_symbols_alone_still_gets_a_cover(archive):
    archive.record("!!!", rating=5)

    game = archive.attach_cover("!!!", image_bytes())

    assert (archive.covers_directory / game["cover"]).exists()


def test_covers_sit_next_to_the_archive(archive, tmp_path):
    assert archive.covers_directory == tmp_path / "covers"


# Removal.


def test_remove_takes_out_only_the_named_game(archive):
    archive.record("Hollow Knight", rating=9)
    archive.record("Celeste", rating=8)

    assert archive.remove("hollow knight") is True
    assert archive.games() == [{"title": "Celeste", "rating": 8}]


def test_removing_an_absent_game_reports_it(archive):
    archive.record("Celeste", rating=8)

    assert archive.remove("Missing") is False


# Two writers at once — the page saving while a cover script runs. Both come
# through the Archive, so one write landing inside another is normal operation
# here, and losing a judgement to it would be silent.

WRITER = """
import sys, time
from vgdb.archive import Archive

path, title, pause = sys.argv[1], sys.argv[2], float(sys.argv[3])

# Hold the writer open exactly where the danger is: it has read the archive
# and made its change, and has not put it back yet.
writing_back = Archive._write
Archive._write = lambda self, games: (time.sleep(pause), writing_back(self, games))[1]

Archive(path).record(title, rating=8)
"""


def writing(path, title, pause=0.0):
    """Another process recording one game, dawdling mid-write if asked."""
    return subprocess.Popen(
        [sys.executable, "-c", WRITER, str(path), title, str(pause)],
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
    )


def test_a_write_landing_inside_another_one_is_not_lost(tmp_path):
    """The second writer must wait for the first, not start from stale games."""
    path = tmp_path / "games.json"
    Archive(path).record("Celeste", rating=8)

    dawdling = writing(path, "Hades", pause=2.0)
    time.sleep(0.5)  # long enough for it to have read the archive
    quick = writing(path, "Hollow Knight")

    assert dawdling.wait(timeout=30) == 0
    assert quick.wait(timeout=30) == 0
    assert sorted(g["title"] for g in Archive(path).games()) == [
        "Celeste",
        "Hades",
        "Hollow Knight",
    ]


def test_saving_one_edit_reads_the_archive_once(archive, monkeypatch):
    """Reading twice is not just wasteful: the two reads can disagree."""
    archive.record("Celeste", rating=8)
    reads = []
    reading = Archive.games
    monkeypatch.setattr(
        Archive, "games", lambda self: (reads.append(1), reading(self))[1]
    )

    archive.record("Celeste", rating=9, notes="better on replay")

    assert len(reads) == 1


# resolve(): the looser lookup the cover scripts need, where typing the whole
# title of "Clair Obscur: Expedition 33" at a shell prompt is a nuisance.


@pytest.fixture
def shelf(archive):
    archive.record("Clair Obscur: Expedition 33", rating=10)
    archive.record("Hollow Knight", rating=9)
    archive.record("Hollow Knight: Silksong", rating=9.5)
    return archive


def test_a_partial_title_finds_the_game(shelf):
    assert shelf.resolve("expedition")["rating"] == 10


def test_an_exact_title_wins_over_a_partial_match(shelf):
    """'Hollow Knight' must not resolve to Silksong just because it matches it."""
    assert shelf.resolve("Hollow Knight")["rating"] == 9


def test_an_ambiguous_title_is_refused_rather_than_guessed(shelf):
    """'hollow' matches both Hollow Knights, so it must not pick one at random."""
    with pytest.raises(Ambiguous) as raised:
        shelf.resolve("hollow")

    assert raised.value.matches == ["Hollow Knight", "Hollow Knight: Silksong"]


def test_an_unknown_title_resolves_to_nothing(shelf):
    assert shelf.resolve("Celeste") is None


# Where the archive lives. Which settings say so is test_config.py's business;
# what matters here is that an Archive nobody placed goes and asks.


def test_an_unplaced_archive_takes_the_configured_location(tmp_path, monkeypatch):
    monkeypatch.setenv("VGDB_FILE", str(tmp_path / "other.json"))

    assert Archive().path == config.archive_path()


def test_the_archive_never_lands_inside_the_code_repository(monkeypatch):
    """Personal ratings must not sit inside a repository that is public."""
    monkeypatch.delenv("VGDB_FILE", raising=False)

    assert Path(__file__).resolve().parent.parent not in Archive().path.parents


def test_a_home_relative_location_is_expanded(monkeypatch):
    """Whether the path arrives as an argument or as VGDB_FILE, ~ means home."""
    monkeypatch.delenv("VGDB_FILE", raising=False)

    assert Archive("~/elsewhere/games.json").path == Path.home() / "elsewhere" / "games.json"
