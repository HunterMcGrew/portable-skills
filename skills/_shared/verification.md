# Checks that cannot fail

Read this when your run grades something — a check, a suite, an acceptance criterion, an audit sweep, a count you're about to report. It is the sharper form of the closing battery's fourth question: not "is there evidence," but **for every green result, could it have come out red?**

A check that cannot fail still prints a number, and the number reads exactly like a measurement — which is why this defect survives review. Every instance on this roster was written in good faith and reported a plausible figure. Three rules make the question answerable rather than rhetorical.

**A grade covering N members carries N observations, and the check emits its own cardinality.** `0 mismatches` means nothing without `143 rows examined` printed beside it — a denominator that isn't emitted wasn't counted, and a grade that reads one member while speaking for nine is the same defect wearing a bigger number.

**Ship the positive control inside the check.** Break the input, watch the check go red, restore it, watch it go green — and put that harness in the check itself (a `--selftest` mode), not in the write-up. Prose claiming a check was watched to fail is itself an assertion without proof; the control travels with the code or it doesn't travel.

**A check that derives its expectation from the thing under test proves agreement, not correctness.** Byte-comparing a generated file against a fresh call to its own generator passes at 27/27 however wrong the generator is — it satisfies both rules above and is still blind. Where the check and the artifact share a code path, only an independent re-derivation carries the weight: a different parser, a hand-computed expectation, a second tool.

## Controls that prove nothing

A control has to keep the thing under test *in scope* while making it false. Two mutations look like controls and aren't:

- **Mutating the input so a different code path runs.** The check now reports a different failure, or skips the case entirely — that's a different check going red, not this one.
- **Mutating something the check normalizes away** — punctuation, casing, whitespace where the comparison strips it. The run stays green because nothing changed as far as the check can see.

Both leave the check looking fine with nothing tested, and "the control didn't fire" then reads as "the check is fine" when it means the opposite. Confirm the mutation landed in the file, then confirm it turns the run red.
