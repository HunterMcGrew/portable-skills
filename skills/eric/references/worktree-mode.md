# Worktree mode procedure

Same review logic as in-branch, but against an isolated checkout. Create it, read from it, tear it down on every exit path.

```bash
git worktree remove /tmp/pr-review-<branch-slug> --force 2>/dev/null || true
rm -rf /tmp/pr-review-<branch-slug>
git fetch origin <branch>
git worktree add /tmp/pr-review-<branch-slug> origin/<branch>
```

- `<branch-slug>` is the safe-filesystem form of the branch name (slashes replaced). The worktree lands in detached HEAD — intentional.
- **Full path only** — install dependencies inside the worktree using the repo's package manager, then run the repo's own formatter/linter checks from inside it. Lightweight skips both.
- **All reads use the worktree path as root** instead of `git show origin/<branch>:` reads.
- **cwd discipline is load-bearing.** Never leave the shell cwd inside the worktree; return to the repo root after any in-worktree command. Use `;` (not `&&`) before the return-to-root so a non-zero exit (prettier, eslint, tests) doesn't strand the cwd — a stranded cwd makes the cleanup fail with `getcwd` errors.
- **Cleanup is mandatory** — on success, on error, and on interruption: `cd <repo-root> && git worktree remove /tmp/pr-review-<branch-slug> --force`. This is Eric's own read-only review worktree — always detached, never carries work he made — so it stays force-removed under `_shared/worktree-safety.md`'s own exception (step 2). Before removing any *other* worktree that might carry work, read `_shared/worktree-safety.md` and classify first.
