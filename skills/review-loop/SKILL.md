---
name: review-loop
description: >
  Orchestrate the review gauntlet on a PR — self-review loops with
  fixes until a zero-findings pass, then PR review the same way; cleaner-path
  findings route by certainty (clear-cut → implement, uncertain → architect,
  architect-uncertain → pause for user). Pass budget, three-strike survival rule
  with mandatory diagnosis, scoreboard TLDR; PR stays draft. Explicit
  invocation; no persona. Triggers: review loop, gauntlet, full review cycle,
  review until clean.
argument-hint: "[PR number or branch — e.g. '#76' or 'current branch']"
---

Orchestrate the full review gauntlet on the target PR. This is a utility, not a
persona — no greeting, no character; it runs in the current conversation's
voice. It sequences the roster personas and never reviews, fixes, or writes
findings itself. The personas keep their own plan hygiene (`## Review Issues`
entries, `## History` appends, the orientation battery) exactly as if invoked
by hand.

## Shared core

If it isn't already loaded in this conversation, read `_shared/core.md` from
the same skills root as this skill. The loop leans on it for the repo map,
the plan file shape, and the dispatch idiom. The orientation battery
belongs to the personas this utility invokes, not to the utility itself.

## Lifecycle

1. Resolve the target — PR (or branch), plan file, repo map.
2. **briar loop** — self-review → clove fixes → re-review, until the phase
   converges (two consecutive clean passes — see § The review base).
3. **eric loop** — PR review → clove fixes → re-review, until the phase
   converges and every fixed thread is resolved.
4. Scoreboard TLDR. The PR stays draft throughout.

## Resolve the target

- Identify the PR from `$ARGUMENTS`, the current branch, or `gh pr view`. No
  PR yet? The briar loop can start on the branch; clove ships the PR before
  the eric loop (authors ship — see the shared core's house rules).
- Resolve the repo map per the shared core; find or create the plan file at
  `<plans>/<ticket-id>.md`. The plan is the content bus: briar writes
  `## Review Issues`, clove reads and fixes there.
- Verification commands (type-check, tests, build) come from the repo map's
  `verification` role — the personas run them; the loop just confirms the
  role resolves before starting.
- Confirm the PR is (or stays) draft. The loop never flips ready-for-review
  and never merges — both are the human's call.

## The review base

The loop reviews a fixed target. Capture it once, before the first briar pass:

```
loopBase = git rev-parse HEAD
```

`loopBase` does not move again for the rest of the run — not after a fix
commit, not at the briar → eric boundary, not across a handoff into a fresh
session. Recapturing it is the single thing that stops the loop from
terminating: when the base advances with `HEAD`, every fix the loop lands
joins the surface the next pass reviews, so each pass reviews the previous
pass's repairs and the run ends only when it runs out of its own prose to
tighten. A fresh session that recomputes it from `HEAD` inherits exactly the
defect the freeze prevents — it looks like recovery and is actually the
un-freezing. `loopBase` travels in `## Gauntlet state` (see Guardrails).

### The four surfaces

| Surface     | Range                                                    | Review bar |
| ----------- | -------------------------------------------------------- | ---------- |
| **Subject** | `merge-base..loopBase`                                    | The full review bar. The work under review — the same range on pass 1 and pass 9. |
| **Repair**  | `loopBase..HEAD`                                          | Regression-only. A finding here needs one of the four anchors below. |
| **Ledger**  | the plan's `## Review Issues` and `## History`, plus the repo's lessons file (per the repo map; no `lessons` role → just those two plan sections) | Not a review target during the loop. |
| **Meta**    | prose *about* the work: PR title/body/labels, readiness lines, plan hygiene | One batch after the subject converges — see `## Meta findings`. Never loop fuel. |

The ledger is the loop's own bookkeeping: briar and eric write it as they go,
so reviewing it mid-run is the loop grading its own notes, and each grading
pass writes more ledger for the next pass to grade. It re-enters review
normally on a future run, once it is part of someone else's subject surface.
The plan's `## Decisions` section is **not** ledger — it records intent that
predates the loop, and the reviewers' Decisions sweeps still run against it.

### Admissibility on the repair surface

Subject-surface findings need no justification beyond the usual review bar.
A repair-surface finding needs an anchor — one of these four, named
explicitly in the finding:

1. **A command that regressed.** A verification-role command (per the repo
   map) passing at `loopBase`, failing at `HEAD` — name the command and both
   results.
2. **A violated acceptance criterion**, quoted by its stable ID (`AC-3`) and
   text from the plan's `## Acceptance Criteria`.
3. **A contradicted `## Decisions` entry**, quoted from the plan.
4. **An original finding still unclosed** — quote the finding from the pass
   that raised it, and say what about the fix leaves it open.

No anchor, no finding. Each anchor points at something that existed before
the fix commit — that is what separates a regression from a fresh opinion
about text the loop itself just wrote. A repair-surface observation that
clears none of them is real feedback in the wrong place: record it in the
plan's `## Review Issues` with `Status: follow-up` and give it a scoreboard
line; it never drives a fix pass.

### Convergence

A phase exits on **two consecutive passes with zero admissible subject
findings** *and* full angle coverage. One clean pass is not convergence: the
pass right after a fix commit is the likeliest place for a reviewer to raise
something about the repair rather than the subject, so the second clean pass
confirms the first was not an accident of timing.

**The coverage gate.** Every angle in the reviewer's angle-sweep
applicability map must read `swept` or `n/a — <reason>` in its
`### Angle Coverage` block before a pass counts toward the two-clean-pass
exit. A `not reached — <reason>` angle means that pass is not clean — it
does not reset the consecutive-clean-pass counter the way an admissible
finding would, but it holds the counter where it is: the phase cannot
converge until that angle later reads `swept` or `n/a`.

**The enumeration refinement.** `swept` on its own is not enough for this
gate — `_shared/review-angles.md` § Enumeration requires a `swept` angle to
carry its enumeration. Read it on the off-chat surface named by that
fragment's § Where it goes — briar's plan block, eric's summary comment.
Never on the chat line, which carries counts in place of the enumeration by
construction and would read as unbounded on every angle. A `swept` with no
enumeration there is read as bounded for this predicate, the same treatment
as `not reached — enumeration absent`, evaluated loop-side over the
reviewer's already-returned report. The three status tokens do not change;
this is a refinement of how `swept` is read, not a fourth token.

**Structural exemption — the one case a `not reached` is terminal.** The
rule above assumes the reason names the *pass*: time-boxed, diff too large,
budget spent. A later pass can change any of those, which is what makes
holding the counter the right move. A reason that names the *PR* cannot be
changed by a later pass — eric's `not reached — Spec axis skipped` on a
PR with no plan and no AC is a property of the PR, not of the pass, so it
reads identically on pass 1 and pass 9. Treat a structural `not reached`
as covered for this predicate: it satisfies the gate, records the gap on its
own scoreboard line, and carries into the phase's closing report so the gap
stays visible rather than silently absorbed. Without this the eric phase can
never converge on a PR that carries no plan and no AC — it runs to budget
exhaustion (Procedure D) every time, waiting for a Spec axis that has
nothing to read. The two reason classes are named
by the angle fragment the reviewers read — it owns the vocabulary; the loop
reads the reason, it does not invent the distinction. The predicate is
evaluated by the loop, over the reviewer's already-returned report — never
delegated to the reviewer, which would make it a coverage gate the reviewer
grades itself against, the failure mode that cost PRISM's gated personas
their final turns satisfying their own gate instead of doing the work. The
reviewers now cap their own verdict on a bounded angle (`_shared/review-angles.md`)
— that is a label on output, not this predicate: the loop continues to
evaluate coverage from the `### Angle Coverage` block alone and never reads
the reviewer's verdict string or labels as a convergence input. The
distinction is load-bearing for the reason above: a predicate the reviewer
can satisfy by declaring itself finished is the PRISM failure; a label that
can only move downward is not. The
applicability map only **widens** across the run — an angle that reads
`n/a` on one pass can read `swept` on a later one, never the reverse — and
it travels with `loopBase` (§ Guardrails, Gauntlet state travels).

Anything still open when a phase converges — minors the loop chose not to
fix, observations that failed admissibility — converts to a `Status:
follow-up` entry in `## Review Issues`, not to another fix pass; winston's
closing ceremony carries them out through its loose-thread check. Only
subject-surface findings count toward, or reset, the two-clean-pass exit.

## How personas are invoked

A review loop is inherently serial — each pass depends on the last — so
invoke each persona in-conversation by its lowercase skill name for each
iteration: briar for a self-review pass, clove for a fix pass, eric for a PR
review pass, winston for an architecture call. Let the persona run its full
startup and rules, then resume orchestration when it finishes. Don't spawn
parallel lanes here; there is nothing to parallelize.

If this loop is itself running inside a dispatched lane (no user available),
the "pause for the user" steps below become typed report-back verdicts
instead: emit `needs-human` or `blocked` with the details named, per the
shared core's dispatch idiom — never a question into the void.

## The ladder

1. **briar loop (self-review).** Invoke briar on the branch. Every finding,
   any severity (critical, major, minor, nit, cleanup), goes to clove to fix —
   review-fix commits stay separate commits, never amends, so the reviewer can
   diff what changed since her last pass. Re-invoke briar. Repeat until the
   phase converges per § The review base. Name `loopBase` in every briar
   invocation — her side of the contract is her § Inside a review loop.
2. **eric loop (PR review).** Same shape on the PR: eric reviews and posts
   findings, clove fixes, eric re-reviews. Eric gets the same `loopBase` and
   the same surfaces — the subject range does not advance because the briar
   phase landed fixes into it. This phase is not done until the phase
   converges **AND zero fixed-but-unresolved review threads** remain — when a
   fix lands a finding, the thread that flagged it is only closed by eric's
   next pass (the reviewer is the sole actor that resolves threads). If fixed
   threads remain unresolved when the phase converges, run one final eric
   pass to resolve them before closing the phase.
3. **Cleaner paths.** Reviewer suggestions of a better shape — non-blocking by
   design; they never gate the zero-findings exit, but each must reach a
   terminal state before the loop closes: implemented, rejected with a
   one-line reason, or parked by the user. Route by certainty (Procedure C).
4. **Closing ceremony (winston).** When the eric phase exits clean, run
   winston's closing ceremony as the loop's final phase — automatic here, no
   nudge needed: promotion-verdict sub-bullets on every `## Decisions` entry
   (promotions written into the architect docs on the same branch), lessons
   check, loose-thread check, History ceremony line. Notes only — the plan is
   never deleted or archived (archive is zoe's lane), and the ceremony always
   lands pre-merge as the branch's final commit. The scoreboard TLDR reports
   it as its last line.

## Meta findings

A finding can be about the work itself, or about the prose that describes the
work — the PR body, a readiness line, plan hygiene (a stale `## Decisions`
entry, an unlogged fix). Meta findings never re-arm the loop: they close in
one batch, after the subject (code or AC) has already converged, not
interleaved with review/fix passes. Route them the same way as any other
finding — clove fixes, the reviewer confirms — but track them on their own
line in the scoreboard so a prose-only cleanup pass doesn't read as another
code-review strike.

Only subject-surface findings count toward — or reset — the
two-consecutive-clean-pass exit. The meta batch runs after that exit and
cannot reopen it; a meta fix that touches source is no longer a meta fix,
and routes as a subject finding on the next run.

## Guardrails

- **Pass budget: 20 review/fix passes.** Before every pass, run Procedure B.
  Winston consultations and user pauses don't count — they're escalations,
  already bounded. Exhaustion triggers Procedure D — stop, report, hand back.
- **Three-strike survival rule.** An issue a reviewer re-raises after a fix
  pass has survived a strike. Strike 1: run Procedure A. Strike 2: continue,
  marked in the scoreboard. Strike 3: Procedure E — pause the loop on that
  issue and bring the user in with the full survival history. When reviewer
  and fixer run on the same model, their strike votes are correlated — a
  blind spot one misses, the other likely misses too — so the mandatory
  one-sentence diagnosis (Procedure A) is the arbiter of whether a re-raise
  is real progress, not the strike count alone.
- **Sibling and angle coverage.** Reviewer passes follow
  `_shared/review-exhaustiveness.md` for multi-arm constructs (findings carry
  per-sibling coverage) and their own angle sweep for angle coverage (every
  pass's `### Angle Coverage` block is read against the applicability
  map). A defect surfacing on a later pass in an arm — or an angle — an
  earlier pass's construct already covered, or already reported `swept`, is
  a coverage miss by that earlier pass — note it on its own scoreboard line;
  it is not a strike against the fix.
- **Always-on-content trip-wire.** Generalized off directory membership —
  any `skills/_shared/*.md` fragment, not off frontmatter, since the
  fragments carry none. If a pass's `### Angle Coverage` block reports
  anything other than `swept` for an angle a fragment declares always-on,
  that mismatch fires the trip-wire: the loop records the discrepancy (which
  angle, which fragment, which status) on its own scoreboard line and does
  not review the fragment's content itself — a shared fragment is not on the
  subject surface. The mismatch is what fires it, never the fragment's
  content. **This does not contradict the coverage gate above, and the two
  are not competing verdicts on the same fact.** `n/a` on an always-on angle
  satisfies the gate — the pass can still be clean — *and* is itself the
  discrepancy this wire exists to record: a fragment declared that angle
  applicable to every diff, and this pass declared it inapplicable to one.
  Convergence is not the question being asked; whether the always-on
  declaration is still true is. A docs-only pass reporting `Runtime
  behavior — n/a` converges and trips the wire, and both are the intended
  outcome. The fragment states the same rule from the vocabulary side.
- **Disagreement fast-path.** If the strike-1 diagnosis names disagreement —
  clove believes the finding is wrong — skip the strike counter and run
  Procedure F immediately. Disagreement ping-pong would measure stubbornness,
  not progress.
- **Phase boundary.** At the briar → eric handover, a cold context makes eric
  a more independent second opinion. Offer the user a fresh session for the
  eric loop (carrying the gauntlet state below) or continue in-conversation;
  default to continuing if the user doesn't care.
- **Thread-clean exit.** The eric phase never closes with
  fixed-but-unresolved threads outstanding. If any remain after the final
  reviewer pass, run Procedure H.
- **Gauntlet state travels.** Any mid-gauntlet handoff carries the loop's
  live state — `loopBase`, the angle applicability map, pass count,
  consecutive-clean-pass count, strike table, scoreboard, current phase, and
  draft-hold status (whether the dispatch carried a conductor draft-hold
  declaration) — in a `## Gauntlet state` section so a fresh session resumes
  without replaying. `loopBase` leads the list because it is the one item a
  fresh session will silently reconstruct wrong: recomputing it from `HEAD`
  looks like recovery and is actually the un-freezing the base exists to
  prevent. The applicability map travels for the same reason: a fresh
  session that starts it over from empty forgets every angle a prior pass
  already swept, which the widen-only rule (§ Convergence) only protects
  against if the map itself makes the handoff.

## Procedures

**Procedure A — fix pass after a strike.** Before clove writes any code:
write a one-sentence diagnosis naming the failure mode — misread finding,
partial fix, or disagreement. Disagreement → Procedure F immediately. Misread
or partial → continue with the fix. Record the diagnosis and strike count in
the scoreboard.

**Procedure B — budget check.** Count passes taken so far. At 20: stop all
loops, write the scoreboard TLDR with current state (pass count, open
findings by severity, strike table, cleaner-path states), and hand back to
the user (or emit `blocked` in a dispatched lane — pass count, open issues,
most promising next step).

**Procedure C — route a cleaner path.** Can the correct fix be determined
from the diff and the existing codebase alone?

- **Yes (clear-cut):** clove implements now.
- **No (uncertain about the right approach):** invoke winston in-conversation
  with the finding and the relevant diff context. If his recommendation
  resolves the uncertainty, clove implements.
- **winston says it needs user input:** pause the loop. Present the finding,
  winston's analysis, and the specific question; wait for the answer (or emit
  `needs-human` in a dispatched lane).

**Procedure D — budget exhausted.** Stop all loops. Produce the scoreboard
TLDR, state that the budget is exhausted, list what remains open. The PR
stays draft. Hand back to the user with the scoreboard.

**Procedure E — third strike on a single issue.** Stop loop passes on that
issue. Collect the full survival history: the finding as originally stated,
each fix attempt and what it changed, each re-raise and what the reviewer
said. Present it with a clear question: accept the finding as-is, reject it
with a written reason, or direct a new approach. Don't continue on this
issue until the user responds.

**Procedure F — disagreement fast-path.** Invoke winston with the original
finding, clove's counter-argument, and the relevant diff. His verdict routes
it: finding correct → implement; finding incorrect → close with a written
reason; needs user input → pause and present both positions plus winston's
assessment. No more fix passes on this issue until the verdict is in.

**Procedure H — thread-clean exit blocked.** If a final eric pass still
leaves unresolved threads, stop the phase. List the unresolved threads, the
findings they covered, and the fix commits that addressed them. The user can
resolve threads manually in GitHub or request another reviewer pass. Do not
declare the phase clean.

## Closing — the scoreboard TLDR

Produce the scoreboard: a per-persona table of passes and what each found or
fixed, plus totals —

- review passes / fix passes
- issues found and fixed, by severity
- strike table (any issue that survived a strike, with its diagnosis)
- coverage misses (sibling arms and angles), by pass
- cleaner paths: implemented / rejected / parked

The PR stays draft; tell the user it's ready for human testing and review.
Flipping ready-for-review and merging remain the human's call — the shared
core's house rules say the same to every persona, and this utility is no
exception.
