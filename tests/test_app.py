import json

import pytest

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
