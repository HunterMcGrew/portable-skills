# Worktree removal safety

Read this before removing any worktree that might carry work. Classify first — the color decides. Ambiguity always resolves to the more conservative color.

**Classify** (run inside the worktree):
1. `git status --porcelain` non-empty → **RED** (uncommitted work).
2. Detached HEAD (`git rev-parse --abbrev-ref HEAD` = `HEAD`) → **YELLOW** — except a read-only review worktree you created detached this session, which never carried work and may be removed.
3. `git rev-list --count @{upstream}..HEAD` = 0 → **GREEN** (everything is on the remote). No upstream, or count > 0 → continue to step 4.
4. Merged-PR check — the squash-merge case. A squash-merged branch's commits are never ancestors of main, so never use git ancestry as the durability oracle; use the PR record: `gh pr list --state merged --head <branch> --json headRefOid,number`. A merged PR makes the work durable **only if** its `headRefOid` contains the current HEAD: `git rev-list --count <headRefOid>..HEAD` = 0 → **GREEN**. Count > 0 means commits landed *after* the merge → **RED**. Trust commit identity, never the branch name alone. No `gh`, no remote, or no merged PR → **YELLOW**.
5. Anything the steps above didn't color → **YELLOW**.

**Act:**
- **GREEN** — `git worktree remove <path>`, never `--force`: if git refuses a GREEN removal, the classification was wrong — reclassify, don't override. Removing a worktree never deletes its branch; branch deletion is a separate, human-approved act.
- **YELLOW** — leave it; name it to the user with the reason.
- **RED** — never remove, never list as removable.

Batch removals (zoe's hygiene mode): dry-run listing first, then one confirmation covering the GREEN set only.
