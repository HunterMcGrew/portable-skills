# Hooks

User-level Claude Code hooks that add enforcement thrive's own repo hooks do
not yet provide. `sync.sh` copies every hook here to `<dest>/hooks/` — the
`*.test.*` files and this README stay behind — and registration in the
profile's `settings.json` is a hand edit (block below).

Every hook shares one contract. **Inert outside thrive:** it walks up from
the payload `cwd` (or the edited file) looking for
`.ai-spec/architect/manifest.json` and exits silently when none is found, so
the profile can run it in any repo. **Fails open:** every path exits 0; a deny
is the PreToolUse JSON envelope on stdout, and a skipped check is one line on
stderr. **Claude only:** no `--tool` argument, no other harness.

## architect-enforce.mjs (PreToolUse `Write|Edit`)

Denies a write to a code path until every architect doc the manifest's `code`
section routes to has been read in full this session. Thrive's own hook nags
on code routes and denies only on authoring routes; this adds the deny for
code. Credit comes from thrive's hook, which records every full `Read` under a
manifest root in `<tmpdir>/architect-context/claude/<session_id>.json`, so a
doc read once clears it here too. `ARCHITECT_ENFORCE=false` turns it off and
`ARCHITECT_ENFORCE=true` forces it on; when that is unset,
`ARCHITECT_CONTEXT_MODE=observe` or `off` relaxes it (enforce is the default
— that is the only job this overlay has). And `ARCHITECT_ENFORCE_MIN_LINES` (default 0, so every routed write denies)
is a changed-line tally an edited file must cross before the deny fires;
raise it only when small edits should pass without the reads. There is no
yield rule yet: if thrive later registers a code-route enforce hook, this one
should gain the same settings-based check `commit-cleanup.mjs` uses.

## commit-cleanup.mjs (PreToolUse `Bash`)

Gates the first `git commit` of a change set behind the cleanup instruction
from THR-2358: the first attempt is denied with the instruction, the identical
retry lands. Plan-only commits skip. Yields when the repo's own
`.claude/settings.json` registers a hook whose command contains
`commit-cleanup` — that is what stands it down once PR #2451 merges.

## push-verify.sh (PreToolUse `Bash`)

Runs prettier, `next lint`, and `check-types` over the commits a `git push`
would carry and denies the push when one fails, with the tail of the tool's
output in the reason. A port of the PR's `.githooks/pre-push`. Yields when the
repo already runs that check itself: `.githooks/pre-push` exists and
`core.hooksPath` resolves to that directory, or an executable `pre-push` sits
in the repo's git hooks directory. `check-types` follows
`.ai-spec/rules/command-execution.md`: on Darwin it runs through the
`thrive-admin-1` container and is skipped with a stderr notice when the
container is down. Runs under macOS `/bin/bash` 3.2 on purpose.

## Registering the hooks

`sync.sh` never touches `settings.json`. Replace the `hooks` key of the
profile's `settings.json` with this block, adjusting the profile path:

```json
"hooks": {
  "PreToolUse": [
    { "matcher": "Write|Edit", "hooks": [
      { "type": "command", "command": "node \"$HOME/.claude-work/hooks/architect-enforce.mjs\"" } ] },
    { "matcher": "Bash", "hooks": [
      { "type": "command", "command": "node \"$HOME/.claude-work/hooks/commit-cleanup.mjs\"" },
      { "type": "command", "command": "bash \"$HOME/.claude-work/hooks/push-verify.sh\"", "timeout": 900 } ] }
  ]
}
```

The `timeout: 900` on push-verify is not optional. The harness default is 60
seconds, and a full `check-types` run through the container takes longer than
that; a hook that times out is dropped silently, so the push would go through
with the check half-run and nothing said.

## Environment variables

| Variable | Values | Default | Reads it |
|---|---|---|---|
| `ARCHITECT_ENFORCE` | `true`, `false` | unset (falls back to the mode below) | architect-enforce |
| `ARCHITECT_CONTEXT_MODE` | `enforce`, `observe`, `off` | `enforce` | architect-enforce |
| `ARCHITECT_ENFORCE_MIN_LINES` | integer, `0` means always | `0` | architect-enforce |

Set profile defaults in the same `settings.json` under `"env"`; hooks inherit
them. A value on the command line wins over the settings one (verified:
`ARCHITECT_CONTEXT_MODE=observe claude-work` ran `observe` against a settings
default of `enforce`), so a one-off session overrides without an edit.

```json
"env": {
  "ARCHITECT_CONTEXT_MODE": "enforce",
  "ARCHITECT_ENFORCE_MIN_LINES": "0"
}
```

## Tests

```bash
node --test hooks/*.test.mjs      # THRIVE_ROOT=<thrive checkout> enables the live-remedy leg
/bin/bash hooks/push-verify.test.sh
```
