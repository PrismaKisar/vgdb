# A JSON file instead of a database

The archive is a single `games.json` indented with 2 spaces, not SQLite — despite the project being called "vgdb". The dataset runs to a few hundred rows over the project's whole life, so nothing SQL exists for (indexes, joins, concurrent transactions) is needed; meanwhile there are two writers, the LLM and the web app, and plain text makes reading it a single operation for the LLM instead of a call out to `sqlite3`, besides keeping the data inspectable by eye and versionable with git.

## Considered Options

- **SQLite** — rejected: a binary format, so every read or write by the LLM goes through hand-assembled SQL. An access cost paid for robustness that is not needed at this scale.
- **Markdown** — rejected: the most readable for a human, but the web app would have to parse *and* re-serialise on every save, with a real risk of mangling the formatting. With two writers the round-trip has to be exact.

## Consequences

The file lives at `~/.vgdb/games.json` and the path is **absolute**, resolved from `VGDB_FILE` with that default: `vgdb` is installed globally and is meant to run from any directory, so a path relative to the working directory would silently produce empty archives. The same variable lets the tests run against a temporary file.

The path was originally inside the repository, to get a git history of the judgements for free; it moved out when the repository went public — see [ADR-0003](./0003-personal-data-lives-outside-the-repo.md).
