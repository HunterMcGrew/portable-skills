# Review angles

Read by briar and eric only — an opt-in fragment, not core content. A review
pass with no coverage obligation ends when the reviewer runs out of ideas,
not out of check space — that's how a diff gets four passes on one defect
class and zero on the other eight. This fragment is the check space: nine
named angles, six always-on and three triggered, swept every pass and
reported with a status.

## Always-on angles

- **Runtime behavior** — does the changed code actually do, at runtime, what
  the diff and the plan claim? Read the logic as executed, not as described.
- **Test efficacy** — do the tests covering this diff actually fail if the
  behavior regresses, or do they pass regardless? A test that can't fail
  isn't coverage.
- **Spec and doc consistency** — does the diff match the plan's stated
  intent and AC, and does it leave any doc, comment, or config now
  contradicting the code?
- **Citation integrity** — does every cited line number, sha, file path, or
  quoted rule actually say what the citation claims, checked against the
  current file rather than trusted from memory?
- **External-system claims** — does the diff assert, or does the review rely
  on, behavior of a framework, library, API, or platform this repo cannot
  itself confirm? Treat every such claim as a question to verify at source
  (docs, source code, or a runnable check), not as model-resident knowledge.
  This is the single highest-value angle in this file: a reviewer that
  can't answer "how do I know this is actually how it behaves?" without
  checking is the reviewer that lets a plausible-sounding but wrong claim
  through, silently, every time.
- **Repo writing rules** — does the diff follow the host repo's own
  comment, naming, and structure conventions (per the repo map), not a
  generic style preference?

## Triggered angles

- **Security** — triggered when the diff touches auth, input handling,
  secrets, permissions, or any trust boundary.
- **Docs impact** — triggered when the diff changes a feature, component, or
  module with a matching docs file.
- **Accessibility** — triggered when the diff touches UI: semantic HTML,
  keyboard access, focus management, ARIA, contrast, `prefers-reduced-motion`.

## Status vocabulary

Each angle reports exactly one status per pass — no free text:

- **`swept`** — actively checked against this pass's diff.
- **`n/a — <reason>`** — does not apply to this diff at all (e.g. no UI in
  the diff, so Accessibility is `n/a`); the reason names why there's no
  surface here.
- **`not reached — <reason>`** — applies, but the pass didn't get to it
  (time-boxed, axis skipped, diff too large). An incomplete sweep, never a
  substitute for `n/a` — conflating "doesn't apply" with "didn't get to it"
  is what lets an incomplete pass read as a clean one.

The reason on a `not reached` is load-bearing, because it says whether
another pass can change the status. Two classes:

- **Pass-bounded** — the reason names this pass: time ran out, the diff was
  too large to finish, the budget was spent. A later pass can reach it, so
  the angle is pending.
- **Structural** — the reason names the *diff*: an axis that cannot run on
  this PR at all, such as a Spec axis skipped because the PR carries no plan
  and no AC. Nothing a later pass does changes the diff, so
  the status is terminal — it reads the same on pass 1 and pass 9. Write the
  structural cause into the reason so a consumer can tell the two apart
  without guessing. A consumer gating on coverage must treat a structural
  `not reached` as terminal rather than pending, or it waits forever for a
  status that cannot move.

A bounded angle — any angle whose status is not `swept` or `n/a` — caps the
reviewer's own verdict: the reviewer may not report an unqualified ready
state while one stands, and the best available verdict names the angle and
the specific check still owed. This is a label on output already produced,
not a gate on whether the review continues, and no consumer branches control
flow on it.

A `n/a` on one of the six always-on angles is a legal status and a
discrepancy at the same time — always-on is this file's claim that the angle
applies to every diff, so a pass declaring it inapplicable is reporting that
the claim didn't hold here. Give the reason, and expect a consumer to record
it. It does not make the pass incomplete; `not reached` is the status for
that.

## Enumeration

`swept` is not a verdict on its own; it carries an enumeration — the list of
items of that angle's unit found in the pinned range, each with its own
verdict. An item absent from the list is a visible gap; a bare `swept` is
not. An empty enumeration (`— no items`) is a legitimate and falsifiable
result; a *missing* enumeration is not.

**The unit, per angle:**

- **Runtime behavior** — each changed entry point whose behavior at runtime
  differs from before.
- **Test efficacy** — each new or changed behavior, paired with the test
  that fails if it regresses.
- **Spec and doc consistency** — each acceptance criterion and each doc,
  comment, or config the diff touches.
- **Citation integrity** — each cited line number, sha, path, or quoted
  rule.
- **External-system claims** — each external identifier the diff introduces
  or relies on: hook names, screen or route URLs, capabilities, CSS custom
  properties, API signatures, config keys. This is the unit the bake-off's
  missed major sat in; state it in full and do not compress it, on the same
  grounds this fragment already gives this angle.
- **Repo writing rules** — verdict-only; no natural enumerable unit. Its
  absence here is decided, not forgotten.
- **Security** — each trust boundary the diff touches.
- **Docs impact** — each changed feature, component, or module with a
  matching docs file.
- **Accessibility** — each interactive or focusable element the diff adds
  or changes.

**Where it goes.** To the reviewer's off-chat surface — briar's plan
`### Angle Coverage` block, eric's summary-comment `## Angle Coverage`
section. The chat-side line carries the token plus counts, never the list.

**Status interaction.** The three tokens are unchanged. A `swept` with no
enumeration is not a fourth status — it is an incomplete report, and a
consumer gating on coverage (review-loop's convergence predicate) reads it
as bounded, the same treatment `not reached` already gets.

## Finding anatomy

Every finding carries two fields beyond its existing ones:

- **`Class: <pattern>`** — the defect pattern in general terms, stated so it
  can be searched for (e.g. "plan-supplied external identifier asserted but
  never resolved against its source"), never the instance restated.
- **`Sweep: <where searched, what else found>`** — where the reviewer looked
  for other instances of that class and what turned up, including
  `— none found` and `— NOT swept: <reason>` as legitimate, visible values.

This does not fork `_shared/review-exhaustiveness.md`'s sibling-arm coverage —
the two sweep different things. Sibling-arm coverage is the *intra-construct*
sweep: other arms of the one switch, if/elif chain, or dispatch table the
finding sits in. Class/Sweep is the *cross-diff* sweep: other instances of the
same defect pattern anywhere in the pinned range, regardless of construct. A
finding on a multi-arm construct carries both, and neither substitutes for the
other.

## Reporting

The coverage block is exempt from conditional-emit: report all nine angles'
statuses every pass, including a clean pass with zero findings. A gap typed
into the output is harder to skip than a gap only implied by silence.

## Re-sweep obligation

On any pass after the first, the angles that were bounded, or whose
enumeration was thinnest, are re-run in full against the subject surface —
not merely checked for whether the prior pass's findings were fixed.
Verifying a fix is a different act from sweeping an angle: a pass that only
does the former inherits the prior pass's gaps while reporting a fresh
status.
