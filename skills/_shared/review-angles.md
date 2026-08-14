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

## Axis split

Briar and eric both split their review into two parallel, context-isolated
axes — Standards and Spec — and never merge findings across them. This
section is the single owner of which angle runs on which axis; both
personas cite it rather than restating the assignment.

- **Standards axis** runs: Runtime behavior, Test efficacy, External-system
  claims, Repo writing rules, Security, Accessibility.
- **Spec axis** runs: Spec and doc consistency, Citation integrity, Docs
  impact.

Both axes are presented verbatim or lightly cleaned under separate
headings, never merged, never reranked, and no single cross-axis winner —
that separation is the artifact's structure, not a formatting preference.
Aggregate with one summary line: findings per axis and the worst within
each.

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
  absence here is decided, not forgotten. `verdict-only` is a shape on *both*
  surfaces, not a chat-side abbreviation: the word stands where the
  enumeration would go in the off-chat block exactly as it stands in the chat
  line's counts slot. That is what makes `Repo writing rules — swept` a
  complete report rather than a permanently incomplete one.
- **Security** — each trust boundary the diff touches.
- **Docs impact** — each changed feature, component, or module with a
  matching docs file.
- **Accessibility** — each interactive or focusable element the diff adds
  or changes.

**Where it goes.** To the reviewer's off-chat surface — briar's plan
`### Angle Coverage` block, eric's summary-comment `## Angle Coverage`
section. Refer to either by its surface rather than its heading level: the
same string names briar's plan block and his chat section, so a consumer
keyed to the level alone cannot tell them apart, and it is not eric's level
at all. A `swept` angle carries its enumeration there. One angle is given no
unit by § Enumeration. It carries `verdict-only` in that slot — the
enumeration slot filled, not left empty. The chat-side line
carries the angle, its status token
verbatim, and the counts — nothing further. Verbatim includes the
`— <reason>` that § Status vocabulary makes part of `n/a` and
`not reached`: that reason is the token, not a defense of it, and two
consumers parse it. The counts slot carries `<n> items enumerated,
<n> verdicts` on `swept`, the word `verdict-only` on the one angle given no
unit by § Enumeration, and nothing at all on `n/a` and
`not reached`, which carry no enumeration. All three shapes in full:
`Runtime behavior — swept — 12 items enumerated, 12 verdicts`,
`Repo writing rules — swept — verdict-only` and
`Accessibility — n/a — no UI in the pinned range`.

What is banned is everything after that — no caveat, no second
sentence, no explanation of why an angle came back clean. Banning only
the list is not enough: prose defending a status restores the same wall
of text the counts exist to replace, and a reader who skims nine
paragraphs of "checked, fine" stops reading the block that carries the
loop's coverage signal. An angle whose status needs
explaining does not get a slot to explain it in: neither destination's
shape admits free text, and the status already has to stand on its own
under § Status vocabulary.

**Status interaction.** The three tokens are unchanged. A `swept` with no
enumeration is not a fourth status — it is an incomplete report, and a
consumer gating on coverage (review-loop's convergence predicate) reads it
as bounded, the same treatment `not reached` already gets.

That reading is scoped to the angles given a unit by § Enumeration. The one
without carries `verdict-only` in the enumeration's place and is read as
`swept`, complete, never bounded. The carve-out is load-bearing rather than
tidy: without it `Repo writing rules — swept` is unsatisfiable by
construction — the angle has no unit, so no pass can ever produce the
enumeration the gate is waiting for — and a review phase carrying it runs to
budget exhaustion every time instead of converging.

## Finding anatomy

**One cause is one finding.** Composed once, at its clearest location, with
every other site it appears in listed under it — never N findings with
their own severities for one root cause. This holds inside whichever axis
produced the finding, and within an inline-comment mechanism alike; it is
the complement of the first-finding-stop anti-pattern (`_shared/review-exhaustiveness.md`)
— that rule stops the reviewer from quitting at the first instance, this
one stops the reviewer from re-reporting the same instance as if it were
several.

Every finding carries two fields beyond its existing ones:

- **`Class: <pattern>`** — the defect pattern in general terms, stated so it
  can be searched for (e.g. "plan-supplied external identifier asserted but
  never resolved against its source"), never the instance restated.
- **`Sweep: <the exact pattern or command run>, <where searched>, what else
  found`** — the literal search, not just its scope. Prefer the narrowest
  stable token over a phrase: a phrase probe can wrap a line break and
  return clean against a live defect, while the token inside it still
  matches — quote what you actually ran (e.g. `` grep -rn 'orientation-battery' ``,
  not "searched the README"), including `— none found` and
  `— NOT swept: <reason>` as legitimate, visible values.

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
