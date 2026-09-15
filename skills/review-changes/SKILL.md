---
name: review-changes
description: >
  Reviews a diff against its spec and the codebase's own rules, and returns
  findings classified by kind (bug, security risk, standards violation,
  out-of-scope change, code smell, nitpick) with file and line. Use when asked
  to review code, review changes, check work before a PR, self-review a
  branch, or review a pull request. Reports in chat only; never posts to
  GitHub.
argument-hint: "[PR number, branch, or nothing for the working tree]"
---

# Code review

Review the change in front of you: the working tree, a branch against its
base, or a PR. Findings only, ranked by severity, each tied to a file and
line. No greeting, no persona, no rewrite of the code.

## 1. Find the diff

- Working tree: `git diff` plus `git diff --cached`, and `git status --short`
  for untracked files that belong to the change.
- Branch: `git diff <base>...HEAD` where `<base>` is the branch's merge
  target (default `main`). `git log --oneline <base>..HEAD` for the commit
  story.
- PR: `gh pr diff <n>` and `gh pr view <n> --json title,body,baseRefName`.

List every changed file before reading any of them. The list is the
coverage checklist; a file you never opened is a file you did not review.

## 2. Find the spec

The diff is judged against what it was supposed to do, not against taste.
Locate, in this order, and read in full whatever exists:

- The plan file for the ticket (`<plans>/<ticket-id>.md` per the repo map,
  or wherever the repo keeps plans). Its goal, acceptance criteria, and
  `## Decisions` are the contract.
- The architect docs routed to the changed files. If the repo has
  `.ai-spec/architect/manifest.json`, resolve every changed path through its
  `code` section and read each doc it names. Other repos: the nearest
  `ARCHITECTURE.md`, `docs/`, or module README.
- The ticket or PR description, when there is one.
- The repo's own writing and structure rules (`CLAUDE.md`, `.ai-spec/rules/`,
  lint config).

No spec at all: say so in the report's first line and review against the
codebase's existing conventions only. Do not invent requirements.

## 3. Read the change

Read the full diff, then open each changed file and read enough surrounding
code to know what the changed lines are for. For every hunk ask, in order:

1. Does it do at runtime what the plan says it should? Read the logic as
   executed, not as described in the commit message.
2. Do the tests that cover it fail if the behavior regresses? A test that
   passes regardless is not coverage.
3. Does the diff assert behavior of a library, framework, or platform that
   this repo cannot confirm on its own? Check the source or docs before
   accepting it; a plausible claim is the one that gets through.
4. Does it leave a doc, comment, config, or type now contradicting the code?
5. Does it follow this repo's rules (naming, comments, structure), as opposed
   to a generic style preference?
6. When the diff touches auth, input handling, secrets, permissions, or any
   trust boundary: is the boundary still intact?
7. When the diff touches UI: keyboard access, focus, semantics, contrast,
   reduced motion.

Every cited line number and path must be checked against the current file,
never quoted from memory.

## 4. Classify every finding

One class per finding. Pick the most specific that fits.

| Class | Meaning |
|---|---|
| **bug** | Wrong behavior at runtime, or a test that cannot catch the regression it claims to. |
| **security risk** | A trust boundary weakened: injection, auth bypass, secret exposure, unsafe deserialization, missing validation at an input edge. |
| **code standard violation** | Breaks a rule this repo states in its own docs, lint config, or architect docs. Cite the rule. |
| **out of scope** | Work the plan did not specify, present in the diff with no stated reason in the plan, the PR body, or the code itself, and belonging in its own PR. Only when no justification exists anywhere; a stated reason moves it to a nitpick at most. |
| **divergent change** | One file edited for several unrelated reasons. Ask for a split so each module changes for one reason. |
| **feature envy** | A function that reaches into another module's data more than its own. Belongs where the data lives. |
| **middle man** | A class or function that only delegates. Callers should go direct. |
| **mysterious name** | A name that says nothing about what the thing does, or says something it does not do. |
| **nitpick** | Everything else that is real but small: formatting the linter missed, a clearer phrasing, a comment that drifted. |

Severity is separate from class and takes one of three values. **Blocking**:
a bug or security risk, or an out-of-scope change large enough to hide one.
**Should fix**: a standards violation, a divergent change, a mysterious name
on a public surface. **Optional**: the rest.

## 5. Report

In chat, in this shape, nothing else:

```
Reviewed: <N files, +A/-D> against <spec source, or "no spec found">
Verdict: <ready | ready after should-fix | not ready>

Blocking
1. [bug] path/to/file.ts:42 — one sentence naming the wrong behavior and the input that triggers it.

Should fix
2. [code standard violation] path:line — the rule (cite it) and the deviation.

Optional
3. [nitpick] path:line — ...

Not reached: <files or checks skipped, with the reason, or "none">
```

Rules for the list:

- One sentence per finding, stating the defect, not the fix. Add a second
  sentence only for the reproduction or the cited rule.
- No finding without a file and line. No finding you have not confirmed
  against the current file.
- A clean review reports `Verdict: ready` with empty sections, and still
  lists the spec source and any `Not reached` items. An empty "Not reached"
  is a claim that every file was opened; make it only when true.
- Do not post to GitHub. If the user wants findings on the PR, they will
  say so.
