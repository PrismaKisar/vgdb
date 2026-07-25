"""Web interface: one table of games."""

from pathlib import Path

from flask import Flask, jsonify, render_template

from vgdb import store


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

    return app
