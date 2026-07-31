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
  shared operating system — everything a persona relies on that isn't
  specific to it. Every persona reads it as Step 0, so a roster installed
  without it runs on a degraded failsafe. Its sibling `_shared/verification.md`
  is loaded only by the personas that grade something (reviewers, QA, audits).
  The `cp -R skills/*` above includes both; if you cherry-pick individual
  personas, copy `_shared/` too.
- **Copies don't self-update.** There are no symlinks — after `git pull`
  brings in roster changes (or after you edit your clone), re-run the copy.
  Until you do, your profile keeps running the old version.

User-level skills load in **every** repo you open with that profile and live
in **no** repo's tree.

### The owner's sync script

`sync.sh` in the repo root is the owner's personal install path: it copies the
roster into `~/.claude/skills` and keeps a backup under `~/Downloads/`, and it
references a plan file at a hardcoded `~/worklogs/...` path specific to the
owner's machine — guarded, so a missing file is skipped with a stderr note
rather than aborting the sync. Treat it as a reference, not a turnkey
installer: it's wired to the owner's own profile dir and personal backup
location, not yours — either retarget the copy loop, or just use the manual
`cp -R` above. Its one design point worth keeping if you adapt it: per-skill
copy with no `--delete` semantics against the profile dir, so skills you keep
only in your profile survive a re-sync.

The roster itself never names a profile directory. A dispatch prompt points a
subagent at "the skills root this skill loaded from" rather than at a literal
path, because a hardcoded profile is a dispatch that reads nothing on anyone
else's machine. `render-agents.py --check` enforces that (below).

### The codex-agents toml surface

`codex-agents/*.toml` is a derived artifact, not a second copy to maintain by
hand: `render-agents.py` in the repo root rewrites every persona's toml from
its `skills/<persona>/SKILL.md` plus `skills/_shared/core.md`, creating one
for any new persona and reporting any orphaned toml with no matching skill.
Run `python3 render-agents.py` after any `skills/` edit — it's idempotent,
safe to run any time, and prints which tomls it wrote. **Never hand-edit a
toml** — the next run silently reverts it; change the `skills/` source and
re-run instead.

Two read-only modes back it up:

- `python3 render-agents.py --check` — exits non-zero on a toml that has
  drifted from its source, a `~/.claude*/skills` literal anywhere under
  `skills/`, or an orphan toml. It prints how many personas, markdown files,
  and tomls it examined alongside the violation count, because a zero with no
  denominator beside it can't be told apart from a check that looked nowhere.
- `python3 render-agents.py --selftest` — the positive control for all three:
  it copies the tree, breaks one input per check, confirms that check goes
  red, restores, and confirms it goes green again. A check nobody has watched
  fail is not evidence.

### Output styles (hand-installed, never synced)

`output-styles/scannable.md` is tracked in this repo but deliberately **not**
part of the roster copy or `sync.sh` — an output style changes a profile-wide
conversational default, and pushing that silently on every sync is a
different act from refreshing skills you already opted into. Install it
yourself, and only if you want it as your default:

- **Manual copy:**

  ```bash
  mkdir -p ~/.claude/output-styles
  cp output-styles/scannable.md ~/.claude/output-styles/
  ```

- **Hand it to an LLM instead** — paste this prompt into any session with
  filesystem access to your Claude profile:

  > Create the directory `~/.claude/output-styles` if it doesn't exist, then
  > copy the file `output-styles/scannable.md` from this repo into
  > `~/.claude/output-styles/scannable.md`.

Selecting Scannable as your active output style is a separate step (`/output-style`
or your profile's `settings.json`) — installing the file doesn't set it as
default anywhere.

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

## Why the persona files are thin

Each `SKILL.md` carries what is specific to that persona and points at
`_shared/core.md` for the rest — the orientation batteries, the dispatch
contract, the session-close routine. It reads as underspecified next to a
self-contained skill file, and that is deliberate: the roster previously
restated the shared chassis in every persona, which meant a wording fix had to
land in 27 places and the copies drifted between them. Current models don't
need the same instruction three times to follow it, and a repeated instruction
competes with the persona-specific content around it. If you find yourself
re-expanding a section because it looks too short, check whether `core.md`
already says it.

The same reasoning covers what is *absent*: instructions to double-check,
re-verify, or narrate progress step by step were removed rather than
shortened. Current models do those unprompted, and prompting for them on top
compounds instead of adding.

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
