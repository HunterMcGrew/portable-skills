# Portable Skills

A personal, repo-independent set of engineering personas for Claude Code.
They travel with you (user-level skills), read each repo's real docs and rules
via a small per-repo map, and leave zero footprint in any repo's git tree.

## The roster

The folders under `skills/` are the source of truth — every folder is one
skill. Call personas by name ("Winston, is this the right approach?") or by
slash command (`/winston`, `/clove`, ...). Two invocation verbs: bare-name
address hands the conversation over; "send out <persona> to <task>" dispatches
a background agent (see the persona-dispatch rule in `~/.claude-work/CLAUDE.md`).

**Dev workflow:** winston (architecture + plans), sasha (debugging, never
fixes), clove (implementation + shipping), briar (self-review, chat only),
eric (PR review, never approves/merges), eli (docs), nora (ticket setup),
mira (user stories), parker (PRDs), pixel (design), reese (QA test plans),
sage (changelog), lilac (standup), iris (retros), theo (architect-doc walker),
ren (refactor scout), zoe (surface audit).

**Orchestration:** sol — the conductor; dispatches the roster, pauses at every
human gate, tracks runs in `<plans>/conductor/`; never writes code or merges.

**Business layer:** vera (strategy, owns `<plans>/business/strategy.md`),
kora (market research), ellis (finance), charlie (marketing), quinn (sales,
never sends outreach), tess (data/metrics), remy (customer success),
penny (recruiting), lex (legal — never legal advice).

**Utilities (no persona):** handoff (compact a session into a resumable
document), review-loop (the briar → clove → eric gauntlet).

## Install

This folder (`~/Documents/portable-skills`) is the canonical copy — the only
place to edit, kept under git. `sync.sh` pushes real copies of every skill
folder to both Claude profiles (`~/.claude/skills`, `~/.claude-work/skills`)
and a backup at `~/Downloads/portable-skills-backup/`:

```bash
~/Documents/portable-skills/sync.sh
```

No symlinks anywhere — copies don't propagate on their own, so re-run
`sync.sh` after any edit. Profile-only skills (folders with no counterpart
here) are never touched by the sync.

The `_shared/core.md` file is the roster's shared operating system — repo map,
plan files, orientation batteries, re-anchors, context budget, house rules.
Every skill reads it as Step 0; edit it once and every persona picks up the
change. Persona SKILL.md files carry only persona-specific content.

User-level skills load in **every** repo you open with that profile and live
in **no** repo's tree. (If your normal profile is `~/.claude`, use that path
instead.)

## Per-repo setup (five minutes, once per repo)

1. Copy `repo-map.template.md` to the repo root as `.repo-map.md` and fill in
   where that repo keeps its architect docs, rules, docs, lessons, and where
   you want plan files to go (can be outside the repo, e.g. `~/worklogs/thrive/plans/`).
2. Keep it out of the repo's git with a **global** gitignore (never edits the
   repo's own `.gitignore`):

```bash
git config --global core.excludesFile ~/.gitignore_global
printf '.repo-map.md\n' >> ~/.gitignore_global
```

**Prefer the interview over hand-filling.** In a new repo's first session, invoke
any persona and say "no repo map yet — interview me." The skill runs a discovery
pass, asks you to confirm where each role lives (rules, architect docs, docs,
lessons, plans, verification), and writes `.repo-map.md` itself. Front-loading
this interview beats mid-task questions — make it the first thing you do in a
new repo. Roles you leave out are opt-outs (no `lessons` line → no lesson
capture), and skills will offer to append locations they discover mid-session
back into the map.

## How work leaves the repo

Edits the personas make to the repo's own files (their rules, their
lessons.md, their docs) are just your work — they ship through your normal
branch → PR flow. The tooling itself is never installed in, or committed to,
the repo.

## Caveats

- **Don't open the PRISM repo with these installed** (or expect duplicates if
  you do) — PRISM's repo-level skills carry the same persona names, and two
  Winstons make name-routing ambiguous. Everywhere else there's exactly one.
- **Repos with their own persona skills route names to their own skills.** If a
  repo's skills or routing rules claim a persona name (e.g. Thrive's
  `thrive-architect` claims "Winston"), bare-name invocation may load the repo's
  version instead of yours. Two-layer fix: a routing preference in
  `~/.claude-work/CLAUDE.md` makes bare names default to the portable skills,
  and the slash command (`/winston`, `/sasha`, ...) is the guaranteed path —
  it targets the skill by exact id. The repo's own skills stay reachable via
  their own commands (`/thrive-architect`).
- These files are a **snapshot port**, decoupled from PRISM's build. Edits you
  make here are the source of truth for this roster — nothing regenerates them.
- Plans use a simplified plan-file shape (goal / tasks / decisions / history /
  sessions / issues). Point `plans:` in the repo map wherever you want them
  kept. The `## Sessions` section holds each session's orientation-battery
  answers (open + close) — private tooling state, never the host repo's concern.

## Roadmap

- Roster is complete (dev workflow + sol + business + utilities, all on
  `_shared/core.md`). Excluded on purpose: onboarding/install personas
  (Atlas, skill-forge) — they configure a specific toolkit repo and have no
  meaning as portable skills.
- Re-run `sync.sh` after adding or editing personas — copies don't
  self-propagate.
- If long sessions still drift despite the re-anchors, a user-level
  PostToolUse hook is the mechanical backstop — layer it on, don't replace
  the skill-level instructions.
