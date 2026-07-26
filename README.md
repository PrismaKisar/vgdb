# vgdb — videogame database

A personal archive of the videogames you have played, and of what you thought of
them. It exists to answer one question — **"what should I play next?"** — by
giving an LLM the material for a real recommendation instead of a generic one.

The program computes nothing. You open an LLM session in this folder, it reads
your archive, and you talk it through: an average rating per genre cannot tell
*"I don't like RPGs"* apart from *"I can't take 80-hour games"*, whereas reading
the notes can. What `vgdb` provides is the part a chat does badly and a table
does well — **looking at the archive and correcting it**.

## Quick start

```sh
uv tool install --editable .   # once
vgdb                           # opens http://127.0.0.1:5757/
```

The command serves the page in the foreground and opens the browser; `Ctrl+C`
stops it. Running `vgdb` again while an instance is already up simply reopens
the browser instead of failing on the busy port.

## The table

Every cell is editable in place and saves on its own — no forms, no save button,
since correcting a rating is the operation you perform most. Rows are sorted by
rating on load and stay put afterwards, so nothing jumps out from under the
cursor while you work. The search box filters by title, and the counter shows
how many rows are visible out of the total.

Covers are set by dropping an image on the thumbnail, or by clicking it. The
platinum cell cycles through its three states with a click.

## The archive

One JSON file, an array of objects, documented by
[`games.example.json`](games.example.json):

| Field | Type | Meaning |
| --- | --- | --- |
| `title` | string | Identifies the game; matched ignoring case and outer spaces. Required. |
| `rating` | number | 1 to 10, half points allowed. How much you enjoyed it. |
| `notes` | string | Optional, and the reason the archive is worth anything: `8` alone says little, `8 — great combat but 40 hours of filler` is usable. |
| `platinum` | boolean | `true` won, `false` missed, absent when there is no platinum or you don't remember. |
| `cover` | string | Image file name under `covers/`. Managed by the app. |

It lives in `~/.vgdb/` — the archive as `games.json`, the artwork in `covers/` —
**deliberately outside this repository**, which is public while the ratings are
personal.

## Covers

`scripts/fetch_covers.py` pulls artwork from SteamGridDB, which offers square art
and indexes console exclusives. It needs a free API key (steamgriddb.com →
Preferences → API). Without one it falls back to Steam, which requires no
authentication but only has 2:3 posters and no PlayStation exclusives.

```sh
uv run scripts/fetch_covers.py                            # only the missing ones
uv run scripts/fetch_covers.py --force                    # re-fetch everything
uv run scripts/set_cover.py "Cuphead" <link-or-id-or-url>  # one specific cover
```

Titles are matched fuzzily and anything below a confidence floor is reported
rather than guessed, so a wrong cover is never attached silently. Images are
stored as WebP scaled to 192px on the longest side: a few KB each, with no
visible difference at the size they are displayed.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `VGDB_FILE` | `~/.vgdb/games.json` | Archive location. |
| `VGDB_SGDB_KEY` | — | SteamGridDB API key, read from the environment or from an untracked `.env`. |

## Development

```sh
uv sync
uv run pytest
```

The suite covers the two public seams — the `store` module and the HTTP API —
plus the cover pipeline and the scripts. The page logic
(`vgdb/static/app.js`) has no build step and is verified by hand.
