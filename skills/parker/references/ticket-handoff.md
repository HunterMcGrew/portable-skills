# Ticket handoff (optional)

Runs only on explicit user confirmation, and only when a ticket tracker is reachable in the session (a tracker MCP or CLI). Absent one, skip with: "No tracker in this session — the PRD lives at `<path>`; hand it to nora later."

By stakes: **hobby** — don't offer (the finalize summary already mentioned it). **internal** — offer. **launch** — recommend: "Launch stakes — a tracker initiative buys cross-team visibility."

On confirmation, compose the payload — `title` (from frontmatter), `summary` (first paragraph of the problem statement), `prdPath`, `stakes` — and route to nora (dispatch per the shared core, or hand the user a one-line invocation). Record the returned initiative ID in frontmatter `trackerInitiativeId`. If the user declines, note the decline in `stepsCompleted` and close cleanly.
