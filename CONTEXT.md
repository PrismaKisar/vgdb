# vgdb

A personal archive of videogames played and the judgements passed on them. It exists for one purpose: to give an LLM the material to recommend the next game to play. It is not a catalogue or a library — it is a record of taste.

## Language

**Archive** → `archive`:
The whole record of played games, and the only place a **Game** is written. It owns what a Game has to satisfy to be in it — a **Rating** on the scale, a title that names it — so the rules hold whichever writer is running: the page, the cover scripts, or the LLM. That it is a JSON file is incidental; see [ADR-0001](./docs/adr/0001-json-instead-of-a-database.md).
_Avoid_: store, database, collection, library

**Game** → `game`:
A videogame the owner has already played, together with the judgement they gave it.
_Avoid_: title, entry, record

**Rating** → `rating`:
How much the game was **enjoyed**, on a 1-10 scale — not how well made it is.
_Avoid_: score, quality, objective assessment

**Notes** → `notes`:
Free text on why the game was enjoyed or not. Also carries the outcome (e.g. "dropped it after two hours").
_Avoid_: comment, review, description

**Platinum** → `platinum`:
Whether the platinum trophy was earned (`true`), attempted and missed (`false`), or — when the field is absent — that the game has no platinum at all. The three states are deliberately distinct: "I didn't get it" says something about the player, "it doesn't exist" says nothing.
_Avoid_: completed, 100%, trophies

**Feeling**:
What a game leaves behind when you finish it or switch the console off — how much it makes you say "wow" or "this doesn't work". A judgement of the whole, not a technical aspect: it covers both how the controls respond ("the jump physics are broken") and the atmosphere ("a feeling that's genuinely hard to find"). **It is the main lever behind the Rating.**
_Avoid_: game feel, gameplay, atmosphere (each is a part of this, not a synonym)

**Recalibration**:
The sitting where the owner rereads the existing ratings ordered against each other and corrects them for consistency. A recurring operation, not a one-off.

**Recommendation**:
The LLM's answer to "what should I play next?", produced by reading the whole archive in a chat. It is not computed by code and it is not stored. It only concerns **authored games**: the owner will never ask for a recommendation about a sports title or an annual shooter, even though well-rated ones sit in the archive.
_Avoid_: suggestion, automatic recommendation, prediction

## Relationships

- The **Archive** holds every **Game**, and a Game exists only inside it
- A **Game** has exactly one **Rating** and, optionally, **Notes**, a **Platinum** and a cover (`title`, `rating`, `notes`, `platinum`, `cover`)
- A **Recommendation** draws on every **Game** but produces none: recommended games do not enter the archive until they have been played
- **Recalibration** changes existing **Ratings**, never the **Games**

## How to read the ratings

Habits of the owner, without which the archive is read wrongly:

- **Games are chosen in advance**, knowing what to expect, so they are almost always finished. The absence of dropped games does not mean everything was enjoyed: it means the filtering happens before buying. The **real floor is around 5.5**, not 1 — a 6 is their "disappointing".
- **The platinum is the default, not an obligation.** It is pursued on everything unless prohibitive; hard platinums are no deterrent (both Hollow Knights), insane ones are (Crash 4 refused, Super Meat Boy left incomplete). It follows that **length is a structural risk**: a mediocre game does not merely bore them, it costs them dozens of hours because they complete it anyway.
- **Only remakes and remasters get played** where they exist. Great sensitivity to mechanics that *feel* dated — not to a game's age: BioShock (2007) scores 9 precisely because "it never makes you feel its almost 20 years", while Spyro 1, Crash 1 and Uncharted 1 are the lowest of their respective series for old mechanics.
- **Being a fan of a series is worth about half a point.** Hogwarts Legacy at 8.5 would be an 8 without the fandom: "cool" instead of "wow".
- **Large maps are not a problem, infinite ones are.** Ubisoft-style open worlds are an explicit like — handcrafted map, structured progression, characters (Assassin's Creed Syndicate 8.5, Ghost of Yotei 9, Far Cry 4 8.5); endless procedural generation is not (No Man's Sky 7.5).
- **Being forced online to *play* costs rating; online trophies only cost the platinum.** Two different things, kept apart. A game playable only while connected is penalised on the **Rating** (Need for Speed 2015: "you can only play connected: bad, bad"). When it is the **Platinum** that demands online trophies, the game itself does not suffer: Uncharted 4 sits at 9 and is "a masterpiece" while being the only platinum ever given up — "I wouldn't have wanted to miss a game like that". **So an online platinum is never a reason to advise against a game.** No aversion to multiplayer as such: Black Ops III scores 9 precisely because of it.

## Example dialogue

> **Dev:** "If I recommend Silksong and you buy it, do I add it to the archive as *to play*?"
> **Owner:** "No. The archive holds only what I've already played. If I buy it and finish it, then it becomes a **Game** with a **Rating**."
> **Dev:** "And if I drop it halfway?"
> **Owner:** "Give it a low **Rating** anyway and write it in the **Notes**. Those are the cases you need most."

## Flagged ambiguities

- "rating" could have meant *quality of the game* or *how much I enjoyed it* — resolved: it means **how much I enjoyed it**. Disagreements with the critics are information, not mistakes.
- "database" suggested something queryable — resolved: it is a JSON file. See [ADR-0001](./docs/adr/0001-json-instead-of-a-database.md).
- an `outcome` field (finished/dropped) and **hours** played were planned — dropped: that information lives in the **Notes** when it matters.
- a system of genre **tags** was planned — dropped: genres are obvious from the title to whoever produces the **Recommendation**, so tagging would be manual work for data already known.
- a `date` field was planned — dropped after the first import: none of the entries carried one, and a permanently empty field is worse than no field.
- "**finished**" is not the bar for entering the archive: having played enough to hold an opinion is enough. Super Meat Boy is in with 30+ hours despite being incomplete; Crash 3 is not, because it has not been played.
- **Feeling** looked like it split into two separate levers (control response vs atmosphere) — resolved: for the owner it is one single, whole judgement.
