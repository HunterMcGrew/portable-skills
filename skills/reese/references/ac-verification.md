# AC Verification Mode

> Executed grading of a plan's acceptance criteria against the branch diff — per-criterion verdicts with typed evidence, not a tester checklist.

This mode consumes the gradeability bar winston authors: stable IDs and falsifiable Evidence sub-bullets, each tagged `machine` or `human`. Reese follows that format and never re-specifies it — winston owns the Evidence format, and the report-back's `acVerdicts` field shape is owned by `_shared/ac-verdicts.md`. This mode owns only the verdict *semantics*.

1. **Resolve the diff at the chain position.** Reese runs *before* the PR exists — resolve the change set from the branch, never `gh pr view`: `origin/<default>..<branch>` (or the worktree diff). Read the plan's `## Acceptance Criteria`. Commands come from the repo map's `verification` role, not guesses.
2. **Walk criteria by ID, following each Evidence sub-bullet.** Execution is **read-only**, operationally defined: no writes to tracked files, no mutating flags (snapshot updates, migrations, seeders); ephemeral build artifacts are tolerated. **Tree-clean discipline:** run `git status` before and after — the tree must be unchanged, or the run is invalid (a dirtied worktree poisons sol's own `git diff` ratification). The "tree unchanged" invariant governs the **graded source / diff under test** — Reese never mutates the code or AC being graded, since that's exactly what would make a broken change look passing or poison sol's ratification over the committed diff. His own mandated deliverables — the QA report under `<plans>/qa/` and the single `## History` pointer line, even when the plan is part of the graded diff — are the mode's outputs, not graded surface, and are exempt. When a criterion's Evidence turns on a tool's exit code or output format — a suite that exits 0 while skipping, a runner that calls "0 passed" success, a linter whose non-zero exit means warnings, not failures — confirm that meaning against the tool's own documentation or a deliberate probe before grading against it. A signal read wrong is a confident MET that's simply wrong.
3. **Render a verdict per criterion** (below), each stamping the SHA it was rendered at.

### The verdict contract

- **MET** — the Evidence procedure ran and produced its expected observation.
- **UNMET** — the procedure ran and produced the failure signature (or any result that isn't the expected observation). A failing evidence run is UNMET; a run that *can't happen* is not (see UNGRADEABLE).
- **UNGRADEABLE** — the criterion couldn't be graded. Always carries a required `reason`. UNGRADEABLE explicitly covers the evidence *source* being insufficient, dead, or unfalsifiable — not just the criterion text:
  - `ac-defect` — the criterion or its Evidence line is vague, unfalsifiable, or missing, and Reese can't derive an obvious evidence source.
  - `harness` — the evidence command errored, couldn't run in the worktree, or disagreed with itself across two runs (a flake). A signal that can't run is **not** a failing signal — capture the error and mark `harness`, never UNMET. Grading a broken harness as UNMET dispatches clove against a signal, not a defect.
  - `dead-reference` — the Evidence names a command or path that no longer resolves.
  - `requires-human` — a `human`-tagged criterion (visual, timing, feel). Not an AC defect — routed to the merge gate as a checklist item, never graded.
  - `converted` — a criterion that survived two fix cycles (set by the loop, not born here).

**Evidence is typed, never scored** — `executed` (a re-runnable command) > `inspected` (file-state) > `demonstrated` (self-reported). No per-criterion confidence grade: a confidence dial would reopen the partial-credit door binary grading exists to close. The type ratio is itself a signal — wall-to-wall `demonstrated` METs is the rubber-stamp tell.

**Missing Evidence sub-bullet (the back catalog).** Criteria authored before the gradeability bar carry no Evidence line. Reese may **derive** an obvious evidence source, labeled `(derived)` in the citation; UNGRADEABLE(`ac-defect`) only when he can't. This keeps a day-one flood of side-findings from training everyone to ignore the channel.

**No prescribed fixes.** An UNMET is a failing-test report, not a diagnosis — root cause is clove's (or sasha's) job. Each UNMET entry carries: the stable ID + the criterion verbatim; the exact procedure followed (command + exit code, or file:line, or behavior attempted); concrete expected-vs-observed (quoted output, not "not met"); and the evidence type. Location observations are fine; "change X to Y" is lane drift.

### The report

Save one report per ticket to `<plans>/qa/ac-verification-<ticket-id>.md`:

- **Header** pins the commit SHA, date, and environment — a false MET must be distinguishable from "code changed after grading."
- **Verdict table** up top: ID / verdict / evidence type / citation. Captured command output goes below the table. Every verdict stamps the SHA it was rendered at.
- **Re-checks update the table and append a dated re-check log entry** — never overwrite history. Refuted verdicts are data, and the two-strike budget needs the trail.
- **Human-tagged criteria** get a dedicated "criteria awaiting human verification" mini-checklist section — surfaced at the merge gate, never graded, never silently dropped.

**Re-check scope.** On a fix re-check, re-grade the previously-failed criteria **plus any previously-MET criterion whose evidence citations intersect the fix diff's file list** — fixes regress neighbors, which is why QA exists. Before returning the final all-clear, do one full re-run of all machine evidence (read-only and cheap by construction) so the final table is graded at a single SHA.

### After saving

Append one line to the plan's `## History`: date, report path, and the MET/UNMET/UNGRADEABLE counts. The plan is the content bus — eric, briar, and iris discover the report through this pointer; `<plans>/qa/` is invisible to them otherwise.

### The report-back verdict (dispatched)

The report-back verdict is **`done` whenever verification ran to completion** — the per-criterion results ride the `acVerdicts` field (shape per `_shared/ac-verdicts.md`, never re-quoted here), mirroring the review-loop precedent where reviewers return `done` with findings and sol routes on the findings. Two exceptions:

- **no `## Acceptance Criteria` section at all → `blocked`** — there's nothing to grade.
- **every criterion UNGRADEABLE → `needs-replan`** — the plan is the problem; zero criteria were verified, and advancing a lane verified by no one is exactly what this guards against.

A disputed verdict isn't Reese's to resolve: if clove disputes an UNMET, that routes through clove's `needs-replan` to winston (the criterion's owner), who sharpens the criterion or its Evidence. Reese re-grades against the corrected version.
