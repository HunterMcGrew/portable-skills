# Common Issues

- **`resolveReviewThread` mutation fails** — stale thread ID or missing `write:discussion` scope. Don't retry; leave the thread open and note the failed auto-resolve in the summary.
- **Inline comment rejected with 422** — the line is outside a diff hunk. Move the observation to the summary; don't retry with a different line number.
- **`gh pr diff --stat` does not exist** — use `--name-only` for the changed-file list.
- **Formatter/linter "Cannot find package"** (worktree mode) — plugins often resolve per-package, not at the repo root; run from the package context.
- **Write tool fails on temp files** — always use a bash heredoc for temp files; reserve the Write tool for repo files.
- **Sequential API calls / incremental file reads** — the two biggest time wastes. Batch all GitHub writes into one message; compute the full source-file set after batch B and read it all in batch C.
