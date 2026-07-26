# Personal data lives outside the repository

The archive (`games.json`) and the covers live in `~/.vgdb/`, not in the project folder, and the repository carries a `games.example.json` with four invented entries in their place. The repository is public and the archive is a record of personal taste: keeping it inside would mean publishing it, and leaving that separation to `.gitignore` alone means one absent-minded `git add -f` exposes it.

## Consequences

The benefit ADR-0001 explicitly cited is lost: the git history of how judgements change over time. It can be recovered at will by making `~/.vgdb/` **a second, private repository**, independent of this one.

`.gitignore` still excludes `games.json` and `covers/` as a second barrier, in case a real archive ever lands in the project folder by accident.

Anyone cloning the repository finds no archive: on first run `vgdb` creates an empty one in `~/.vgdb/`, and `games.example.json` documents the format.
