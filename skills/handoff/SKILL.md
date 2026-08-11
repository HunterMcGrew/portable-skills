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

This is a utility, not a persona — no greeting, no orientation battery. It
runs in whatever voice the conversation already has.

## Shared core

If `_shared/core.md` hasn't been read this session, read it now from the same
skills root as this skill. It defines the repo map (which resolves the plans
location) and the plan file shape (which sections the flush targets).

## When to invoke

The user asks to hand off or continue in a new chat, a long session's
continuity across a new chat matters, or drift shows up in your own responses
— wrong file paths, stale assumptions, re-asking context already given. Don't
wait for the context edge: a session writing under pressure produces a worse
summary exactly when a good one matters most.

## Flush before writing

Promote plan-worthy state into the plan first (shape per the shared core):
unrecorded decisions, meaningful changes since the last History entry, open
bugs with a root cause, review findings not yet recorded, and this session's
Close bullet if it opened a `## Sessions` block — the handoff is this
session's close. The handoff doc carries only what the plan structurally
cannot: in-flight reasoning, the user's framing, open threads, dead ends. A
handoff doc growing sections that resemble `## Decisions` is a shadow plan —
promote the content, then reference it. No plan found? Note it in
`## Artifacts` and move on.

## Shape the document to the request

Read `$ARGUMENTS` or the user's last message for a scope filter (keep only
matching threads; everything else goes in `## Dropped`, never silently
absorbed) and a target persona (`clove:`, `briar:`, any roster name followed
by a colon) — a named target shapes `## Continue from` as a next-action brief
instead of a same-persona resume. No arguments, or a target that isn't an
installed roster skill, defaults to same-persona resume scoped to the
session's dominant thread; note the default in `## Focus` rather than
guessing silently.

## Write the document

**Path:** `<os-temp>/<repo-name>-handoffs/<YYYY-MM-DD>-<slug>.md` — repo name
from the repo map, slug from the scope or branch. `$TMPDIR` may or may not
carry a trailing slash — join with `"${TMPDIR%/}/..."`, which strips one when
present and adds exactly one either way. If the path already
exists, append a suffix (`-2`, or the HHMM time) — never overwrite, and never
a fixed shared filename. The OS reaps the temp dir; durable state belongs in the plan the flush step
already wrote, never here.

Sections, both shapes: `## Continue from` (what this session was doing and
where it stopped, or the next-action brief for a cross-persona route);
`## Artifacts` (plan, issues, PRs, key files — paths and URLs only, never
duplicated content); `## Open threads`; `## Live state` (uncommitted files,
open worktrees, background processes, an un-pushed branch); `## Dropped`
(threads the scope filter excluded); `## Suggested skills` (which roster
persona fits each open thread, by capability); `## Focus` (the passed
arguments restated as the next session's brief, plus any defaults taken
above).

Every `## Live state` and `## Open threads` item is either current — verifiable
from this session's tool output — or asserted from memory, and a memory-asserted
one is written with `(unverified)` on it so the next session re-checks before
acting. Live state is what the next session inherits physically, so an un-pushed
branch or an open worktree recalled rather than checked is the item most worth
marking.

Write neutral structured prose — no persona flavor, greetings, or character
voice; the next reader may be a different model or persona. Redact secrets
and PII before writing. The spoken summary back to the user (below) may stay
in the conversation's voice.

## Report the path

In the conversation's voice: the absolute path to the handoff file, the
one-line start for the next session ("New chat → read `<path>`, then continue
as `<persona>`"), and any default taken above the user should confirm or
redirect before opening the new chat.

## Read-side contract

A fresh session given a handoff path opens that file directly — never scans
the handoffs directory for a recent one; a stale handoff read as current is
worse than none. Then run normal startup: shared core, repo map, plan lookup.
The handoff doc supplements the plan, never replaces it — if `## Live state`
conflicts with the plan's `## History`, the plan is authoritative.
