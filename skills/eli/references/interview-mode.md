# Interview mode

Fires only when no diff exists to read — the user chose interview mode in Step 2, or there's no branch/PR/tag context to resolve.

Ask these one at a time:

1. "What does this feature do? Give me a one-sentence summary."
2. "Who uses it — an end user, an admin, a developer integrating it, or some combination?"
3. "What's the main thing someone needs to do to use it?"
4. "Any edge cases, limitations, or gotchas worth calling out?"
5. "Are there any existing components, modules, or classes involved?"

Use the answers as the basis for documentation — same format, same standards as diff-sourced docs. Treat the interview answers as the source of truth in place of a diff: they still go through the same claim-verification rule wherever they name a concrete identifier or path that exists in the codebase.
