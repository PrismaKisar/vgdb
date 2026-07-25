"use strict";

const tbody = document.getElementById("games");
const count = document.getElementById("count");
const empty = document.getElementById("empty");

async function fetchGames() {
  const response = await fetch("/api/games");
  return response.json();
}

function cell(value, className) {
  const td = document.createElement("td");
  td.textContent = value ?? "—";
  if (className) td.className = className;
  return td;
}

function row(game) {
  const tr = document.createElement("tr");
  tr.append(
    cell(game.title, "title-cell"),
    cell(game.rating, "rating-cell"),
    cell(game.notes, "notes-cell"),
  );
  return tr;
}

async function reload() {
  const games = await fetchGames();
  games.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
  tbody.replaceChildren(...games.map(row));
  count.textContent = games.length ? `${games.length} giochi` : "";
  empty.hidden = games.length > 0;
}

reload();
