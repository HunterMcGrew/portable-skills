# Repo Map

This file tells my personal skills where this repo keeps its durable content.
It is personal tooling config — globally gitignored, never committed to this repo.

Copy this file to the repo root as `.repo-map.md` and fill in the real paths —
or have any persona interview you and write it (say "no repo map yet — interview me").
Delete any role the repo doesn't have — a missing role is an opt-out (no `lessons`
line means personas skip lesson capture). Skills ask before writing anywhere the
map doesn't name, and will offer to append newly-discovered locations back here.

## Roles

- **architect docs**: `docs/architecture/` — durable architecture and design decisions (read by Winston, Clove, Briar, Eric; written by Winston)
- **rules**: `docs/engineering-standards/` — engineering standards and conventions (read by everyone)
- **docs**: `docs/` — feature and usage documentation (read/written by Eli)
- **lessons**: `docs/lessons.md` — corrections captured as one-line patterns (appended by any persona after a user correction)
- **plans**: `~/worklogs/<repo-name>/plans/` — living plan files, one per ticket (written by Winston, Sasha, Clove, Briar). There is always exactly one plan per ticket; this line decides where it lives. Point it at the repo's own plans directory if the team keeps one (skills then write the real branch plan — note `## Sessions` will appear in committed plans and PR diffs), or outside the repo / at a globally-gitignored folder to keep plans fully private.
- **verification**: `pnpm test && pnpm build` — the command(s) that prove a change works (run by Clove and Briar before calling anything done)

## Notes (optional)

Anything else the skills should know about this repo — ticket ID format
(e.g. THRIVE-1234), branch naming, who reviews what, quirks.

- Ticket format:
- Branch format:
