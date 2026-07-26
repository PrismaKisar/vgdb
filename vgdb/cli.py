"""The `vgdb` command: opens the archive in a browser."""

import socket
import threading
import webbrowser

from vgdb import store
from vgdb.app import create_app

PORT = 5757
ADDRESS = f"http://127.0.0.1:{PORT}/"


def instance_running(port: int = PORT) -> bool:
    """True if a vgdb is already serving on this port."""
    with socket.socket() as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    if instance_running():
        print(f"vgdb is already running, opening {ADDRESS}")
        webbrowser.open(ADDRESS)
        return

    archive = store.archive_path()
    print(f"Archive: {archive}")
    print(f"vgdb on {ADDRESS} — Ctrl+C to stop")

    threading.Timer(0.5, webbrowser.open, [ADDRESS]).start()
    create_app(archive).run(host="127.0.0.1", port=PORT)
