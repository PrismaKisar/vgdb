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

async function remove(title) {
  await fetch(`/api/games/${encodeURIComponent(title)}`, { method: "DELETE" });
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
  // The server identifies a game by its title, so a rename has to say which
  // entry it replaces — otherwise it would add a second one.
  let storedTitle = game.title;

  const fields = {
    title: field(game.title),
    rating: field(game.rating, { type: "number", min: 1, max: 10, step: 0.5 }),
    notes: field(game.notes, { placeholder: "—" }),
  };
  const inputs = Object.values(fields).map((f) => f.input);

  async function apply() {
    const title = fields.title.input.value.trim();
    try {
      await put(title, { ...readFields(fields), previousTitle: storedTitle });
      storedTitle = title;
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

  const button = document.createElement("button");
  button.textContent = "×";
  button.title = "Rimuovi dall'archivio";
  button.addEventListener("click", async () => {
    if (!confirm(`Rimuovere "${storedTitle}" dall'archivio?`)) return;
    await remove(storedTitle);
    tr.remove();
  });
  const actions = document.createElement("td");
  actions.append(button);

  tr.append(fields.title.cell, fields.rating.cell, fields.notes.cell, actions);
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

const draft = {
  title: document.getElementById("draft-title"),
  rating: document.getElementById("draft-rating"),
  notes: document.getElementById("draft-notes"),
};

async function add() {
  const title = draft.title.value.trim();
  if (!title) return;
  const rating = draft.rating.value === "" ? null : Number(draft.rating.value);
  try {
    await put(title, { rating, notes: draft.notes.value.trim() });
  } catch (error) {
    draft.rating.classList.add("invalid");
    draft.rating.title = error.message;
    return;
  }
  Object.values(draft).forEach((input) => {
    input.value = "";
    input.classList.remove("invalid");
  });
  draft.title.focus();
  await reload();
}

document.getElementById("add").addEventListener("click", add);
Object.values(draft).forEach((input) =>
  input.addEventListener("keydown", (e) => e.key === "Enter" && add()),
);

reload();
