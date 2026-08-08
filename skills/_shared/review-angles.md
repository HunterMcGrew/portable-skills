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
  this PR at all, such as a Spec axis skipped because the PR is docs-only or
  carries no plan and no AC. Nothing a later pass does changes the diff, so
  the status is terminal — it reads the same on pass 1 and pass 9. Write the
  structural cause into the reason so a consumer can tell the two apart
  without guessing. A consumer gating on coverage must treat a structural
  `not reached` as terminal rather than pending, or it waits forever for a
  status that cannot move.

A `n/a` on one of the six always-on angles is a legal status and a
discrepancy at the same time — always-on is this file's claim that the angle
applies to every diff, so a pass declaring it inapplicable is reporting that
the claim didn't hold here. Give the reason, and expect a consumer to record
it. It does not make the pass incomplete; `not reached` is the status for
that.

## Reporting

The coverage block is exempt from conditional-emit: report all nine angles'
statuses every pass, including a clean pass with zero findings. A gap typed
into the output is harder to skip than a gap only implied by silence.
