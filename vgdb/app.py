"""Web interface: one table of games.

Nothing here decides what a game is — that lives in the Archive. This module
translates between HTTP and the archive, and nothing else.
"""

from flask import Flask, jsonify, render_template, request, send_from_directory

from vgdb.archive import Archive, Invalid

MAX_COVER_BYTES = 16 * 1024 * 1024


def create_app(archive: Archive) -> Flask:
    app = Flask(__name__)
    # vgdb stays up for days: without this, a process started before an edit
    # keeps serving the template it compiled at boot.
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.get("/")
    def page():
        return render_template("index.html")

    @app.get("/covers/<name>")
    def cover(name):
        return send_from_directory(archive.covers_directory, name)

    @app.get("/api/games")
    def listing():
        return jsonify(archive.games())

    @app.put("/api/games/<title>")
    def save_game(title):
        body = request.get_json(silent=True) or {}
        try:
            game = archive.record(
                title,
                rating=body.get("rating"),
                notes=body.get("notes"),
                platinum=body.get("platinum"),
                previous_title=body.get("previousTitle"),
            )
        except Invalid as refused:
            return jsonify({"error": str(refused)}), 400
        return jsonify(game)

    @app.post("/api/games/<title>/cover")
    def attach_cover(title):
        game = archive.find(title)
        if game is None:
            return jsonify({"error": f"{title} is not in the archive"}), 404

        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"error": "No image was sent"}), 400

        data = upload.read(MAX_COVER_BYTES + 1)
        if len(data) > MAX_COVER_BYTES:
            return jsonify({"error": "Image too large (max 16 MB)"}), 400

        try:
            return jsonify(archive.attach_cover(game["title"], data))
        except OSError:
            return jsonify({"error": "That file is not a readable image"}), 400

    @app.delete("/api/games/<title>")
    def remove_game(title):
        if not archive.remove(title):
            return jsonify({"error": f"{title} is not in the archive"}), 404
        return jsonify({"removed": title})

    return app
