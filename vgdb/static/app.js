"use strict";

const tbody = document.getElementById("games");
const search = document.getElementById("search");
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

async function uploadCover(title, file) {
  const payload = new FormData();
  payload.append("file", file);
  const response = await fetch(`/api/games/${encodeURIComponent(title)}/cover`, {
    method: "POST",
    body: payload,
  });
  if (!response.ok) {
    const { error } = await response.json().catch(() => ({}));
    throw new Error(error || "Caricamento copertina fallito");
  }
  return response.json();
}

// The real PlayStation platinum trophy, stored locally so the page keeps
// working offline and does not lean on someone else's bandwidth.
const TROPHY = `<img class="trophy" src="/static/platinum.webp" alt="">`;

// Three states, cycled by clicking: won, missed, no platinum exists.
const PLATINUM = [
  { value: null, mark: "–", label: "Nessun platino / non lo so", css: "none" },
  { value: true, mark: TROPHY, label: "Platino ottenuto", css: "won" },
  { value: false, mark: TROPHY, label: "Platino non ottenuto", css: "missed" },
];

/** A trophy toggle. Calls back with the new state so the row can save it. */
function platinumCell(game, onChange) {
  const cell = document.createElement("td");
  cell.className = "platinum-cell";
  const button = document.createElement("button");

  let index = PLATINUM.findIndex((s) => s.value === (game.platinum ?? null));

  function paint() {
    const state = PLATINUM[index];
    button.innerHTML = state.mark;
    button.title = state.label;
    button.className = `platinum ${state.css}`;
  }

  button.addEventListener("click", () => {
    index = (index + 1) % PLATINUM.length;
    paint();
    onChange(PLATINUM[index].value);
  });

  paint();
  cell.append(button);
  return cell;
}

/** A cover slot: click to pick a file, or drop one onto it. */
function coverCell(game, titleNow) {
  const cell = document.createElement("td");
  const slot = document.createElement("label");
  slot.className = "cover";
  slot.title = "Trascina qui un'immagine, o clicca per sceglierla";

  const picture = document.createElement("img");
  picture.alt = "";
  picture.hidden = !game.cover;
  if (game.cover) picture.src = `/covers/${encodeURIComponent(game.cover)}`;

  const chooser = document.createElement("input");
  chooser.type = "file";
  chooser.accept = "image/*";
  chooser.hidden = true;

  async function send(file) {
    if (!file) return;
    slot.classList.add("busy");
    try {
      const saved = await uploadCover(titleNow(), file);
      // The name is stable, so bust the browser cache on replacement.
      picture.src = `/covers/${encodeURIComponent(saved.cover)}?v=${Date.now()}`;
      picture.hidden = false;
    } catch (error) {
      slot.title = error.message;
    } finally {
      slot.classList.remove("busy");
    }
  }

  chooser.addEventListener("change", () => send(chooser.files[0]));
  slot.addEventListener("dragover", (e) => {
    e.preventDefault();
    slot.classList.add("hovered");
  });
  slot.addEventListener("dragleave", () => slot.classList.remove("hovered"));
  slot.addEventListener("drop", (e) => {
    e.preventDefault();
    slot.classList.remove("hovered");
    send(e.dataTransfer.files[0]);
  });

  slot.append(picture, chooser);
  cell.append(slot);
  return cell;
}

function field(value, { tag = "input", cellClass, ...options } = {}) {
  const input = document.createElement(tag);
  input.value = value ?? "";
  Object.assign(input, options);
  const cell = document.createElement("td");
  if (cellClass) cell.className = cellClass;
  cell.append(input);
  return { input, cell };
}

/** Grow a notes box to fit its text: the notes are why the archive is useful. */
function fitToText(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${textarea.scrollHeight}px`;
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
    title: field(game.title, { cellClass: "title-cell" }),
    rating: field(game.rating, { type: "number", min: 1, max: 10, step: 0.5 }),
    notes: field(game.notes, {
      tag: "textarea",
      cellClass: "notes-cell",
      rows: 1,
      placeholder: "Perché ti è piaciuto, o perché no…",
    }),
  };
  const inputs = Object.values(fields).map((f) => f.input);

  fields.notes.input.addEventListener("input", () => fitToText(fields.notes.input));

  let platinum = game.platinum ?? null;

  async function apply() {
    const title = fields.title.input.value.trim();
    try {
      await put(title, { ...readFields(fields), platinum, previousTitle: storedTitle });
      storedTitle = title;
      inputs.forEach((input) => input.classList.remove("invalid"));
    } catch (error) {
      fields.rating.input.classList.add("invalid");
      fields.rating.input.title = error.message;
    }
  }

  for (const input of inputs) {
    input.addEventListener("change", apply);
    // Enter commits a one-line field, but inside the notes it means a new line.
    if (input.tagName !== "TEXTAREA") {
      input.addEventListener("keydown", (e) => e.key === "Enter" && input.blur());
    }
  }

  const button = document.createElement("button");
  button.textContent = "×";
  button.title = "Rimuovi dall'archivio";
  button.addEventListener("click", async () => {
    if (!confirm(`Rimuovere "${storedTitle}" dall'archivio?`)) return;
    await remove(storedTitle);
    tr.remove();
    updateCount();
  });
  const actions = document.createElement("td");
  actions.append(button);

  const cover = coverCell(game, () => storedTitle);
  const trophy = platinumCell(game, (state) => {
    platinum = state;
    apply();
  });

  tr.append(
    cover,
    fields.title.cell,
    fields.rating.cell,
    trophy,
    fields.notes.cell,
    actions,
  );
  return tr;
}

/** Visible out of total, so an active filter is never mistaken for an empty archive. */
function updateCount() {
  const rows = [...tbody.children];
  const shown = rows.filter((tr) => !tr.hidden);
  count.textContent = rows.length
    ? `${shown.length}${shown.length === rows.length ? "" : ` / ${rows.length}`} giochi`
    : "";
  empty.hidden = rows.length > 0;
}

function filter() {
  const term = search.value.trim().toLowerCase();
  for (const tr of tbody.children) {
    // Explicitly the title field, so further columns cannot break the filter.
    const title = tr.querySelector(".title-cell input").value.toLowerCase();
    tr.hidden = term !== "" && !title.includes(term);
  }
  updateCount();
}

search.addEventListener("input", filter);

async function reload() {
  const games = await fetchGames();
  // Sorted by rating once, on load: re-sorting after every edit would make
  // rows jump out from under the cursor during a recalibration pass.
  games.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
  tbody.replaceChildren(...games.map(row));
  // scrollHeight only means something once the rows are in the document.
  tbody.querySelectorAll("textarea").forEach(fitToText);
  filter();
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
