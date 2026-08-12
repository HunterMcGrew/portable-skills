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
document), review-loop (the briar → clove → eric gauntlet), devils-advocate
(red-teams a finished plan, PRD, strategy, model, or diagnosis and hands back
findings — never edits the artifact).

devils-advocate has no name or voice on purpose: a character with a
personality is tempted to *perform* skepticism, and performance is the failure
mode the skill exists to prevent. It also has no toml under `codex-agents/`,
for the same reason handoff and review-loop don't — `render-agents.py` keys
off the persona declaration line, so a utility skill is skipped by
construction rather than by a maintained exclusion list.

### Local-only skills stay local

Some skills live in a profile without living here — vendored ones, plugin ones,
experiments, and anything tied to a machine rather than a workflow. This repo
doesn't know their names — `sync.sh` never lists them, because its copy loops
are per-file with no `--delete`, so anything already in a destination that
this repo doesn't ship simply survives a sync untouched.

They are **deliberately out of scope**: not tracked in this repo, not synced by
`sync.sh`, and not covered by the audit in [ROSTER-AUDIT.md](ROSTER-AUDIT.md) or
the rubric in [SLIMMING-GUIDE.md](SLIMMING-GUIDE.md). When those documents say
"the roster," they mean what's under `skills/` here — 30 skill directories, of
which 27 declare a persona and 3 (`handoff`, `review-loop`, `devils-advocate`)
are utilities. Their own headline counts were written at different times and
have drifted; `ls -d skills/*/ | grep -vc _shared` is the live number.

Nothing needs configuring for this to work. The per-file, no-`--delete` copy in
`sync.sh` is what makes it safe — a sync refreshes what this repo owns and
leaves everything else in the profile untouched. That is why the loops copy
file-by-file instead of mirroring a directory, and it applies equally to skills,
subagent files, and output styles.

The tradeoff is worth naming: a skill this repo doesn't own gets no rubric, no
audit, and no review. `graphify` is the one to keep an eye on — it loads in
every session and has never been audited.

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

### sync.sh

`sync.sh` in the repo root does what the manual `cp -R` above does, plus the
agent shims and output styles, minus the parts you'd have to remember: run it
with no setup and it copies `skills/`, `claude-agents/`, and `output-styles/`
into `~/.claude`. That's the whole story for one profile — no exclusions, no
backup, nothing to configure.

`sync.sh` takes no arguments — there is no `--check`/`--dry-run` mode, only
the real deploy. Any argument exits 2 with a usage line before anything is
written; `sync-selftest.sh` is the read-only counterpart, and it never
touches a real profile.

Every copy loop is per-file with no `--delete` semantics against the
destination, so a skill, agent, or style you keep only in your profile (not
shipped by this repo) survives a re-sync untouched.

That property has one cost, and it lands on upgrades: **a sync never removes
anything, so a file this repo renames stays in your profile under its old
name.** Both copies then resolve. The `p-` prefix on the agent shims is
exactly such a rename — if you synced before it, `~/.claude/agents/` now
holds both `winston.md` and `p-winston.md`, and the unprefixed one is the
silent collision the prefix exists to remove. Prune the superseded names by
hand, once, per destination:

```bash
ls ~/.claude/agents | grep -v '^p-'   # look first
ls ~/.claude/agents | grep -v '^p-' | sed "s|^|$HOME/.claude/agents/|" | xargs rm
```

The same applies to any future rename of a generated file. `sync.sh` will not
tell you — nothing compares the destination against the repo — so the release
note is the only warning you get.

If your setup is more than one profile — say, a personal `~/.claude` and a
second profile for a specific client or repo that ships its own
similarly-named personas and shouldn't get this roster's colliding ones —
drop a `sync.local.sh` next to `sync.sh`. It's gitignored, sourced before the
sync runs if present, and sets three things:

```bash
# sync.local.sh — untracked, not read by anyone else's clone
DESTS=("$HOME/.claude" "$HOME/.claude-work")
EXCLUDES=("" "some-persona-name")   # parallel to DESTS; "" means no exclusions
BACKUP_DIR="$HOME/Downloads/portable-skills-backup"  # optional; omit or leave "" to skip
```

**`BACKUP_DIR` is a mirror, not an additive copy.** It runs
`rsync -a --delete`, so anything in that directory that this repo doesn't
ship is deleted on every sync. Give it a directory dedicated to this backup
and nothing else — never an existing documents, downloads, or cloud-synced
folder that holds anything you care about. `sync.sh` refuses the three
targets that would be unrecoverable (`$HOME`, the repo itself, `/`), but it
cannot detect a directory you merely share with something else.

`EXCLUDES[i]` is a space-separated list of skill names to skip for `DESTS[i]`,
written unprefixed — `winston`, never `p-winston`; the agent shim is matched on
its stripped name, so the prefixed form matches nothing. It's parallel-array
rather than an associative array because the
bash macOS ships (3.2) predates them. An excluded name is skipped for both
the skill directory and its `claude-agents/*.md` shim together: the agent
file's `skills:` field preloads the same-named skill, so shipping the shim
without the skill produces an agent pointing at nothing. `sync.sh` warns on a
stale exclusion (a listed name with no matching `skills/` dir) so a rename
doesn't silently start leaking the renamed skill into a profile that meant to
exclude it.

`./sync-selftest.sh` covers that logic in nine controls — exclusions, the
prefix strip, the no-`--delete` guarantee, an empty `DESTS`, and the three
abort conditions — against a fabricated tree in `$TMPDIR` with `HOME`
redirected there, so it never touches a real profile. Two are paired red
controls: they break the mechanism under test and assert the check goes red,
so the control it guards cannot pass by testing nothing.
`render-claude-agents.py --selftest` applies that discipline to all three of
its own.

No `sync.local.sh`? The script runs the single-profile default above — that
absence is the normal case, not a degraded one. How you sync beyond that is
your own affair; this repo ships the skills and a script that obviously works
for one profile.

The roster itself never names a profile directory. A dispatch prompt points a
subagent at "the skills root this skill loaded from" rather than at a literal
path, because a hardcoded profile is a dispatch that reads nothing on anyone
else's machine. `render-agents.py --check` enforces that (below).

### The codex-agents toml surface

`codex-agents/*.toml` is a derived artifact, not a second copy to maintain by
hand: `render-agents.py` in the repo root rewrites every persona's toml from
its `skills/<persona>/SKILL.md` plus everything that file would otherwise have
to open at runtime — `skills/_shared/core.md` and `_shared/verification.md` for
every persona, plus any other `_shared/<name>.md` fragment and any
`references/<name>.md` file that persona's own body cites. A codex agent has no
filesystem to resolve a pointer against, so a cited path that isn't inlined is
a broken reference rather than a deferred read. The renderer creates a toml for
any new persona and reports any orphaned toml with no matching skill.
Run `python3 render-agents.py` after any `skills/` edit — it's idempotent,
safe to run any time, and prints which tomls it wrote. **Never hand-edit a
toml** — the next run silently reverts it; change the `skills/` source and
re-run instead.

Two read-only modes back it up:

- `python3 render-agents.py --check` — exits non-zero on a toml that has
  drifted from its source, a `~/.claude*/skills` literal anywhere under
  `skills/`, or an orphan toml. The literal scan reads every `.md` in the
  tree — `references/` files and `_shared/` fragments as well as the SKILL.md
  bodies — because all of them inline into a consumer toml. It prints how many
  personas, markdown files, and tomls it examined alongside the violation
  count, because a zero with no denominator beside it can't be told apart from
  a check that looked nowhere.
- `python3 render-agents.py --selftest` — the positive control for all three:
  it copies the tree, breaks one input per check, confirms that check goes
  red, restores, and confirms it goes green again. The literal check gets
  four plants — a SKILL.md body, `_shared/core.md`, a `references/` file, and
  a non-core `_shared/` fragment — so narrowing its file list back to a subset
  shows up as a failing control instead of a green check over a surface it
  stopped reading. A check nobody has watched fail is not evidence.

### The claude-agents subagent surface

`claude-agents/*.md` is the second derived artifact, built by
`python3 render-claude-agents.py` from the same `skills/` sources. Same
contract as the tomls: idempotent, `--check` exits non-zero on drift, orphans
are reported rather than deleted, hand-edits are silently reverted by the next
build, and `--selftest` supplies the positive control — it breaks one agent
file and plants one orphan against a throwaway copy, confirming each check goes
red and then green again.

Unlike the tomls, these are **shims**. Each is frontmatter plus three short
paragraphs, with the persona pulled in by the documented `skills:` field — which injects
the skill's *full content* at startup, not just its description. The Codex
tomls inline everything because Codex has no skills mechanism to defer to;
Claude Code does, and `sync.sh` already installs every persona under
`~/.claude/skills/`. Inlining here would put each persona in the profile twice
and let the copies drift, which is the failure `render-agents.py`'s own header
records. Utilities (handoff, review-loop, devils-advocate) get no agent file,
by the same persona-declaration gate that governs the tomls.

**Know what this buys before relying on it: skills and subagents have opposite
precedence.** A repo's `.claude/agents` beats `~/.claude/agents` — read out of
the shipped Claude Code binary, whose agent dedupe walks built-in, plugin, user
settings, then project settings, last write winning. The mirror-image half —
that a personal `~/.claude/skills` entry beats a repo's `.claude/skills` — was
confirmed by experiment: a same-named throwaway skill with distinguishable
marker bodies was planted in both `~/.claude/skills/` and a scratch repo's
`.claude/skills/`, and a nested headless session invoked from inside the
scratch repo resolved the personal body, twice, reproducibly. The skill
appeared in the listing exactly once, not twice — the load-bearing detail,
since it means an override, not a merge. So: the skills half is
experiment-verified, the agents half is verified by reading the binary's own
dedupe logic — different evidence classes, both load-bearing. On the agents
half: an unprefixed portable stub would lose to any repo shipping a persona of
the same name, which is why these are not unprefixed. Each stub registers as
`p-<name>` — `render-claude-agents.py`'s `AGENT_PREFIX`, applied to the
frontmatter `name:` and the filename only, never to `skills:`, which still has
to resolve against `skills/<name>/SKILL.md`. Both rosters are therefore
reachable side by side, and which one you get is explicit at the call site:
`subagent_type: "p-winston"` is this repo's Winston, `subagent_type: "winston"`
is whatever the host repo ships. Prefixing this side rather than the repo's is
what keeps it a one-script rename instead of a team PR. One caveat holds
regardless of how it was checked: this is vendor-owned behavior and can change
on any Claude Code release — a release that changes skill resolution is this
claim's reopening signal.

This paragraph is the only copy of the precedence claim. It is vendor-owned and
no `--check` covers prose, so `sync.sh` and `render-claude-agents.py` point here
instead of restating it — three hand-maintained copies is the drift the
renderers exist to prevent. `render-claude-agents.py`'s `AGENT_PREFIX` comment
is the one deliberate near-exception: it names the *consequence* the prefix
defends against rather than which side wins, so the orderable fact still lives
only here. A release that changes resolution falsifies both, so that comment is
the second thing to check when this paragraph reopens.

Neither renderer is wired into `sync.sh`: rendering is a build step that
mutates tracked files, syncing only copies committed ones.

### Output styles

`output-styles/*.md` sync to every destination alongside skills and agents.

This was once deliberately excluded, on the reasoning that an output style
changes a profile-wide conversational default and pushing that silently is a
different act from refreshing skills you opted into. The reasoning was sound
but aimed at the wrong risk: copying the file only makes a style *available*.
Selecting it is a separate step (`/output-style`, or `outputStyle` in your
profile's `settings.json`), and no default is set anywhere in this repo.

What changed the call is that the THR-851 bake-off measured the output style
as a *larger* lever on response shape than the entire skill redesign — +113%
chat output from the style alone, against ~500 words for slim-vs-fat. A
profile running this roster without the matching style is running a different
configuration from the one that was tuned, so leaving the styles uninstalled
was the bigger hazard.

Two ship today: **Focused** (answer-first, calibrated to Opus 5's own
guidance) and **Scannable** (high-density, and note it instructs the model not
to announce what it is about to do — if your `CLAUDE.md` asks for exactly that,
the two conflict, and conflicting guidance across layers degrades compliance).

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
lessons, plans, verification, ticket pattern), and writes `.repo-map.md` itself.
Front-loading this interview beats mid-task questions — make it the first thing
you do in a new repo. Roles you leave out are opt-outs (no `lessons` line → no
lesson capture; no `ticket pattern` → Nora and Briar's Spec subagent fall back
to a generic ticket shape), and skills will offer to append locations they
discover mid-session back into the map.

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
`_shared/core.md` for the rest — the orientation battery, the dispatch
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
  kept. The `## Sessions` section holds one dated block per session — four
  opening bullets (Intent / Ambiguity / Bounds / Approach) plus a Close
  bullet appended at the end — private tooling state, never the host repo's
  concern.

## Roadmap

- Roster is complete (dev workflow + sol + business + utilities, all on
  `_shared/core.md`). Excluded on purpose: onboarding/install personas
  (Atlas, skill-forge) — they configure a specific toolkit repo and have no
  meaning as portable skills.
- Re-run the copy (`cp -R skills/* ~/.claude/skills/`, or `./sync.sh`) after
  adding or editing personas — copies don't self-propagate.
- If long sessions still drift despite the orientation battery and the
  `## Sessions` Close bullet's drift check, a user-level PostToolUse hook is
  the mechanical backstop — layer it on, don't replace the skill-level
  instructions.
