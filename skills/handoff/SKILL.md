---
name: handoff
description: >
  Compact the current session into a scoped handoff document a fresh agent can
  continue from — same persona or a different one. Flushes plan-worthy state
  into the plan first, then writes only the session residue to a unique path
  under the OS temp dir and reports that path back. Explicit /handoff
  invocation; no persona — runs in the current conversation's voice.
  Triggers: handoff, hand off, continue in a new chat, fresh session, pass this to.
argument-hint: "[scope and/or target — e.g. 'story 4' or 'clove: implement story 4.1']"
---

Compact the current session into a handoff document a fresh session can continue
from. The fresh chat is the win: every message in a long session re-pays for
every tool result and tangent that came before it; the handoff doc replaces the
conversation, not the working memory. The plan stays the working memory.

This is a utility, not a persona — no greeting, no orientation batteries. It
runs in whatever voice the conversation already has.

## Shared core

If `_shared/core.md` hasn't been read this session, read it now from the same
skills root as this skill. It defines the two things this utility depends on:
the repo map (which resolves the plans location) and the plan file shape
(which sections the flush targets).

## Lifecycle

1. **Resolve** — repo map → plans location → the active plan file.
2. **Flush** — promote plan-worthy state into the plan; the plan holds the
   durable record.
3. **Write** — session residue only, to a unique path under the OS temp dir.
4. **Report** — the exact path plus the one-line resume instruction.

## When to invoke

- The user asks to hand off or continue in a new chat.
- The session has 20+ messages and continuity across a new chat is expected.
- You notice drift in your own responses — wrong file paths, stale assumptions,
  re-asking context the user already provided.

Don't wait for 95% context — a session at the edge writes a degraded summary
exactly when a good one matters most.

## Step 1 — Flush before writing

Runs on every invocation, before the document is drafted. Promote any
plan-worthy state into the plan (shape per the shared core):

- Unrecorded architectural decisions → `## Decisions` (one bullet per decision,
  with the reason)
- Meaningful changes since the last History entry → `## History` (one line per
  unit of work, branch name included)
- Open bugs with a root cause → their structured `## Debugged Issues` entry
- Review findings not yet recorded → `## Review Issues`
- If this session opened a `## Sessions` line, append its close verdict now —
  the handoff is this session's close.

The handoff doc carries only what the plan structurally cannot: in-flight
reasoning, the user's framing, open threads, this session's dead ends. A handoff
doc that grows sections resembling `## Decisions` is a shadow plan; promote the
content, then reference it. The better the session maintained its plan, the
thinner this doc — that's the system working.

**Escape (no plan found):** if plan lookup per the shared core finds no plan,
skip this step. Note in the handoff `## Artifacts` section: "No plan found;
flush skipped." Proceed to Step 2.

## Step 2 — Parse the arguments

Resolve the handoff shape from `$ARGUMENTS` or the user's last message:

- **Scope filter** (a topic or story reference, e.g. "story 4") — keep only
  threads pertaining to the named scope; place everything else in `## Dropped`.
- **Target prefix** (`clove:`, `briar:`, any persona name followed by a colon)
  — produce the cross-persona shape instead of the same-persona resume.
- **No arguments** — same-persona resume, scoped to the session's dominant work
  item.

Ambiguity gets a default, not a stall: pick a defensible reading, state the
assumption in `## Focus`, and proceed — the user confirms or redirects at the
report-back, not mid-write.

**Escape (unrecognized target):** if the named target isn't one of the installed
roster skills (winston, sasha, clove, briar, eric, eli, sol — check the skills
root for the current set), default to same-persona resume and note in `## Focus`:
"Target `<name>` not recognized; defaulting to same-persona resume."

## Step 3 — Write the document

**Path:** `<os-temp>/<repo-name>-handoffs/<YYYY-MM-DD>-<slug>.md` — repo name
from the repo map, slug from the scope or branch. Create the directory on first
write, and join path segments explicitly: `$TMPDIR` may lack a trailing slash
(macOS hands back `/var/folders/...` without one), so use `"${TMPDIR%/}/..."` to
guarantee exactly one separator. If the path already exists (a second handoff the
same day), append a short suffix (`-2`, or the HHMM time) — never overwrite, and
never a fixed shared filename: unique paths prevent stale reads of dead handoffs.
The temp dir is the cleanup contract: a handoff is session residue the next
session consumes and discards, so the OS reaps stale handoffs and no one
maintains the directory. Durable state belongs in the plan, which the flush step
already wrote — never here. A committed plans location would otherwise pull
scratch residue into git, which is the trap this path avoids.

**Document shapes:** both shapes share these sections; the shape changes emphasis.

- **`## Continue from`** — one paragraph: what this session was doing and where
  it stopped. Same-persona resume: where the reasoning was mid-flight.
  Cross-persona route: a next-action brief — what to do, not how we got here.
- **`## Artifacts`** — plan, issues, PRs, key files. Paths and URLs only; never
  duplicate content the artifact already holds.
- **`## Open threads`** — questions raised and unresolved, one line each.
- **`## Live state`** — anything the next session inherits physically:
  uncommitted files, open worktrees, background processes, an un-pushed branch.
- **`## Dropped`** — one line per thread the scope filter excluded. Dropping is
  a visible decision, not silent decay.
- **`## Suggested skills`** — which roster persona fits each open thread, by
  capability; don't re-enumerate the roster.
- **`## Focus`** — the passed args restated as the next session's brief; any
  defaults or assumptions picked in Steps 1–2 stated here explicitly.

**Prose discipline:** omit persona flavor — greetings, character voice, puns.
The next reader may be a different model or persona, and voice is noise to it.
Write neutral structured prose: declarative sentences, section headers, bullet
lists for parallel items. Redact secrets and PII before writing. The spoken
summary back to the user (Step 4) may stay in the conversation's voice.

**Pre-report check** — before reporting, verify the draft on four points and fix
any gap:

1. **Scope** — is everything in the doc inside what the arguments named? Adjacent
   threads noticed but excluded belong in `## Dropped`, not silence.
2. **Assumptions** — every default picked without the user saying so is named in
   `## Focus`.
3. **Edges** — missing plan, empty sections, malformed arguments: each captured
   explicitly in the doc, not silently resolved.
4. **Evidence** — for each `## Live state` and `## Open threads` item, is the
   claim current (verifiable from this session's tool outputs) or asserted from
   memory? Mark memory-only items "(unverified)" so the next session re-checks
   before acting on them.

## Step 4 — Report the path

Report three things, in the conversation's voice:

1. The absolute path to the handoff file.
2. The one-line start for the next session:
   > New chat → "read `<path>`, then continue as `<persona>`"
   (same persona for a resume, the target persona for a cross-persona route;
   the fresh session invokes that persona's skill and reads the file first).
3. Any defaults picked in Steps 1–2 the user should confirm or redirect before
   opening the new chat — one line per default.

## Read-side contract

When a fresh session receives a handoff path: open the file at the given path.
Never scan the handoffs directory for recent files — a stale handoff read as
current is worse than no handoff.

Then run normal startup: shared core, repo map, plan lookup. The handoff doc
supplements the plan, never replaces it. If the handoff's `## Live state`
conflicts with the plan's `## History`, the plan is authoritative; the handoff
is the session-residue layer above it.
