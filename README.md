# Portable Skills

A personal, repo-independent set of engineering personas for Claude Code.
They travel with you (user-level skills), read each repo's real docs and rules
via a small per-repo map, and leave zero footprint in any repo's git tree.

## The roster

The folders under `skills/` are the source of truth — every folder is one
skill. Call personas by name ("Winston, is this the right approach?") or by
slash command (`/winston`, `/clove`, ...). Two invocation verbs: bare-name
address hands the conversation over; "send out <persona> to <task>" dispatches
a background agent (see the persona-dispatch rule in your user-level
`CLAUDE.md`).

**Dev workflow:** winston (architecture + plans), sasha (debugging, never
fixes), clove (implementation + shipping), briar (self-review, chat only),
eric (PR review, never approves/merges), eli (docs), nora (ticket setup),
mira (user stories), parker (PRDs), pixel (design),
reese (QA test plans + AC verification), sage (changelog), lilac (standup),
iris (retros), theo (architect-doc walker), ren (refactor scout),
zoe (surface audit).

**Orchestration:** sol — the conductor; dispatches the roster, pauses at every
human gate, tracks runs in `<plans>/conductor/`; never writes code or merges.

**Business layer:** vera (strategy, owns `<plans>/business/strategy.md`),
kora (market research), ellis (finance), charlie (marketing), quinn (sales,
never sends outreach), tess (data/metrics), remy (customer success),
penny (recruiting), lex (legal — never legal advice).

**Utilities (no persona):** handoff (compact a session into a resumable
document), review-loop (the briar → clove → eric gauntlet).

## Install

Clone the repo, then copy every folder under `skills/` into your Claude
profile's skills directory — `~/.claude/skills` for most people:

```bash
git clone <repo-url> portable-skills
cd portable-skills
mkdir -p ~/.claude/skills
cp -R skills/* ~/.claude/skills/
```

Two things the copy must get right:

- **`skills/_shared/` has to come along.** `_shared/core.md` is the roster's
  shared operating system — repo map, plan files, orientation batteries,
  house rules. Every persona reads it as Step 0, so a roster installed
  without it runs on a degraded failsafe. The `cp -R skills/*` above includes
  it; if you cherry-pick individual personas, copy `_shared/` too.
- **Copies don't self-update.** There are no symlinks — after `git pull`
  brings in roster changes (or after you edit your clone), re-run the copy.
  Until you do, your profile keeps running the old version.

User-level skills load in **every** repo you open with that profile and live
in **no** repo's tree.

### The owner's sync script

`sync.sh` in the repo root is the owner's personal install path: it copies the
roster into two profiles (`~/.claude/skills` and `~/.claude-work/skills`) and
keeps a backup under `~/Downloads/`, and it references a plan file at a
hardcoded `~/worklogs/...` path that won't exist on your machine — so run
as-is it will fail partway. Treat it as a reference, not a turnkey installer:
either trim it to the copy loop for your own profile dir, or just use the
manual `cp -R` above. Its one design point worth keeping if you adapt it:
per-skill copy with no `--delete` semantics against the profile dirs, so
skills you keep only in your profile survive a re-sync.

## Per-repo setup (five minutes, once per repo)

1. Copy `repo-map.template.md` to the repo root as `.repo-map.md` and fill in
   where that repo keeps its architect docs, rules, docs, lessons, and where
   you want plan files to go (can be outside the repo, e.g. `~/worklogs/<repo-name>/plans/`).
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

## Alongside a repo's own persona skills

Some repos ship their own skill set, and those skills may carry the same
persona names — a repo-level skill with its own id (say `acme-architect`)
whose routing rules claim "Winston", or a roster that has its own "clove".
When both layers are installed, the name and the skill stop being the same
thing. The rules:

- **Bare names are ambiguous.** Saying "Winston, is this the right approach?"
  routes by name, and the repo's own routing rules can claim that name — so
  in such a repo, a bare name may load the repo's version instead of the
  portable one. Neither outcome is wrong; you just can't tell from the name
  alone.
- **Slash commands are exact.** `/winston`, `/clove`, `/eric` target a skill
  by its id, so they always load the portable version. When it matters which
  one you get, use the slash command.
- **The repo's skills stay reachable the same way** — via their own ids
  (`/acme-architect`, `/acme-code-dev`). Installing this roster hides
  nothing; it only adds a second claimant for the bare names.
- **You can set a default.** A one-line routing preference in your user-level
  `CLAUDE.md` (e.g. `~/.claude/CLAUDE.md`: "when a bare persona name matches
  both a portable skill and a repo skill, prefer the portable one") makes
  bare names resolve your way without per-invocation slash commands. The
  repo's skills remain a slash command away.

## Caveats

- These files are a **snapshot port**, decoupled from the toolkit repo they
  were extracted from. Edits you make here are the source of truth for this
  roster — nothing regenerates them.
- Plans use a simplified plan-file shape (goal / tasks / decisions / history /
  sessions / issues). Point `plans:` in the repo map wherever you want them
  kept. The `## Sessions` section holds each session's orientation-battery
  answers (open + close) — private tooling state, never the host repo's concern.

## Roadmap

- Roster is complete (dev workflow + sol + business + utilities, all on
  `_shared/core.md`). Excluded on purpose: onboarding/install personas
  (Atlas, skill-forge) — they configure a specific toolkit repo and have no
  meaning as portable skills.
- Re-run the copy (`cp -R skills/* ~/.claude/skills/`, or your trimmed
  `sync.sh`) after adding or editing personas — copies don't self-propagate.
- If long sessions still drift despite the re-anchors, a user-level
  PostToolUse hook is the mechanical backstop — layer it on, don't replace
  the skill-level instructions.
