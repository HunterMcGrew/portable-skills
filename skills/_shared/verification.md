# Checks that cannot fail

Read this when your run grades something — a check, a suite, an acceptance criterion, an audit sweep, a count you're about to report. It is the sharper form of the edge recall the `## Sessions` Close bullet asks for: not "is there evidence," but **for every green result, could it have come out red?**

A check that cannot fail still prints a number, and the number reads exactly like a measurement — which is why this defect survives review. Every instance on this roster was written in good faith and reported a plausible figure. Three rules make the question answerable rather than rhetorical.

**A grade covering N members carries N observations, and the check emits its own cardinality.** `0 mismatches` means nothing without `143 rows examined` printed beside it — a denominator that isn't emitted wasn't counted, and a grade that reads one member while speaking for nine is the same defect wearing a bigger number.

**Ship the positive control inside the check.** Break the input, watch the check go red, restore it, watch it go green — and put that harness in the check itself (a `--selftest` mode), not in the write-up. Prose claiming a check was watched to fail is itself an assertion without proof; the control travels with the code or it doesn't travel.

**A check that derives its expectation from the thing under test proves agreement, not correctness.** Byte-comparing a generated file against a fresh call to its own generator passes at 27/27 however wrong the generator is — it satisfies both rules above and is still blind. Where the check and the artifact share a code path, only an independent re-derivation carries the weight: a different parser, a hand-computed expectation, a second tool.

**A control is written against the failure, not against the fix.** Whoever just wrote the fix plants, by default, the failure that fix already handles — a length floor calibrated against the tree it validates, a selftest whose planted string is chosen long enough that truncation can't over-forgive it, a sync-selftest covering five guards and not the property that actually broke, a red arm asserting polarity only. Each passes on day one and carries no information afterward, because the control is shaped like the repair instead of shaped like what got through — and a control shaped to miss a class of failure looks identical, at a glance, to one that catches it, until that class recurs. When a check cannot cover a named class of failure at all, that bound is reported where the check reports its result — never left standing only in a comment nobody re-reads.

**A control suite's denominator is the properties the thing claims, not the guards it happens to have.** Enumerate controls from what the code promises in its own contract, never from the branches it contains: a suite enumerated from the implementation is silent about the property nobody guarded, so deleting the lines that implement it leaves every control green and reports full coverage of a thing that no longer does what it says.

**A criterion the implementation fell short of is not reworded down to what shipped.** Rewording is the cheapest green available and it erases the only record that a gap existed; the criterion keeps its sentence and stays unmet, with the size of the shortfall recorded in its evidence rather than absorbed into its wording.

## Controls that prove nothing

A control has to keep the thing under test *in scope* while making it false. Two mutations look like controls and aren't:

- **Mutating the input so a different code path runs.** The check now reports a different failure, or skips the case entirely — that's a different check going red, not this one.
- **Mutating something the check normalizes away** — punctuation, casing, whitespace where the comparison strips it. The run stays green because nothing changed as far as the check can see.

Both leave the check looking fine with nothing tested, and "the control didn't fire" then reads as "the check is fine" when it means the opposite. Confirm the mutation landed in the file, then confirm it turns the run red.
