# The acVerdicts contract

Read this when reese is dispatched to grade a plan's acceptance criteria, and when sol, eric, or iris consumes that report-back. This file is the single shape-owner for the `acVerdicts` field — everyone else (reese, sol, eric, iris) points here; nobody re-quotes the schema, because the roster's history shows quoted contracts fork.

`acVerdicts: [{ id, criterion, verdict, evidenceType, evidence, reason? }]` — one entry per criterion:

- `id` — the stable criterion ID (`AC-1`, `AC-2`, …) assigned at authoring.
- `criterion` — the criterion text, verbatim.
- `verdict` — `MET` | `UNMET` | `UNGRADEABLE`.
- `evidenceType` — `executed` (a re-runnable command) | `inspected` (file-state) | `demonstrated` (self-reported). Typed, never scored — there is no per-criterion confidence grade.
- `evidence` — the procedure followed and its observed result (command + exit code + output line, file:line, or behavior).
- `reason` — **required when `verdict` is `UNGRADEABLE`**, one of `ac-defect` | `harness` | `dead-reference` | `requires-human` | `converted`; omitted otherwise.

Escape verdicts are a dispatch mechanism. In an interactive session the same conditions — a blocking gap, a missing input, a bound you can't cross — are flags raised to the user, not verdicts.

The report-back verdict itself is `done` when verification ran (`blocked` with no AC section, `needs-replan` when every criterion is UNGRADEABLE); the per-criterion detail rides `acVerdicts`, and sol routes on deterministic predicates over the field — never re-judging a criterion.
