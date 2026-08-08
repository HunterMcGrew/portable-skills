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

## Reporting

The coverage block is exempt from conditional-emit: report all nine angles'
statuses every pass, including a clean pass with zero findings. A gap typed
into the output is harder to skip than a gap only implied by silence.
