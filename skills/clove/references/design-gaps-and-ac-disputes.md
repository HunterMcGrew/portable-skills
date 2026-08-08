# Design Gaps

If you hit a UI gap during implementation — missing state, unclear layout, no spec for how something should look or behave — surface it:

> "There's no design spec for [this state/interaction]. Want to define it together, or should I make a judgment call and keep going?"

If you make the call, record it in `## Decisions` so it's visible and reversible.

# AC Adjustment Proposals

When you discover during implementation that an acceptance criterion can't be met as written, needs to be different, or is missing a case:

1. Flag the behavior change explicitly — silent changes undermine trust and make AC tracking impossible.
2. Add an `### AC Adjustment: [title]` entry under the plan's `## Acceptance Criteria` with **Original**, **Proposed**, **Reason**, and **Status:** `proposed`.
3. Notify the user: "I've proposed an AC adjustment — [short description]. Accept or reject before I proceed?"
4. Wait for the response before implementing the affected behavior. Proceed with unrelated work in the meantime if possible.

# Disputing a graded UNMET

When reese's AC verification returns an UNMET Clove believes is wrong — the criterion is ambiguous, or the evidence tests the wrong thing — the answer is **never an appeasement fix** (a code change with no requirement behind it). Return `needs-replan` quoting both readings: what the criterion says, what the code does, and why each is defensible. winston owns the criterion and arbitrates by sharpening it or its Evidence; reese re-grades against the corrected version. Two competent readers reaching opposite verdicts is the definition of an ambiguous criterion — the fix is a clearer criterion, not code bent to satisfy a bad one.
