"use strict";

const tbody = document.getElementById("games");
const count = document.getElementById("count");
const empty = document.getElementById("empty");

async function fetchGames() {
  const response = await fetch("/api/games");
  return response.json();
}

async function put(title, game) {
  const response = await fetch(`/api/games/${encodeURIComponent(title)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(game),
  });
  if (!response.ok) {
    const { error } = await response.json().catch(() => ({}));
    throw new Error(error || "Salvataggio fallito");
  }
}

function field(value, options = {}) {
  const input = document.createElement("input");
  input.value = value ?? "";
  Object.assign(input, options);
  const cell = document.createElement("td");
  cell.append(input);
  return { input, cell };
}

/** The edited values of one row, in the shape the API expects. */
function readFields({ rating, notes }) {
  return {
    rating: rating.input.value === "" ? null : Number(rating.input.value),
    notes: notes.input.value.trim(),
  };
}

function row(game) {
  const tr = document.createElement("tr");
  const fields = {
    title: field(game.title),
    rating: field(game.rating, { type: "number", min: 1, max: 10, step: 0.5 }),
    notes: field(game.notes, { placeholder: "—" }),
  };
  const inputs = Object.values(fields).map((f) => f.input);

  async function apply() {
    try {
      await put(fields.title.input.value.trim(), readFields(fields));
      inputs.forEach((input) => input.classList.remove("invalid"));
    } catch (error) {
      fields.rating.input.classList.add("invalid");
      fields.rating.input.title = error.message;
    }
  }

  for (const input of inputs) {
    input.addEventListener("change", apply);
    input.addEventListener("keydown", (e) => e.key === "Enter" && input.blur());
  }

  tr.append(fields.title.cell, fields.rating.cell, fields.notes.cell);
  return tr;
}

async function reload() {
  const games = await fetchGames();
  // Sorted by rating once, on load: re-sorting after every edit would make
  // rows jump out from under the cursor during a recalibration pass.
  games.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
  tbody.replaceChildren(...games.map(row));
  count.textContent = games.length ? `${games.length} giochi` : "";
  empty.hidden = games.length > 0;
}

reload();
