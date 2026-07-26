import json
from pathlib import Path

from vgdb import store


def test_missing_archive_is_empty(tmp_path):
    assert store.load(tmp_path / "games.json") == []


def test_blank_archive_does_not_break_the_page(tmp_path):
    archive = tmp_path / "games.json"
    archive.write_text("   \n")

    assert store.load(archive) == []


def test_archived_games_are_read_back(tmp_path):
    archive = tmp_path / "games.json"
    games = [{"title": "Hollow Knight", "rating": 9, "notes": "Perfect combat"}]
    archive.write_text(json.dumps(games), encoding="utf-8")

    assert store.load(archive) == games


def test_saved_games_are_read_back(tmp_path):
    archive = tmp_path / "games.json"
    games = [{"title": "Celeste", "rating": 8, "notes": "Hard but fair"}]

    store.save(archive, games)

    assert store.load(archive) == games


def test_saving_leaves_no_scratch_files(tmp_path):
    archive = tmp_path / "games.json"

    store.save(archive, [{"title": "Celeste", "rating": 8}])
    store.save(archive, [{"title": "Celeste", "rating": 9}])

    assert [f.name for f in tmp_path.iterdir()] == ["games.json"]


def test_upsert_adds_an_unseen_game(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Hollow Knight", "rating": 9}])

    store.upsert(archive, {"title": "Celeste", "rating": 8})

    assert [g["title"] for g in store.load(archive)] == ["Hollow Knight", "Celeste"]


def test_upsert_updates_without_duplicating(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Hollow Knight", "rating": 9, "notes": "great"}])

    store.upsert(archive, {"title": "Hollow Knight", "rating": 10, "notes": "replayed"})

    assert store.load(archive) == [
        {"title": "Hollow Knight", "rating": 10, "notes": "replayed"}
    ]


def test_titles_match_regardless_of_case(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Hollow Knight", "rating": 9}])

    store.upsert(archive, {"title": "hollow knight", "rating": 7})

    assert store.load(archive) == [{"title": "hollow knight", "rating": 7}]


def test_find_returns_the_game_whatever_the_case(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Hollow Knight", "rating": 9}])

    assert store.find(archive, "hollow knight")["rating"] == 9


def test_find_returns_nothing_for_an_absent_game(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Hollow Knight", "rating": 9}])

    assert store.find(archive, "Celeste") is None


def test_renaming_replaces_the_game_instead_of_adding_one(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Celest", "rating": 8}])

    store.upsert(archive, {"title": "Celeste", "rating": 8}, previous_title="Celest")

    assert store.load(archive) == [{"title": "Celeste", "rating": 8}]


def test_a_renamed_game_keeps_its_position(tmp_path):
    archive = tmp_path / "games.json"
    store.save(
        archive,
        [{"title": "Celest", "rating": 8}, {"title": "Hades", "rating": 9}],
    )

    store.upsert(archive, {"title": "Celeste", "rating": 8}, previous_title="Celest")

    assert [g["title"] for g in store.load(archive)] == ["Celeste", "Hades"]


def test_delete_removes_only_the_named_game(tmp_path):
    archive = tmp_path / "games.json"
    store.save(
        archive,
        [{"title": "Hollow Knight", "rating": 9}, {"title": "Celeste", "rating": 8}],
    )

    assert store.delete(archive, "hollow knight") is True
    assert store.load(archive) == [{"title": "Celeste", "rating": 8}]


def test_deleting_an_absent_game_reports_it(tmp_path):
    archive = tmp_path / "games.json"
    store.save(archive, [{"title": "Celeste", "rating": 8}])

    assert store.delete(archive, "Missing") is False


def test_the_archive_lives_outside_the_code_repository(monkeypatch):
    """Personal ratings must not sit inside a repository that is public."""
    monkeypatch.delenv("VGDB_FILE", raising=False)

    path = store.archive_path()

    assert path.is_absolute()
    assert path == Path.home() / ".vgdb" / "games.json"
    assert Path(__file__).resolve().parent.parent not in path.parents


def test_vgdb_file_overrides_the_default_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("VGDB_FILE", str(tmp_path / "other.json"))

    assert store.archive_path() == tmp_path / "other.json"
