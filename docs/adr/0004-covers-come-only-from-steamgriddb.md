# Covers come only from SteamGridDB

`fetch_covers.py` used to fall back to Steam's keyless store API when no SteamGridDB key was configured, so the script would always produce something. That fallback only served 2:3 posters, missed every console exclusive, and picked artwork the user did not choose. SteamGridDB is the archive owner's actual source for cover art, in every other tool built around it.

The Steam fallback is removed. `fetch_covers.py` now requires `VGDB_SGDB_KEY` and refuses to run without it, rather than silently substituting worse artwork from a different source.

## Consequences

Running the script without a key is now a hard stop (exit code 2) instead of a degraded run. `set_cover.py` was already SteamGridDB-only and needed no change.
