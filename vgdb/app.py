"""Web interface: one table of games."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from vgdb import covers as cover_store
from vgdb import store

OPTIONAL_FIELDS = ("notes",)
MAX_COVER_BYTES = 16 * 1024 * 1024


def _valid_rating(rating) -> bool:
    """A rating is how much the game was enjoyed: 1 to 10, half points allowed."""
    if isinstance(rating, bool) or not isinstance(rating, (int, float)):
        return False
    return 1 <= rating <= 10


def create_app(archive: Path) -> Flask:
    app = Flask(__name__)
    # vgdb stays up for days: without this, a process started before an edit
    # keeps serving the template it compiled at boot.
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    covers = cover_store.directory(archive)

    @app.get("/")
    def page():
        return render_template("index.html")

    @app.get("/covers/<name>")
    def cover(name):
        return send_from_directory(covers, name)

    @app.get("/api/games")
    def listing():
        return jsonify(store.load(archive))

    @app.put("/api/games/<title>")
    def save_game(title):
        body = request.get_json(silent=True) or {}

        if not title.strip():
            return jsonify({"error": "The title cannot be empty"}), 400
        if not _valid_rating(body.get("rating")):
            return jsonify({"error": "The rating must be a number from 1 to 10"}), 400

        game = {"title": title.strip(), "rating": body["rating"]}
        for field in OPTIONAL_FIELDS:
            if body.get(field):
                game[field] = body[field]

        # Three states, not two: "not won" and "there is no platinum" are
        # different facts, and only the second one means absent. Note that
        # "not won" is False, which the loop above would drop as empty.
        if isinstance(body.get("platinum"), bool):
            game["platinum"] = body["platinum"]

        # The cover is attached by its own endpoint, so a plain edit of the
        # rating or the notes must not drop it.
        previous_title = body.get("previousTitle")
        existing = store.find(archive, previous_title or title)
        if existing and existing.get("cover"):
            game["cover"] = existing["cover"]

        store.upsert(archive, game, previous_title=previous_title)
        return jsonify(game)

    @app.post("/api/games/<title>/cover")
    def attach_cover(title):
        game = store.find(archive, title)
        if game is None:
            return jsonify({"error": f"{title} is not in the archive"}), 404

        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"error": "No image was sent"}), 400

        data = upload.read(MAX_COVER_BYTES + 1)
        if len(data) > MAX_COVER_BYTES:
            return jsonify({"error": "Image too large (max 16 MB)"}), 400

        try:
            game["cover"] = cover_store.store_for(archive, game["title"], data)
        except OSError:
            return jsonify({"error": "That file is not a readable image"}), 400

        store.upsert(archive, game)
        return jsonify(game)

    @app.delete("/api/games/<title>")
    def remove_game(title):
        if not store.delete(archive, title):
            return jsonify({"error": f"{title} is not in the archive"}), 404
        return jsonify({"removed": title})

    return app
