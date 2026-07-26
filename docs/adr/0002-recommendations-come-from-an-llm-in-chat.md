# Recommendations come from an LLM in chat, not from the application

No code computes which game to play next: the owner opens Claude Code in this folder, the LLM reads `games.json` and answers conversationally. The original design called for an expected score derived from the historical average rating per genre, abandoned because that average is a poor stand-in for reasoning — it cannot tell "you don't like the genre" from "you can't stand 80-hour games", whereas an LLM reading the notes can. A recommendation is also conversational by nature: the first answer is rarely the right one, and you want to be able to push back with "I've only got ten hours free".

## Considered Options

- **A "Recommend" button calling the Claude API** — rejected: it needs an API key and cost management for a personal tool, and it reduces a conversation to a single-shot oracle.
- **A "Copy prompt" button** — rejected: zero infrastructure, but a manual step on every question.

## Consequences

Two consequences that explain otherwise suspicious absences in the code. First, **there are no tags or genres** in the schema — whoever produces the recommendation already knows the catalogue, so asking the owner for them would be manual work for data already available. Second, **there is no wishlist** — candidates come from the whole world, not from a list the owner curated, which could only be reordered and would limit recommendations to what they already had in mind.

The value of the archive shifts accordingly from the ratings to the **notes**: an isolated `8` is nearly mute, `8 — great combat but 40 hours of filler` is what makes a recommendation good.
