# Sibling-arm coverage — no first-finding stop

Read by code reviewers (briar, eric) and the review-loop. The rule exists because
the first-finding stop is a silent failure: the reported finding is real, so the
review looks complete while unchecked sibling arms ship.

A **multi-arm construct** is any code where parallel branches handle peer cases:
a switch/match, an if/elif chain, a dispatch or routing table, an enum or
classifier handler, a validation cascade. Recognition test: could the defect you
just found plausibly repeat in a neighboring branch of the same construct? If
yes, it's multi-arm.

**The obligation, the moment one arm yields a finding:**

1. **Enumerate the arms** — count them. The count anchors the coverage claim.
2. **Check every sibling** for the same defect class, plus a quick pass for
   arm-local defects.
3. **Report coverage with the finding.** Every finding on a multi-arm construct
   names the construct, the arm count, and the per-sibling result:
   - `classify() (5 arms): arm 2 defective (this finding); arms 1, 3–5 checked — clean`
   - `…arms 4–5 NOT checked: <reason> — coverage gap`
   An unchecked arm is a stated gap the reader can see, never a silent omission.

**Siblings outside the visible diff:** the construct, not the changed line, is
the review unit. A diff-only reviewer reads exactly the construct body — one
bounded read, recorded as a diff-insufficiency per her own escape — not the
whole file. If even that read is unavailable, the finding carries the explicit
coverage-gap line instead.

**Severity:** a same-defect sibling is a separate finding at its own
Impact × Likelihood — sibling arms can differ in blast radius. The coverage
line itself carries no severity; it is evidence of completeness, not a finding.
