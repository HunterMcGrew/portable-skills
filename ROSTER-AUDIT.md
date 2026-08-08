# Roster audit — every skill against the slimming rubric

Audited 2026-08-08 against [SLIMMING-GUIDE.md](SLIMMING-GUIDE.md), using slim Winston (1,459 words) as the target shape and fat Winston (6,757) as the before.

> **Correction — four entries below read a stale tree.** The audit ran against local `main` at `1037460`, which was five commits behind `origin/main`. PRs #5 and #6 merged 2026-07-31 and changed exactly the review machinery: **review-loop 1,634 → 2,483 (+52%)**, eric 6,345 → 6,497, briar 5,566 → 5,734, plus a new `skills/_shared/review-exhaustiveness.md` (284w) the core-intersection analysis never saw. The "review-loop is already clean" verdict is the one that needs re-checking — it is half again larger than the version graded here. Every other skill's numbers are unaffected. The tree is now current at `2a2cdc3`; the delta re-audit is tracked as lane-1 of the implementation run.

**Roster total: 119,735 words across 29 skills.** Applying the rubric everywhere lands it near 45,000 — a ~62% cut.

## The headline: this isn't 29 problems, it's four

The roster was clearly built from a template, and the template carries the defects. That's good news — the fix is four systematic passes, not 29 bespoke rewrites.

| Pattern | Prevalence | Rule |
| --- | --- | --- |
| `## The run, in order` — a numbered 6-to-10 step prescribed sequence | **27 of 29 skills** | 1 |
| A `## Startup` prescribed read batch | **22 of 29** | 1 |
| Numbered cognitive lenses with `**Trigger:**` / `**Escape:**` pairs | **147 Triggers, 165 Escapes** across 27 skills | 8 |
| `## Definition of Done` checklist | **26 of 29**, 4,740 words | 2 |

Only `sol` and `zoe` sit outside the lens pattern. `zoe` is the roster's best-behaved file already — its named Procedures A–D carry reasoning tied directly to mechanics, which is what rule 8's "keep the discriminator" looks like when done right. Use zoe, not winston, as the in-house model for that specific section.

## Finding 1 — the research suppression is near-total

The diagnostic question from rule 1: *does the skill ever ask something the repo itself cannot answer?*

**Across all 29 skills, exactly two do: `kora` and (partially) `lex`.**

- **kora** — confirmed. Its `## Research modes` instructs, absent a deep-research capability, to web-search from multiple angles and verify each load-bearing claim against two independent sources. This is the roster's only unambiguous external-research trigger.
- **lex** — weaker than expected. It detects a `deep-research` capability, but its degrade path is "verification was not performed — have an attorney verify," not kora's fallback sweep. It defers rather than researches.
- **vera** — actively discouraging. When no research capability is present it tells Vera to state the result "isn't independently web-verified" rather than to go verify it.

Every other skill — including all four reviewers and implementers where a wrong framework assumption is most expensive — reads only repo-internal sources. This is the same condition that produced zero research calls from fat Winston, and the pass-3 rewrite showed the fix is one section.

Two skills have a domain that plainly needs outside facts and no instruction to get them: **penny** (no salary or labor-market benchmark lookup anywhere, despite writing headcount plans) and **eric/briar** (framework behavior treated as model-resident knowledge rather than something to verify at source).

## Finding 2 — the business layer is nine copies of one file

`vera, kora, ellis, charlie, quinn, tess, remy, penny, lex` are structurally identical: 5 lenses (vera has 6) each with Trigger+Escape, a 4–5 step Startup, a 141–221 word DoD, a "created lazily, never seeded empty" rule restated 2–3×, and a deliverable that is a section of the strategy doc. Every one lands at ~1,200–1,300 words after the rubric, from 2,518–3,056 today.

**This is one edit applied nine times.** It's also the lowest-risk place to start: business artifacts have no build to break, and a bad slim shows up as a worse document rather than a broken pipeline.

## Finding 3 — restatement is worst where the rule is most important

The pattern is consistent and slightly perverse: the more load-bearing a rule, the more times it's restated, as if repetition were enforcement.

- **eric** — "never approve/merge" appears 4–5× (description, persona bounds, twice in After-the-review, then an entire `## Role Boundary: Approval Is Human` section).
- **briar** — the `## Justification Review` section (~300 words) restates lens #6 (~100 words) almost entirely. ~400 words duplicated outright.
- **pixel** — the five UI states appear 4×; accessibility-at-design-time 3×; mobile-first 3×.
- **tess** — loop-closure-to-vera stated 4× (lens trigger, Ownership, Next persona, DoD).
- **lilac** — "never post without confirmation" 4×; markdown-not-mrkdwn 3×.
- **clove** — "never commit to default branch" 3×; Chesterton's Fence 3×.
- **eli** — "verify every claim against source" 4×.

Repetition isn't what makes Opus 5 comply; a stated reason is. Say it once, where the model is when it needs it.

## Finding 4 — DoD blocks are pure restatement, and pixel's is the worst

26 skills, 4,740 words. Almost every one restates instructions already given. Three deserve specific mention:

- **pixel** (~230 words, 18 checkboxes across three separate checklists) explicitly instructs *"Before presenting, walk the relevant checklist; address each item or note it as not applicable with reasoning"* — a textbook instance of what Anthropic's guidance says to delete.
- **eli** (~230 words, 16 checkboxes) plus a separate "Pre-save self-lint" pass — two verification ceremonies in one file.
- **briar** (~35 words) and **zoe** (~35 words) are already at the target: a line naming the deliverable, no checklist. Copy their shape.

## Per-skill detail

Word counts are current; targets apply rules 1–8.

### Dev core — highest suppression risk

| Skill | Now | Target | Orientation | DoD | Biggest cut |
| --- | --- | --- | --- | --- | --- |
| clove | 5,884 | ~2,000 | SUPPRESSIVE (51–61, 189–200) | 337–349 | 11-lens block (62–138, ~1,600w) |
| eric | 6,345 | ~1,850 | SUPPRESSIVE (49–59, 166–296) — literal `gh`/`git` batches | none (already) | worktree mode → references/; batch scripts → exit conditions |
| briar | 5,566 | ~1,850 | SUPPRESSIVE (43–53, 182–254) | 392–394 (already slim) | duplicated Justification Review (305–316) |
| pixel | 6,017 | ~2,150 | SUPPRESSIVE (56–66, 210–220) | 319–346 (3 checklists) | 8-lens block (68–156, ~1,850w) |

### The four largest

| Skill | Now | Target | Orientation | DoD | Biggest cut |
| --- | --- | --- | --- | --- | --- |
| reese | 6,955 | ~4,000 | SUPPRESSIVE (48–57, 163–169) | 374–401 (336w) | AC Verification mode (263–360, ~2,400w) → references/ |
| nora | 6,125 | ~3,750 | SUPPRESSIVE — **17-step batch (202–242), the largest prescribed sequence in the roster** | 362–377 | rewrite that batch to exit conditions |
| sasha | 5,696 | ~3,400 | SUPPRESSIVE (183–222) | 443–460 (291w, 18 items) | 9-principle block (62–119, 865w); 5 of 9 duplicate Debugging Standards |
| sol | 5,685 | ~4,800 | PARTIAL — short, and its state-recovery step is real | 315–324 (124w, mostly scope statements) | **relocation, not deletion** — Fleet runs + Model tiers → references/ |

Three notes on these. **sasha is the most alarming gap in the roster**: a debugger is precisely where "does this library actually behave the way the code assumes?" pays off most, and nothing in the file poses that question. **sol is protected** — its routing tables, ratification logic, budgets, and run-log schema are run-control machinery; its slimming is almost entirely moving Fleet runs and Model tiers to `references/` with content preserved. **nora's DoD is the smallest of the four at 172 words** yet still 11 checklist items, which tells you the checklist habit is independent of file size.

Restatement in this group is extreme: sasha states "never fixes source" at **7 sites** and "root cause not proximate cause" at **6**; nora states Definition of Ready at **5**; sol states "never merges" at **4**. Sol's are hard-invariant restatements rather than task instructions, which is the defensible end of the spectrum — but four copies is still three too many.

### Dev remainder

| Skill | Now | Target | Orientation | Biggest cut |
| --- | --- | --- | --- | --- |
| eli | 4,759 | ~1,400 | SUPPRESSIVE (42–52, 144–232) | Startup sequence → exit conditions; DoD + self-lint |
| mira | 4,742 | ~1,300 | SUPPRESSIVE (55–65, 194–206) | 8-lens block (67–139, ~1,750w = 57% of file) |
| iris | 4,552 | ~2,200 | SUPPRESSIVE (50–63) but procedure is genuinely mechanical | two report templates + Procedures A–E |
| sage | 4,114 | ~1,700 | SUPPRESSIVE (50–59, 151–171) | docx/pdf/gdocs mechanics → references/ |
| parker | 4,027 | ~2,400 | SUPPRESSIVE (33–45, 254–262) | three fully-spelled review axes (193–211) |
| theo | 3,803 | ~2,200 | PARTIAL — already question-framed at 102–111 | walk-state JSON + resume table (145–187) |
| zoe | 3,433 | ~2,900 | PARTIAL — batching is real parallelism | worktree lane → pointer; state schema |
| lilac | 3,313 | ~1,900 | SUPPRESSIVE (38–50) — heavy for a fetch-and-format task | DoD; lenses 4 & 6 are formatting rules, not judgment |
| ren | 2,731 | ~2,300 | PARTIAL — a scout loop, not a read batch | 6 heuristic Procedure blocks → one table |

### Business layer — one template, nine files

All PARTIAL orientation, all with a 5-lens block as the biggest cut, all targeting ~1,200–1,300 words.

| Skill | Now | Lens block | Notable |
| --- | --- | --- | --- |
| penny | 3,056 | 895w | duplicate Procedures A–D overlap the lens Escapes; no market-benchmark lookup |
| vera | 3,004 | 915w | 6 lenses not 5; actively discourages external verification |
| tess | 2,906 | 939w | largest lens block in the batch; loop-closure stated 4× |
| quinn | 2,841 | 852w | longest DoD in the batch (221w); "never sends" 3× |
| kora | 2,834 | 895w | **the roster's only real external-research trigger — protect it** |
| ellis | 2,711 | 708w | Procedures A–D are genuine escape conditions; keep |
| lex | 2,697 | 680w | disclaimer-first rule is load-bearing repetition; keep that one |
| remy | 2,604 | 847w | leanest on restatement already |
| charlie | 2,518 | 872w | messaging-before-SEO stated 2× |

### Utilities — already clean

`handoff` (1,354) and `review-loop` (1,634) are the two skills that pass the rubric today. Both explicitly opt out of the orientation batteries and say why; both have no persona, no pronoun declaration, and no DoD header. Their numbered steps are domain-necessary sequencing that names its own reason, not a read batch — which is what rule 1 compliance actually looks like.

Two small notes. `handoff`'s "Pre-report check" (128–140) is a four-point DoD in different clothing, though scoped to the artifact it just wrote rather than a generic re-verify — a later-pass candidate, not urgent. And `review-loop` *is* a verification ceremony by construction, which is fine: rule 2 targets redundant self-checks bolted onto a task, and here the ceremony is the task the user explicitly asked for.

They're also the model for the new `devils-advocate`: no voice, no greeting, no batteries, no toml.

## The shared core: yes, one core works

The question was whether every skill truly needs the same core. **It does — and the dev-vs-business split isn't real.** All nine business-layer skills genuinely use the repo map, the plan-file conventions (via the strategy doc), the batteries, response shape, and house rules exactly as the engineering skills do. A separate business core would solve a problem that doesn't exist.

**Why not two cores, stated plainly.** After the trim below, what business skills don't need comes to roughly 116 words — session close (7 of 9 have no lessons role) and the dispatch pointer. Splitting a ~1,500-word core in two to save 116 words per invocation buys almost nothing and costs a maintenance surface this repo has already been burned by: `render-agents.py`'s own header records the last two-surface drift — *174 lines that landed in `skills/` and never made it across, 63 stale lines left over, one stale description field, none of it visible to a plain diff.* A second core recreates exactly that failure mode.

The mechanism that does work is the one already in the repo, in three forms:

1. **Opt-out of a section** — handoff and review-loop skip the batteries and say why, in one line. A business skill with no lessons role does the same for session close.
2. **Opt-in fragments** — `_shared/worktree-safety.md` is read by exactly four skills (clove, eric, sol, zoe). `_shared/ac-verdicts.md` becomes the second, read by exactly four (eric, iris, reese, sol).
3. **Single-owner content lives with its owner** — retros/, audits/, design/, conductor/ paths move out of core into iris, zoe, pixel, and sol respectively.

One core, opt-out where a section doesn't apply, opt-in fragments for shared machinery a minority needs. Nothing here requires a second core.

The actual problem is that `core.md` carries content **nobody universal needs** — single-owner paths and one dead section. Fix that and one core serves all 29.

| Section | Words | Verdict |
| --- | --- | --- |
| Repo map | 198 | **UNIVERSAL** — keep |
| Plan files | 179 | **UNIVERSAL** — keep |
| Private state, generic create-on-first-write rule | ~60 | **UNIVERSAL** — keep |
| Private state, the path enumeration (retros/ audits/ design/ conductor/ state/ business/) | ~117 | **CUT** — one owner each, and each skill already restates its own path locally |
| Opening Orientation Battery | 264 | **MAJORITY** — keep; handoff and review-loop opt out by design and say so |
| Mid-flight re-anchors | 103 | **MAJORITY** — keep |
| Closing Re-Orientation Battery | 196 | **CUT to one line** — see below |
| Context budget | 124 | **UNIVERSAL** — keep (background operating rule; low citation is expected) |
| Servers and long-lived processes | 109 | **DELETE** — zero dependents |
| Dispatching a sibling persona | 159 | **MINORITY** — trim to a pointer; sol is the only real dispatcher |
| acVerdicts contract | 229 | **MOVE** to `_shared/ac-verdicts.md` |
| Session close | 76 | Minority-leaning but cheap and self-excusing — keep |
| Response shape | 225 | **UNIVERSAL** — keep |
| House rules | 250 | **UNIVERSAL** — keep |

**2,350 → ~1,500 words**, and every skill loads it, so this is the single highest-multiple edit available.

Three findings worth stating plainly:

**Servers and long-lived processes has zero genuine dependents.** I verified this directly rather than taking it on report: grepping all 29 skills for `dev server`, `long-lived process`, `npm run dev`, `localhost:`, `tear down`, `kill the server` returns nothing. Every apparent hit in the original sweep was "server-side" or "backend API" prose. No skill in this roster launches, reuses, or tears down a process. It's 109 words that appear to be scaffolding from a different repo.

**The acVerdicts hypothesis was exactly right.** `grep -l acVerdicts` returns precisely `eric, iris, reese, sol` — four skills, no false positives. It moves to `_shared/ac-verdicts.md`, read only by those four. The single-shape-owner rule that keeps it centralized still holds; it just doesn't need to be in the file all 29 load. **The precedent already exists in-house**: `_shared/worktree-safety.md` is read by exactly four skills (clove, eric, sol, zoe) and nobody thinks that's odd. ac-verdicts is the same pattern.

**The Closing Re-Orientation Battery is the open question from the guide, and the answer is cut it.** It's an unconditional four-question ceremony fired at the end of every run across the entire roster — the exact shape Anthropic's guidance says to remove. Its own item 4 already hedges with "the bar is honest reporting, not extra checking," which is the tell that the section knows it's on thin ice. Collapse it to one line — *close by naming scope drift, silent assumptions, and unproven claims, in the same message as the report-back* — and drop the scaffold. This is the change with the widest blast radius in the whole audit, so it's the one to measure rather than assume.

## Persona splits

The question was whether any persona does too many jobs. Most don't — what looks like sprawl is usually sequential stages of one deliverable (iris gathering evidence then writing dialogue; parker interviewing then drafting). Those stay.

Three are genuine — a *different kind of thinking* bolted onto the core job:

1. **winston's Devil's Advocate → extracted.** Done. An architect arguing against their own recommendation in the same pass is the clearest case in the roster, and slim Winston already drops the section. See below.
2. **zoe's worktree-hygiene lane** (188–190) is an opt-in lane bolted onto a plan-audit persona, already pointing at `_shared/worktree-safety.md`. Reduce to a pointer or split it out.
3. **sage's document generation** (232–239) — docx/pdf/gdocs mechanics are a different kind of work from changelog categorization. `references/`, not a split.
4. **nora's Cycle View and Duplicate Finder** (276–297) — sprint dashboard reporting and fuzzy similarity matching, bolted onto a ticket-readiness persona. Neither is ticket setup. `references/`.

**reese's AC Verification is the strongest split candidate in the roster and I'd still not split it.** By the test, it qualifies cleanly: deterministic evidence-grading against a rubric is a different kind of thinking from generative tester-facing scenario writing, and at ~2,400 words it's 35% of the file. But it carries the typed `acVerdicts` contract, and sol, eric, iris, and winston all reference reese-as-AC-verifier by name. Splitting means changing a dispatch contract in four other files to buy a file-weight win that `references/ac-verification.md` delivers for free. Take the reference extraction; revisit the split only if the two modes start diverging in their own right.

Deliberately **not** splitting:

- **briar's adversarial self-critique** — it *is* the persona's purpose (compensating for self-review's blind spot), not an extra job.
- **eric sampling reese's AC grades** — meta-verification, but it's the review's job to check its inputs.
- **clove disputing a graded UNMET** — adversarial, but small and structurally necessary.
- **The capability-detection blocks** in every business skill — these look like a second job (tooling orchestration vs. analysis) and appear in all nine. That's a sign they belong in the shared core, not that nine personas each need splitting.

## The Devil's Advocate: utility, not persona

Built at [skills/devils-advocate/SKILL.md](skills/devils-advocate/SKILL.md), ported from the slim draft.

**It gets no name and no voice, on purpose.** A persona is a point of view you *address* — "Winston, is this right?" The skeptic is never addressed; it's applied to an artifact and hands back findings. It has no conversation, no handoff, and no lane in a run. The roster already has this category: handoff and review-loop are utilities with no persona.

There's a sharper reason than taxonomy. The skill's own stated failure mode is theater — "a page of hedged objections that lets everyone feel rigorous while changing nothing." A named character with quirks and dry humor is an invitation to *perform* skepticism. Giving it a personality works directly against its one job.

This also falls out of the build system for free: `render-agents.py` keys off the persona declaration line, so a utility gets no `codex-agents/` toml by construction. Confirmed — regenerating produces 27 tomls, unchanged.

### Does the skeptic work for anyone?

Not "anyone who plans." The test is narrower and more useful: **does this artifact commit to a decision before the evidence exists?** That's what an adversary can move. Artifacts already graded against evidence can only be re-checked, and re-checking checked work is exactly the over-verification rule 2 removes.

**Worth challenging:**

| Persona | Artifact | Why it fits |
| --- | --- | --- |
| winston | plan + decisions | canonical case |
| parker | PRD | initiative grain, expensive to be wrong |
| vera | strategy, OKRs | highest-stakes, least-verifiable artifact in the roster |
| ellis | pricing / unit economics | assumption stacks — the *best* fit; the skeptic's verified / checkable / unfalsifiable output is literally a model audit |
| kora | TAM, sizing, competitive claims | sizing methods hide their assumptions |
| sasha | root-cause diagnosis | "what has to be true for this to work" reads as "what has to be true for this to be the root cause" |
| ren | refactor proposal | the deletion-test argument is an argument, so it can be argued with |
| theo | architect docs, ADR candidates | decision records |
| mira | user stories | *borderline* — added on the audit's evidence that stories are a challengeable requirements artifact winston and clove build against |

**Not worth challenging:** eric, briar, reese (already adversarial or already evidence-graded — a skeptic here is a re-check of a re-check); nora (ticket readiness is a gate with its own checklist, not a decision); clove (tests and review verify implementation better than argument does); sage, lilac, iris, zoe, eli (derivative of decisions made elsewhere — challenge the decision upstream instead).

**pixel is the borderline case.** A design spec does commit ahead of evidence, and it routes through winston already. But the useful challenge is heuristic- and accessibility-shaped, which pixel owns. Reach for the skeptic only when the spec carries a product bet rather than a layout choice.

## Sync

`sync.sh` already covered all three targets — `~/.claude/skills`, `~/.claude-work/skills`, and `~/Downloads/portable-skills-backup`. The real gap was elsewhere:

**Output styles were never synced.** `output-styles/scannable.md` lives in the repo and `sync.sh` never installed it. Given the bake-off measured the output style as a *larger* lever on response shape than the entire skill redesign (+113% chat output from the style alone vs ~500 words for slim-vs-fat), a profile running the roster without the matching style is running a different configuration than the one that was tuned. Fixed — both profiles now receive `output-styles/*.md` with the same no-`--delete` per-file semantics the skills loop uses, so profile-only styles (`eli5.md`) survive.

**No output style is set as default in either profile** — `outputStyle` appears in neither `~/.claude/settings.json` nor `~/.claude-work/settings.json`, so both already inherit Claude Code's built-in default. Nothing to change; syncing a style file into the profile makes it *available*, not active.

**`focused.md` was written once and is lost.** The opus5-vs-opus4.6 report says "I've written you one (`focused.md`)" and `style-test-outputs/` carries three runs of it — but the file exists in neither the repo nor either profile, and neither does the `lean` style that was tested alongside it. The test outputs can't be reverse-engineered back into style definitions. A fresh `output-styles/focused.md` is written here, grounded in Anthropic's Opus 5 phrasings rather than reconstructed; treat it as new, not recovered.

That style test, for the record: `lean` averaged 615 words, `focused` 669, no style 680. Both custom styles beat no-style, `lean` by about 10%.

**A concrete problem with scannable.** Line 17 instructs *"Don't announce what you're about to do"*; the user's global CLAUDE.md line 11 instructs *"Before the first tool call, say in one sentence what you're about to do."* A direct contradiction across two layers — and conflicting guidance between the system prompt and CLAUDE.md is precisely what Anthropic identifies as degrading compliance. Scannable is also almost entirely negative instruction ("Never write these"), where Anthropic's Opus 5 guidance is explicit that *"positive examples of the communication style you want tend to be more effective than instructions about what not to do."* The new `focused.md` inverts both: it matches the CLAUDE.md narration cadence instead of fighting it, and describes the target shape rather than banning phrases.

Verified by running it: `scannable.md` now reaches both profiles, the profile-only `eli5.md` survived in both (proving the no-`--delete` semantics), `devils-advocate/SKILL.md` landed in both profiles, and the backup carries the full tree including this audit. The completion line now names what actually synced rather than under-reporting it.

`devils-advocate` needs no `EXCLUDE_WORK` entry: the work profile excludes dev-workflow personas because the thrive repo supplies its own, but the skeptic serves the business layer (vera, ellis, kora) which the work profile *does* carry. Default-sync semantics take it to both.
