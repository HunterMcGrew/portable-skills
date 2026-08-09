# Slimming the roster for Opus 5

How to cut a skill down to what actually changes the model's behavior, and leave the rest to the model.

The roster is ~120,000 words across 30 skills. Every invocation loads `_shared/core.md` (2,350 words) plus one skill (1,354–6,955). Most of that weight was written for models that needed it. Opus 5 doesn't, and some of it now actively costs quality — not just tokens.

Each rule below carries an evidence tag:

- **[measured]** — from the THR-851 Winston bake-off (8 runs, single run per cell)
- **[Anthropic]** — from [Prompting Claude Opus 5](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/prompting-claude-opus-5) or the skill-creator guide
- **[inferred]** — reasoning from the above, not yet tested

Treat **[inferred]** as a hypothesis worth a run, not a mandate.

Running a slimming dispatch? Read `.slim-calibration.md` alongside this file. This guide is the rubric; that one is the accumulated cost of the lanes that already ran — each line a mistake paid for once — and it names the authority order when the two disagree.

---

## Part 1 — The cuts, ranked by leverage

### 1. Replace prescribed read sequences with the facts required **[measured]**

The single highest-leverage change found so far. Slim Winston's fixed startup batch — git context, plan lookup, architect manifest, matched docs, in that order — was replaced with exit-condition questions naming what must be *known* before evaluating. Same skill, one section:

| | Prescribed reads | Exit conditions |
| --- | --- | --- |
| External research calls | 0 | **17** |
| Chat words | 1,856 | **917** |
| Verification commands in plan | 11 | 12 |
| Dependency coverage | 8 prose mentions / 18 tasks | 14 / 14 explicit |

It found four correctness-critical facts nothing else in the experiment found, all independently verified — including that `wp_get_global_styles()` returns unresolved `var:preset|…`, a latent bug sitting in three of the four plans.

**The mechanism, stated precisely.** The always-on rules were never the problem. `working-principles.md` already spells out verify-at-source, and it produced zero research when loaded. A prescribed read batch doesn't suppress the rule — **it suppresses the rule's trigger condition**. The model never forms an external-system claim, because the reads never surface a question the repo can't answer. Name the facts instead and the gap becomes visible; the existing rule then fires on its own.

**"Four questions" is not the mechanism.** `_shared/core.md`'s Opening Orientation Battery is already four questions and produces no research, because its questions are about the *request* (Intent / Ambiguity / Bounds / Approach). Winston's worked because one of its questions was about **constraints originating outside the repo**. If you rewrite an orientation section and don't include a question the repo can't answer, you've changed the shape and kept the problem.

**How to spot it:** the section names files and an order. **What replaces it:** what must be true before you can do the work, phrased as a consequence — "load every architecture doc matching the diff, because a partial load produces a confidently wrong recommendation" — rather than as step 4 of a batch.

### 2. Delete Definition of Done checklists **[Anthropic]**

Anthropic's Opus 5 guidance is unambiguous:

> If your prompt contains explicit verification instructions ("include a final verification step for any non-trivial task," "use a subagent to verify"), remove them: instructions like these cause over-verification on Claude Opus 5, and removing them reduces wasted tokens with no loss in quality. The same applies to legacy harness scaffolding that adds separate verification steps.

26 of 30 skills carry a `## Definition of Done` block — 4,740 words in total, 30 to 424 words each, Winston the worst. Ten of Winston's twelve items restated instructions already given earlier in the same file.

The same section also covers self-correction: *"Avoid instructing re-checks it already performs ('double-check your answer,' 're-verify before responding'); like verification instructions, these compound with the model's own behavior and add cost without improving results."*

Grep targets beyond the DoD header: `before declaring done`, `before presenting`, `re-verify`, `verify both sections are present`.

**Keep the one line that names the deliverable.** "The updated plan is the deliverable; the `## Implementation Tasks`, `## Decisions`, and `## Acceptance Criteria` writes are the final act before stopping" is a scope statement, not a verification ritual. It survives. The checkbox list under it does not.

### 3. Cut every restatement **[Anthropic]**

Skill-creator: *"Keep the prompt lean. Remove things that aren't pulling their weight."* Winston states the AC gradeability bar three times — in the output format, again in Plan Mode step 7, again in two DoD blocks. Say it once, in the place the model is when it needs it.

The reliable test: search a phrase from any instruction. More than one hit outside a cross-reference means one of them goes.

### 4. Control verbosity with one explicit instruction, not with skill size **[measured] + [Anthropic]**

Holding fat Winston fixed and changing only the output style moved chat output 1,114 → 2,372 words, **+113%** — more than twice what the entire slim-vs-fat redesign moved (~500). Verbosity is a length instruction, not a byproduct of file weight.

Anthropic confirms the lever and separates two kinds of length: conversational verbosity, and files written to disk. Both belong in `_shared/core.md` once, in Anthropic's own phrasing, rather than in 30 skills:

> Match the length of written documents to what the task needs: cover the substance, but do not pad with filler sections, redundant summaries, or boilerplate.

That one matters here — the roster's deliverables are plans, specs, and reports.

**Order of operations:** freeze the output style before measuring any slimming work. Otherwise the style effect swamps the treatment effect and the numbers mean nothing.

### 5. Collapse output templates **[measured, weak]**

Slim Winston went 7 sections → 3 (verdict / findings / suggested approach) and still beat fat on every detail metric. Sections that get conditionally omitted anyway ("Omit if none," "Omit if no UI impact") are paying rent in every invocation to appear in some. Fold them into a named section that carries them when relevant.

Caveat: single run per cell, and this was bundled with other edits. Directionally supported, not isolated.

### 6. Don't tell a reviewer to be selective **[Anthropic]**

> If your review prompt says "only report high-severity issues" or "be conservative," the model may follow that instruction literally and report less; ask it to report everything and filter in a separate pass instead.

A grep of the roster turns up no instances today — this is a rule to not re-introduce, and one to check whenever a reviewer skill gets tuned for noise. The fix for a noisy reviewer is a filter pass, not a quieter reviewer.

### 7. Cap subagent delegation — already done, keep it **[Anthropic]**

`_shared/core.md` § Context budget already matches Anthropic's recommended guidance almost line for line, including "don't use a subagent to check your own work." No change needed. Noted here so nobody deletes it during a slimming pass.

### 8. Cut the personality essay; keep the voice **[measured]**

Fat Winston carries ~700 words of personality prose plus a ~1,300-word Cognitive Approach — four numbered lenses, each with a Trigger and an Escape. Together that's 30% of the file and the largest block in it.

Slim cuts it to four sentences (see Part 2), and slim won every detail metric in pass 2. That cut was inside the measured slim-vs-fat treatment, so this is evidence rather than a guess: **the essay wasn't load-bearing; the voice is.**

What survived is instructive. Two of the four cognitive lenses live on as one working sentence each — "prefer the smaller design" became a single instruction with its own guardrail, and "understand why the convention exists" became the required shape of a Decisions entry. The other two, plus every Trigger/Escape pair, were deleted outright. **Keep the discriminator, cut the elaboration around it.**

---

## Part 2 — The worked example: Winston, 6,757 → 1,459 words

A 78% cut that beat the original on every detail metric. Use it as the reference shape for *what* to cut — not for how much: Part 8 records this ratio as winston-specific, and the roster-wide projection built on it as wrong.

| Fat section | ~Words | Fate in slim |
| --- | --- | --- |
| Personality prose | 700 | → `## Voice`, four sentences (rule 8) |
| Cognitive Approach ×4 w/ Trigger + Escape | 1,300 | Two survive as one sentence each; two deleted |
| Startup batch (6 numbered reads) | 700 | → `## Orient`, four exit-condition questions (rule 1) |
| Output format (11 sections) | 1,700 | → three parts: verdict / findings / suggested approach |
| Plan Mode (9 steps) | 900 | → 6 items |
| Closing Ceremony Mode | 450 | Deleted — promotion is the auditor's lane. **The run reversed this and restored it compressed; the premise was wrong twice over — see Part 8** |
| Definition of Done (3 checklists) | 424 | Deleted (rule 2) |
| Purpose / when-to-use | 130 | Deleted — it's already in the description |
| A/P/C menu, Premise gate, Dispatched runs, Session close, Closing battery | ~600 | Deleted — except `## Dispatched runs`, which the run restored compressed; see Part 8 |
| Devil's Advocate (inline) | 200 | Extracted to its own 675-word skill |

**Three patterns worth copying.**

*Extraction over deletion.* Devil's Advocate didn't die — it became a skill that loads only when invoked. The standalone version is better than the inline one (four passes, an explicit "be honest when the plan holds" clause, a typed verdict) and costs nothing on the runs that don't need it. Progressive disclosure applied at the roster level rather than inside a file.

*Keep the test, drop the scaffolding.* Fat's detail bar was four nested bullets defining decisions vs keystrokes. Slim keeps the discriminator that does the work — "two competent implementers executing the task independently produce the same result" — and drops the taxonomy around it.

*Slimming is not purely subtractive.* Slim **adds** three things fat lacked, each concrete and each earning its line: acceptance criteria must name where in the product a tester goes to see the change; a chat-output cap on plan writes ("in chat just say 'AC written to the plan — 4 criteria'"); and a search-siblings-before-naming rule. Cutting 78% created room for the specifics that actually change output.

**One divergence to decide deliberately.** Slim Winston does not read `_shared/core.md` at all — it inlines the little it needs and drops the rest, including the pronoun declaration the core's House rules require. That is the opposite of Part 4's advice to push shared content into the core. Both are defensible: a standalone skill is genuinely portable and costs one file to load; a core-backed skill means a wording fix lands in 30 places at once. Pick one and apply it to the whole roster, because a half-migrated roster gets the costs of both. Note that the standalone route makes rule 4's length instructions per-skill work rather than a one-line core edit.

---

## Part 3 — What earns its place

Slimming is not deletion. These pay for themselves and should survive every pass:

- **Output templates** — a shape the reader depends on, and cheap to state.
- **Typed contracts** — the `acVerdicts` schema in `_shared/core.md`. Something downstream parses it; prose flexibility here is a bug. Note the existing single-shape-owner rule: quoted contracts fork.
- **`_shared/core.md` itself** — a wording fix landing in one place is worth the 2,350 words.
- **The plan gate**, run-control state files, pinned review ranges, the manifest-completeness rule.
- **Calibration reads that already say what they're for** — a read instruction paired with the fact it establishes is rule 1 done right, not a violation of it.
- **Escape conditions** — what to do when the work can't proceed. These aren't verification; they're routing.
- **The description frontmatter.** Skill-creator is emphatic: the description is the primary triggering mechanism, and Claude currently *under*-triggers skills. Slimming a body is fine; slimming a description costs invocations.

A stronger pattern than prose exists in-house already: `iris`'s `## Charter coverage` table forces every unanswered question into the rendered output. A gap that has to be typed into the deliverable is harder to skip than a gap mentioned in an instruction.

---

## Part 4 — Where cut content goes

Three destinations, in order of preference:

1. **Delete.** Verification checklists, restatements, and anything the model does unprompted. Most cuts land here.
2. **`_shared/core.md`.** Anything true for every persona — length calibration, delegation caps, response shape. Cross-cutting fixes land once.
3. **`references/` under the skill.** Rarely-fired modes that are real when they fire: `eric`'s worktree mode, `pixel`'s HTML-mockup mode, `sol`'s routing tables. Skill-creator's progressive disclosure — SKILL.md under 500 lines, with a clear pointer saying when to go read the reference.

A mode that fires on one invocation in twenty is paying full price on the other nineteen.

---

## Part 5 — Per-skill procedure

1. **Snapshot first.** `cp -r skills/<name> <workspace>/skill-snapshot/` — the baseline for the A/B is the current version, and you can't reconstruct it after editing.
2. **Find the orientation section** (rule 1). Rewrite to exit conditions, including one question about constraints the repo can't answer. This is the change most likely to matter; do it first and alone.
3. **Delete the DoD block** (rule 2), keeping any single line that names the deliverable.
4. **Grep for restatement** (rule 3) and cut the duplicates.
5. **Collapse the output template** (rule 5) if sections are conditionally omitted.
6. **Move rare modes to `references/`** (Part 4) with a pointer — or extract them as their own skill when they stand alone, the way Devil's Advocate did.
7. **Compress the personality block to a `## Voice` paragraph** (rule 8), keeping any cognitive lens that reduces to a single working instruction.
8. **Re-run the sync** — `sync.sh` and `render-agents.py` regenerate `codex-agents/`; edits there get overwritten.

Change one thing per measured run where you can. The bake-off's clearest confound was slim Winston's pass 2 changing output style *and* three hand edits at once, which made a +202% swing uninterpretable.

---

## Part 6 — Measurement protocol

Learned the hard way during THR-851; skipping any of these produced an invalid cell.

- **Freeze the output style** before measuring anything else. It outweighs the treatment.
- **Delete the skill directory** in the control worktree. Un-invoking is not enough — trigger phrases like "plan this out" auto-fire the skill and silently invalidate the control. This killed pass 1's a3 outright.
- **`.claude/skills/` is gitignored**, so it does not follow into a worktree. Copy it in.
- **Confirm in each transcript which skill actually loaded.** Don't infer it from the invocation.
- **Clean transcripts before counting** — strip `/context` dumps and expanded plan-write blocks.
- **Three runs per cell, minimum.** Single-run detail comparisons are weak evidence: two same-skill runs in pass 1 disagreed 0 vs 11 on sequence markers. Run-to-run variance is large enough to manufacture a finding.
- **Count what matters:** chat words, plan words, external research calls, verification commands, file paths cited. Research calls turned out to be the most diagnostic of the set and nobody was counting them at the start.

The skill-creator plugin has machinery for this — `scripts/aggregate_benchmark`, `eval-viewer/generate_review.py`, and a grader subagent — worth using rather than hand-counting a third time.

---

## Part 7 — Audit order

Ranked by suppression risk, not by file size:

1. **`clove`** (5,884) — arguably worse than Winston was. The implementer most needs framework verification and currently has the least surface for it.
2. **`eric`** (6,345) and **`briar`** (5,566) — reviewers, where a suppressed external lookup becomes a missed bug. Also the skills most at risk of acquiring rule 6's "be conservative" phrasing.
3. **`pixel`** (6,017) — prescribed reads, and design work leans on external convention.
4. **`reese`** (6,955) and **`nora`** (6,125) — largest in the roster; likely restatement-heavy given their overlap with Winston's AC contract.
5. **`_shared/core.md`** — a cut here lands in all 30. The Closing Re-Orientation Battery is the open question: item 4 already hedges with "the bar is honest reporting, not extra checking," but the battery as a whole is a closing verification ceremony of exactly the kind rule 2 removes. Worth isolating, and worth being careful with — the blast radius is the entire roster.

The unanswered question underneath all of this: **what does a skill add over the always-on rules?** The no-skill control in the bake-off produced 801 chat words, 18 tasks, and 15 verification commands — matching or beating both Winston versions on detail at a third of the output — and it did research the skills didn't. Its one durable weakness was task sequencing (2 sequence markers vs 7–8). The skill's measured marginal contribution was ~1,500 extra chat words for a better-sequenced plan.

That may justify the roster or may not, and the bake-off can't say: the control also got two clarifying questions answered mid-run that the other conditions didn't. **Control vs slim, three runs each, same output style, no edits between** is the experiment that settles it, and it should probably run before 30 skills get rewritten.

---

## Part 8 — What the run actually measured

The rubric above was applied to the whole roster on 2026-08-08. This section records what held, what didn't, and what only showed up under execution. It supersedes the projections in Parts 1–7 wherever they disagree.

### The projections were wrong about size and right about mechanism

| | Projected | Measured |
| --- | --- | --- |
| Roster total | ~45,000 (−62%) | **~102,000 (−16%)** |
| Typical load per invocation (core + one skill) | — | **6,441 → 4,896 (−24%)** |
| `## The run, in order` | — | **27 of 29 → 0** |
| Skills asking a question the repo can't answer | 2 | **2 → 14** |
| Definition of Done blocks | 26 | **26 → 1** |
| Trigger/Escape scaffolding | 147 | **147 → 12** |

**The 62% projection came from treating Winston as representative. It isn't.** Its bulk was personality prose, an 11-section output template, and a checklist — all near-fully compressible, hence 79%. Skills carrying reference density (Divio tables, story templates, framework matrices, mode skeletons) landed at 3–38%. Per-invocation load is the honest metric anyway: relocated content sits in `references/` and loads only when its mode fires.

**Word count was the wrong headline.** The two rows that matter are the run-order sweep and the external-question count — those are the measured mechanism from the bake-off, and they went to completion.

### Rule 1 is confirmed, and stronger than stated

Every one of the 27 `## The run, in order` sections turned out to be **pure restatement**. Agents removing them checked each step for content existing nowhere else and found none, across every file. That section never carried information; it carried a script.

**But removing it is only half the fix, and the half that gets forgotten.** Twenty-four skills initially got a clean non-prescriptive orientation with no outside-facing question — which leaves the verify-at-source rule without its trigger, the exact condition that produced fat Winston's zero research calls. A dedicated sweep took the count from 6 to 14, and a read-only audit judged the remaining 14 genuinely N/A with a stated reason each (handoff has no subject matter; sol is pure dispatch; theo's Deletion Test is inherently repo-internal; lex deliberately defers regulation questions to counsel). **Budget the second half as its own pass.**

The worst case found was clove, which carried a line instructing it to *skip* third-party library behavior — worse than silence. The fix separated two ideas that had collapsed into one bullet: don't write tests that pin third-party behavior, but do verify it before building on it.

### Rule 8 needs one correction

"Protected" applied to a cognitive lens means **keep the discriminator, drop the Trigger/Escape scaffolding**. One agent read it as "leave the block untouched" and landed at 10 surviving pairs where its siblings hit 0. The 12 that legitimately remain are genuine escape machinery — sasha's phase gates, zoe's named procedures — which Part 3 already protects.

### A deletion needs a successor, or it isn't a cut

Four sections left the roster with no replacement anywhere and live citers still pointing at them: `_shared/core.md`'s `## Servers and long-lived processes`, and winston's `## Closing ceremony`, `## Dispatched runs`, and Evidence-format gradeability bar. Every one was found by a reviewer rather than by the slimming pass, and every one was restored compressed rather than authorized after the fact.

Three questions separate a cut from a defect. Run them before deleting, not after:

- **Does anything else say this?** Not "could the model infer it" — is it *written* where the reader arrives. Winston's closing ceremony had four dispatchers (`review-loop`, `eric`, `iris`, `sol`) and no successor; `## Dispatched runs` left `grep -ni 'dispatch' skills/winston/SKILL.md` at zero while review-loop dispatched winston at three separate sites.
- **Does the evidence measure the right surface?** The servers-and-processes cut was justified by grepping all 29 skills for process mentions — which asks whether a skill *writes about* processes, when the rule governs what a persona *does*. Clove runs verification gates, briar runs builds, reese verifies against a running app; none of them names the bound locally, which is precisely why it belongs in the file all 27 read.
- **Is the proposed repair "repoint the citers"?** Then you are proposing N copies of a single-owner procedure — the fork the fragment pattern exists to prevent. Restore instead.

Restoration is compression, not reversion: each section came back shorter with every bound intact.

**Part 2's table is stale on exactly this point.** Its `Closing Ceremony Mode | 450 | Deleted — promotion is the auditor's lane` row records a deletion this run reversed, and the premise was wrong twice over — the ceremony is winston's, and zoe's auditor lane is *archiving*, which the ceremony explicitly does not do. Part 4's `references/` example naming the same section is stale for the same reason. Part 8 supersedes both.

### What the process cost

Twelve dispatch briefs contained a factual error about the file under edit — every one from writing against this audit's summary rather than the file. Agents caught all twelve: two refused to fabricate protected content that didn't exist, several followed the plan over the brief and said so.

Three mechanisms did the work, and they're the transferable part:

- **A word ceiling fights its own keep-list.** State what must survive and let the count fall out; mark any number an expectation, never a gate. Two implementers hit the conflict and reported it instead of silently compressing protected content — after one earlier pass, given a hard ceiling, did exactly that.
- **Authorized deletions must travel to the reviewer.** A reviewer flagged a dependency-verified deletion as a Major defect because its brief never said the cut was sanctioned.
- **One shared calibration file beats N bespoke briefs.** After the errors were traced to a common cause, the standing rules moved into a single file every dispatch reads. The next brief error was caught upstream by an agent citing the authority order, rather than in ratification.
- **Governance follows the surface that changed a file, not the file's lane label.** Two plans divided the roster by file, and one execution commit slimmed two files whose file-level scope lines disclaimed them — 121 removed lines that neither plan's deletion audit ever classified, and it took nine review passes to notice. A scope line naming files is a prediction; the diff is the fact. Assign governance by the surface that did the changing and the hole closes without redrawing anyone's file list.

### Verification traps worth stealing

- **`grep -c <pat> && <next>` is a broken absence check.** Zero matches exits non-zero and silently kills the rest of the chain — it produced a falsely-reported exit code. Use `! grep -q`, pair every absence check with a positive control proving the probe reached the file, and read printed values (`wc`, `grep -c`) rather than `$?`.
- **`sed -n '/^---$/,/^---$/p'` false-positives on frontmatter** for any file whose body contains a `---` horizontal rule. Use the awk form.
- **A grep for the right string is not a check for the right structure.** Winston's port passed `grep -q 'he/him'` but `render-agents.py` correctly refused to generate its toml: a carried-over H1 had displaced the persona declaration from the first body line. The deterministic build caught what the probe couldn't.
- **The renderer only scans the SKILL.md body** for `_shared/<name>.md` citations. A citation relocated into `references/` silently drops that fragment from the generated surface. The sibling arm bites the same way and was missed for three passes: the relocated `references/*.md` files themselves — 15 files, 4,384 words — reached no generated toml at all until the renderer was taught to inline them on the same terms.
- **A guard whose file list is enumerated falls behind the surface it guards.** The profile-path check named `skills/*/SKILL.md` plus one fragment; the tree then grew 21 inlinable files it never read, while the README claimed it fired "anywhere under `skills/`". Glob the surface (`skills/**/*.md`) so adding a file widens the guard by construction, and plant one labelled self-test control per file class so a future narrowing fails a control instead of reporting green over a shrunken denominator.
- **A citation is unverifiable only after you've looked in the repo it names.** Four commit shas were flagged as stale references because they were absent from this repo and its sibling — all four resolved in the repo their own `PRISM <sha>` label named. Read the label before writing the finding.
- **File-disjoint lanes are safe to merge, not safe to measure merged.** "Exactly two tomls changed" is a *delta* assertion, readable only in a tree that isolates the change. One uncommitted shared-fragment edit turned that two-file signal into 27, and a sibling lane's output does the same. Measure in the lane's own worktree, record the number there, and treat the merged tree as unmeasurable for that criterion.

### Still unanswered

The control-vs-slim experiment never ran, and the roster was rewritten anyway on an explicit call. **What a skill adds over the always-on rules remains unmeasured** — Part 7's question stands, and now stands against a slimmed roster rather than a fat one.
