# vgdb — videogame database

A personal archive of the videogames you have played and what you thought of them.
It is not a catalogue or a library: it exists to **answer the question "what should
I play next?"**, by giving an LLM the material to make a real recommendation
instead of a generic one.

The program does not compute the recommendation. You open Claude Code in the
folder, the LLM reads `games.json` and you talk it through — because an average
rating per genre cannot tell "I don't like RPGs" apart from "I can't take
80-hour games", while reading the notes can. The program only exists to **look at
and correct** the archive, which is the thing a table does well and a chat does
terribly.

## How it works

One command, `vgdb`, opens a table in your browser that is editable in place:
title, rating from 1 to 10, platinum trophy, and notes. The notes are the field
that matters — an `8` on its own says little, `8 — great combat but 40 hours of
filler` is what makes the archive useful.

```
uv tool install --editable .   # once
vgdb                           # opens http://127.0.0.1:5757/
```

Running `vgdb` again while it is already up just reopens the browser.

## Where the data lives

In `~/.vgdb/`: the `games.json` archive and the cover images in `covers/`.
**Deliberately outside this repository**, because it is public and the ratings are
personal. The format is documented by [`games.example.json`](games.example.json).

Set `VGDB_FILE` to keep it somewhere else.

## Covers

`scripts/fetch_covers.py` pulls artwork from SteamGridDB, which has square art and
indexes console exclusives too. It needs a free API key (steamgriddb.com →
Preferences → API) in `VGDB_SGDB_KEY`, either in the environment or in an
untracked `.env` file. Without a key it falls back to Steam, which needs no
authentication but only offers 2:3 posters and no PlayStation exclusives.

```
uv run scripts/fetch_covers.py                          # only the missing ones
uv run scripts/set_cover.py "Cuphead" <link-or-id-or-url>   # one specific cover
```

Images are scaled to 192px on their longest side as WebP: a few KB each, and no
visible difference at the size they are shown.

## Development

```
uv sync
uv run pytest
```

The tests cover the two public seams, the `store` module and the HTTP API. The
page logic (`vgdb/static/app.js`) is verified by hand.
