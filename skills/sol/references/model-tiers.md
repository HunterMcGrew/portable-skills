# Model tiers

Every dispatch carries a tier; this table is the default assignment:

| Tier | Model / effort | Personas |
| --- | --- | --- |
| `top` | Opus, effort `high` (`xhigh` for the hardest verify stages) | sol, eric, pixel — judgment cannot be front-loaded out of these; eric is **never dispatched below top** (the review firewall never runs cheap — PRISM `fec26cc`) |
| `worker` | Sonnet, effort `medium` (raise to `high` for harder execution stages) | everyone else, eli/sage/lilac/reese included — they execute against judgment already spent at plan time |

A run may pin a persona to a different tier at the run-plan gate (eric excepted — it never leaves `top`); the override is logged in the run log's `## Lanes` line. No config file yet — this table is the default policy.

**AC-verification dispatches are the standing exception that pins reese to `top`.** Grading finished work against an external rubric is judgment-heavy — the same reasoning that holds eric at top — so when reese is dispatched for AC Verification (not checklist-building), the lane runs at `top`. His checklist modes stay `worker`. (`/review-changes` stays worker by design — cheap first pass, expensive firewall — moving its tier is not this policy's call.)

**Iris pins to `top` for epic-grain retros only.** An epic-close retrospective audits an entire plan's history against its execution record — the same judgment class as eric's review or reese's AC grading. Per-PR light retros stay `worker`.

Workers are safe on Sonnet because the plan's detail bar front-loads every judgment call at plan time — a worker executes decisions already made, at the file-and-line level. Paying Opus rates to execute an Opus-grade plan is paying for judgment twice.

Mechanism caveat: the per-call `model`+`effort` dial exists **only in fleet mode** (`agent()` in a Workflow script takes both). The Agent tool takes `model` only; in-conversation runs inherit the session. So in subagent dispatches Sol applies the tier via the `model` override alone, and in-conversation phases simply inherit.
