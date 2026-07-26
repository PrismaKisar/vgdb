"""The HTTP seam: status codes, and the translation to and from the Archive.

What a valid game *is* belongs to the Archive and is tested in test_archive.py.
What is left here is the wire.
"""

import io
import json

import pytest
from PIL import Image

from vgdb.app import MAX_COVER_BYTES, create_app
from vgdb.archive import Archive


@pytest.fixture
def archive(tmp_path):
    return Archive(tmp_path / "games.json")


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
    archive.path.write_text(json.dumps(games), encoding="utf-8")

    assert client.get("/api/games").get_json() == games


def test_put_records_a_game_and_answers_with_it(client, archive):
    response = client.put(
        "/api/games/Celeste", json={"rating": 8, "notes": "Hard but fair"}
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "title": "Celeste",
        "rating": 8,
        "notes": "Hard but fair",
    }
    assert archive.games() == [response.get_json()]


def test_a_platinum_survives_the_wire(client, archive):
    """JSON null is how the page says 'this game has no platinum'."""
    client.put("/api/games/Celeste", json={"rating": 8, "platinum": False})
    assert archive.games()[0]["platinum"] is False

    client.put("/api/games/Celeste", json={"rating": 8, "platinum": None})
    assert "platinum" not in archive.games()[0]


def test_a_rename_is_carried_across_as_previous_title(client, archive):
    client.put("/api/games/Celest", json={"rating": 8})

    response = client.put(
        "/api/games/Celeste", json={"rating": 8, "previousTitle": "Celest"}
    )

    assert response.status_code == 200
    assert [g["title"] for g in archive.games()] == ["Celeste"]


def test_a_game_the_archive_refuses_is_a_400_carrying_the_reason(client, archive):
    response = client.put("/api/games/Celeste", json={"rating": 11})

    assert response.status_code == 400
    assert response.get_json()["error"] == "The rating must be a number from 1 to 10"
    assert archive.games() == []


def test_a_whitespace_only_title_is_a_400(client, archive):
    response = client.put("/api/games/%20%20", json={"rating": 8})

    assert response.status_code == 400
    assert response.get_json()["error"] == "The title cannot be empty"
    assert archive.games() == []


def test_a_put_with_no_body_at_all_is_a_400(client):
    assert client.put("/api/games/Celeste").status_code == 400


def png_bytes(width=600, height=900):
    out = io.BytesIO()
    Image.new("RGB", (width, height), "teal").save(out, format="PNG")
    return out.getvalue()


def attach(client, title, data=None, filename="art.png"):
    return client.post(
        f"/api/games/{title}/cover",
        data={"file": (io.BytesIO(png_bytes() if data is None else data), filename)},
        content_type="multipart/form-data",
    )


def test_uploading_a_cover_attaches_it_to_the_game(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = attach(client, "Celeste")

    assert response.status_code == 200
    cover = response.get_json()["cover"]
    assert archive.games()[0]["cover"] == cover
    assert (archive.covers_directory / cover).exists()


def test_the_stored_cover_can_be_fetched_back(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})
    cover = attach(client, "Celeste").get_json()["cover"]

    response = client.get(f"/covers/{cover}")

    assert response.status_code == 200
    assert response.data == (archive.covers_directory / cover).read_bytes()


def test_a_cover_for_an_unknown_game_is_a_404(client):
    assert attach(client, "Missing").status_code == 404


def test_a_request_carrying_no_file_is_a_400(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = client.post(
        "/api/games/Celeste/cover", data={}, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert "cover" not in archive.games()[0]


def test_a_file_that_is_not_an_image_is_rejected(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = attach(client, "Celeste", data=b"not an image")

    assert response.status_code == 400
    assert "cover" not in archive.games()[0]


def test_an_archive_that_cannot_be_written_is_not_blamed_on_the_image(
    client, archive, monkeypatch
):
    """A full disk is our problem, not 'that file is not a readable image'."""
    client.put("/api/games/Celeste", json={"rating": 8})
    monkeypatch.setattr(
        type(archive), "attach_cover", lambda *_: (_ for _ in ()).throw(OSError("full"))
    )

    with pytest.raises(OSError):
        attach(client, "Celeste")


def test_an_oversized_upload_is_rejected(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = attach(client, "Celeste", data=b"x" * (MAX_COVER_BYTES + 1))

    assert response.status_code == 400
    assert "cover" not in archive.games()[0]


def test_delete_removes_the_game(client, archive):
    client.put("/api/games/Celeste", json={"rating": 8})

    response = client.delete("/api/games/Celeste")

    assert response.status_code == 200
    assert archive.games() == []


def test_deleting_an_absent_game_is_a_404(client):
    assert client.delete("/api/games/Missing").status_code == 404
