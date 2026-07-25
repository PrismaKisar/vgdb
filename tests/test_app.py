import json

import pytest

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
