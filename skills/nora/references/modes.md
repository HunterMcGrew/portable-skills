# Nora — additional modes

Two read-only modes outside ticket setup. Neither creates or modifies tickets on its own — any action taken on what they surface routes back through the start/create paths so the § Shared state writes gate applies.

## Mode: Cycle View

When asked "show me the cycle," "what's in flight," "sprint view" — a read-only snapshot of the active cycle. Requires a tracker with cycle/sprint support; without one, say so.

1. Fetch the active cycle (the one whose window covers today); none → offer the next upcoming one.
2. Fetch its tickets (ID, title, status, assignee, labels, updated-at, linked PRs).
3. Bucket each ticket into exactly one of: **Ready** (assigned, not started) · **In-flight** (in progress, or has an open linked PR) · **Blocked** (blocked label or status). Conflicts resolve to Blocked — the blocker is the user-relevant fact.
4. Rollover detection — in-flight tickets that also appeared unfinished in the previous cycle get a `rollover` mark; headline the count.
5. Output one markdown table per bucket: Ticket | Title | Status | Rollover? | Last activity (human delta, "2d ago").
6. Stuck patterns — anything in the same status over 5 days gets an observational note below the table.
7. **No mutations.** If the user wants to act on what they see, route through the start or create paths so the write gate applies.

## Mode: Duplicate Finder

When asked "find duplicates," "is this a duplicate," "check for similar tickets":

1. Input shape — a ticket ID → fetch it and use its title/labels/description as the candidate; free text → use the text. Ambiguous → ask which.
2. Candidate pool — open tickets (exclude Done/Canceled/Duplicate), capped at the ~200 most recently updated.
3. Score each candidate: 0.5 × title similarity + 0.3 × label overlap + 0.2 × description fuzzy match (titles carry the most signal — shortest and most curated; descriptions the noisiest).
4. Present the top 3 with scores, a per-candidate reasoning bullet (title overlap, shared labels, status/assignee), and a proposed action (link as duplicate / close as duplicate of / no action).
5. If the top score is below ~0.40, lead with "no strong matches" and present the closest three for awareness only — don't manufacture false positives on novel work.
6. **Action gate** — act only on the user's explicit pick, and the mutation passes the § Shared state writes gate. Never auto-link, auto-close, or auto-merge.
