import io
import json

import pytest
from PIL import Image

from vgdb import store
from vgdb.app import create_app


@pytest.fixture
def archive(tmp_path):
    return tmp_path / "games.json"


@pytest.fixture
def client(archive):
    app = create_app(archive)
    app.config["TESTING"] = True
    return app.test_client()


def test_the_home_page_serves_the_table(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"<table" in response.data


def test_an_empty_archive_returns_no_games(client):
    response = client.get("/api/games")

    assert response.status_code == 200
    assert response.get_json() == []


def test_the_archived_games_are_listed(client, archive):
    games = [{"title": "Celeste", "rating": 8, "notes": "Hard but fair"}]
    archive.write_text(json.dumps(games), encoding="utf-8")

    assert client.get("/api/games").get_json() == games


def test_put_records_a_new_game(client, archive):
    response = client.put(
        "/api/games/Celeste", json={"rating": 8, "notes": "Hard but fair"}
    )

    assert response.status_code == 200
    assert store.load(archive) == [
        {"title": "Celeste", "rating": 8, "notes": "Hard but fair"}
    ]


def test_a_repeated_put_recalibrates_the_rating(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    client.put("/api/games/Celeste", json={"rating": 6, "notes": "aged badly"})

    assert store.load(archive) == [
        {"title": "Celeste", "rating": 6, "notes": "aged badly"}
    ]


def test_a_won_platinum_is_recorded(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8, "platinum": True})

    assert store.load(archive)[0]["platinum"] is True


def test_a_missed_platinum_is_recorded_too(client, archive):
    """False must survive: 'not won' is a different fact from 'no platinum exists'."""
    client.put("/api/games/Celeste", json={"rating": 8, "platinum": False})

    assert store.load(archive)[0]["platinum"] is False


def test_a_game_without_a_platinum_carries_no_flag(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8, "platinum": None})

    assert "platinum" not in store.load(archive)[0]


def test_the_platinum_can_be_taken_back(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8, "platinum": True})

    client.put("/api/games/Celeste", json={"rating": 8, "platinum": None})

    assert "platinum" not in store.load(archive)[0]


def test_fixing_a_title_does_not_create_a_duplicate(client, archive):
    client.put("/api/games/Celest", json={"rating": 8, "notes": "typo in the title"})

    response = client.put(
        "/api/games/Celeste",
        json={"rating": 8, "notes": "typo in the title", "previousTitle": "Celest"},
    )

    assert response.status_code == 200
    assert store.load(archive) == [
        {"title": "Celeste", "rating": 8, "notes": "typo in the title"}
    ]


def test_a_renamed_game_keeps_its_row(client, archive):
    client.put("/api/games/First", json={"rating": 9})
    client.put("/api/games/Second", json={"rating": 8})

    client.put("/api/games/Renamed", json={"rating": 9, "previousTitle": "First"})

    assert [g["title"] for g in store.load(archive)] == ["Renamed", "Second"]


def png_bytes():
    out = io.BytesIO()
    Image.new("RGB", (600, 900), "teal").save(out, format="PNG")
    return out.getvalue()


def attach(client, title, data=None, filename="art.png"):
    return client.post(
        f"/api/games/{title}/cover",
        data={"file": (io.BytesIO(data or png_bytes()), filename)},
        content_type="multipart/form-data",
    )


def test_uploading_a_cover_attaches_it_to_the_game(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = attach(client, "Celeste")

    assert response.status_code == 200
    cover = store.load(archive)[0]["cover"]
    assert (archive.parent / "covers" / cover).exists()


def test_the_stored_cover_can_be_fetched_back(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})
    attach(client, "Celeste")

    cover = store.load(archive)[0]["cover"]
    response = client.get(f"/covers/{cover}")

    assert response.status_code == 200
    assert response.data == (archive.parent / "covers" / cover).read_bytes()


def test_editing_a_game_keeps_its_cover(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})
    attach(client, "Celeste")

    client.put("/api/games/Celeste", json={"rating": 6, "notes": "recalibrated"})

    assert "cover" in store.load(archive)[0]


def test_renaming_a_game_keeps_its_cover(client, archive):
    client.put("/api/games/Celest", json={"rating": 8})
    attach(client, "Celest")

    client.put("/api/games/Celeste", json={"rating": 8, "previousTitle": "Celest"})

    assert "cover" in store.load(archive)[0]


def test_a_file_that_is_not_an_image_is_rejected(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = attach(client, "Celeste", data=b"not an image")

    assert response.status_code == 400
    assert "cover" not in store.load(archive)[0]


def test_a_cover_for_an_unknown_game_is_a_404(client):
    assert attach(client, "Missing").status_code == 404


def test_delete_removes_the_game(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = client.delete("/api/games/Celeste")

    assert response.status_code == 200
    assert store.load(archive) == []


def test_deleting_an_absent_game_is_a_404(client):
    assert client.delete("/api/games/Missing").status_code == 404


@pytest.mark.parametrize("rating", [0, 11, -3, "eight", None])
def test_an_invalid_rating_is_rejected(client, archive, rating):
    response = client.put("/api/games/Celeste", json={"rating": rating})

    assert response.status_code == 400
    assert store.load(archive) == []


def test_the_rating_allows_half_points(client, archive):
    assert client.put("/api/games/Celeste", json={"rating": 7.5}).status_code == 200
    assert store.load(archive)[0]["rating"] == 7.5


def test_a_whitespace_only_title_is_rejected(client, archive):
    response = client.put("/api/games/%20%20", json={"rating": 8})

    assert response.status_code == 400
    assert store.load(archive) == []
