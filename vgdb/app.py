"""Web interface: one table of games."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from vgdb import store

OPTIONAL_FIELDS = ("notes",)


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

    @app.get("/")
    def page():
        return render_template("index.html")

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

        store.upsert(archive, game, previous_title=body.get("previousTitle"))
        return jsonify(game)

    @app.delete("/api/games/<title>")
    def remove_game(title):
        if not store.delete(archive, title):
            return jsonify({"error": f"{title} is not in the archive"}), 404
        return jsonify({"removed": title})

    return app
