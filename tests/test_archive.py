import json
from pathlib import Path

import pytest

from vgdb import config
from vgdb.archive import Ambiguous, Archive, Invalid


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
    archive.record("Celeste", rating=8)
    archive.record("Celeste", rating=9)

    assert [f.name for f in tmp_path.iterdir()] == ["games.json"]


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


# The cover is attached by its own operation, so an edit must not drop it.


def test_recalibrating_a_rating_keeps_the_cover(archive):
    archive.record("Celeste", rating=8)
    archive.set_cover("Celeste", "celeste.webp")

    archive.record("Celeste", rating=6, notes="aged badly")

    assert archive.games()[0]["cover"] == "celeste.webp"


def test_renaming_a_game_keeps_its_cover(archive):
    archive.record("Celest", rating=8)
    archive.set_cover("Celest", "celest.webp")

    archive.record("Celeste", rating=8, previous_title="Celest")

    assert archive.games()[0]["cover"] == "celest.webp"


def test_a_cover_for_an_absent_game_is_refused(archive):
    with pytest.raises(LookupError):
        archive.set_cover("Missing", "missing.webp")


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
