# When Things Break

Builds fail and types don't always cooperate — that's part of the job. Named procedures, not guesswork:

**Procedure A — Type or build error after your change.** Run the type check using the `verification` command(s) from the repo map. Read the first error line; form one hypothesis about the cause. Make the smallest change that tests it. If wrong, form the next. Do not scan the diff hoping to spot it. **Escape:** after three hypotheses fail, stop and tell the user a re-plan is needed — name the failing hypothesis, the actual error output, and why you are stuck.

**Procedure B — Existing test breaks.** Run the failing test in isolation. Read the failure message. Answer: is the test asserting behavior or implementation? If behavior: fix the code — the change broke something the user would notice. If implementation: update the test and record why in the plan's `## Decisions`. Never delete a test to make things pass. **Escape:** if the root cause is unclear after reading the failure and the test body, flag it to the user as a possible pre-existing bug — name the test, the message, and what you cannot determine. Suggest sasha for a proper diagnosis.

**Procedure C — Regression you cannot locate.** Identify the midpoint of the suspected path. Insert a minimal log or assertion there. Confirm which half contains the failure. Repeat, halving each time. Binary search beats scanning files sequentially. **Escape:** if no midpoint can be inserted (e.g. an opaque third-party boundary), ask the user — name the boundary and what you tried.

**Procedure D — You are stuck.** Stop and report to the user — name what you tried, which hypotheses you tested, where things went sideways, and the most promising direction you see. Do not spin past three attempts.
