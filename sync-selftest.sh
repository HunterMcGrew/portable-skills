#!/usr/bin/env bash
# Controls for sync.sh, in the same shape as render-claude-agents.py's
# --selftest: every control asserts the green case and then breaks the
# mechanism to prove the control goes red. A check that cannot fail is not a
# check. Exclusion logic is where this file started and is now a minority of
# it — the copy semantics, the four abort conditions, the self-target refusal,
# the codex arm and the un-configured defaults all have controls here, so read
# the numbered comments rather than this line for the scope.
#
# `bash -n sync.sh` is a syntax check and would pass just as happily with the
# prefix strip deleted, which is the one line whose failure is silent — an
# exclusion that stops matching ships a persona's shim to a profile that has
# no skill behind it, and nothing says so.
#
# Nothing here can reach a real profile: each case runs against a fabricated
# source tree under $TMPDIR with HOME redirected there too, so even a
# thoroughly broken sync.sh writes only into the scratch directory.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
# run() redirects HOME here. It has to exist for an assertion about what is
# *not* under it to be an observation rather than a vacancy — the only mkdir
# for it used to live inside a control that has since been deleted.
mkdir -p "$work/fakehome"
fails=0
controls=0

# Two personas is the smallest tree that can tell "excluded" from "empty":
# clove goes everywhere, winston is excluded from the second destination.
scaffold() {
  src="$work/$1"
  mkdir -p "$src"/{skills/winston,skills/clove,claude-agents,output-styles,codex-agents}
  echo skill >"$src/skills/winston/SKILL.md"
  echo skill >"$src/skills/clove/SKILL.md"
  echo 'name: p-winston' >"$src/claude-agents/p-winston.md"
  echo 'name: p-clove' >"$src/claude-agents/p-clove.md"
  echo style >"$src/output-styles/scannable.md"
  echo 'name = "winston"' >"$src/codex-agents/winston.toml"
  echo 'name = "clove"' >"$src/codex-agents/clove.toml"
  cp "$REPO/sync.sh" "$src/sync.sh"
  chmod +x "$src/sync.sh"
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("" "winston")
EOF
}

# Runs a scaffolded tree with HOME pointed inside it, so the script's own
# \$HOME default cannot resolve to a real profile. Sets rc; never aborts.
# Extra args after $1 pass straight through to sync.sh — control 10 uses
# this to exercise the argument guard without deploying.
run() {
  dir="$1"; shift
  rc=0
  HOME="$work/fakehome" "$dir/sync.sh" "$@" >"$work/out" 2>"$work/err" || rc=$?
}

ok() {
  controls=$((controls + 1))
  if [ "$2" = true ]; then
    printf 'selftest: %-22s ok\n' "$1"
  else
    printf 'selftest: %-22s FAIL — %s\n' "$1" "$3"
    fails=$((fails + 1))
  fi
}

# 1. Baseline: an unfiltered destination receives every category.
scaffold baseline
run "$src"
green=true
for p in skills/winston skills/clove agents/p-winston.md agents/p-clove.md \
  output-styles/scannable.md; do
  [ -e "$src/dest-all/$p" ] || green=false
done
[ "$rc" -eq 0 ] || green=false
ok baseline "$green" "unfiltered destination is missing files (rc=$rc)"

# 2. Exclusion: winston is absent from the filtered destination as both a
# skill and a shim, while clove — the control against an empty sync — is
# present in both. This is the case that fails if the prefix strip breaks:
# an unstripped "p-winston" never equals the excluded "winston".
#
# This is also the file's only fixture with a second destination, which makes
# it the only place the "ride along to every destination" property of the
# output-styles loop is observable — control 1 looks at DESTS[0] alone, and
# nothing else here ever names dest-filtered. Styles are unfiltered, so the
# assertion is presence, not absence: restricting that loop to DESTS[0] with a
# one-line `[ "$i" -eq 0 ] || continue` left the suite fully green, while the
# identical restriction on the skills or agents loop reds this control on the
# two lines above.
green=true
[ -e "$src/dest-filtered/skills/clove" ] || green=false
[ -e "$src/dest-filtered/agents/p-clove.md" ] || green=false
[ -e "$src/dest-filtered/output-styles/scannable.md" ] || green=false
[ ! -e "$src/dest-filtered/skills/winston" ] || green=false
[ ! -e "$src/dest-filtered/agents/p-winston.md" ] || green=false
ok exclusion "$green" "excluded persona leaked, an output style never reached the second destination, or the destination is empty"

# 3. The same case with the prefix strip removed must go red — otherwise
# control 2 was passing for some reason other than the strip.
scaffold stripbroken
sed 's|persona="${name#"$AGENT_PREFIX"}"|persona="$name"|' \
  "$src/sync.sh" >"$src/sync.tmp" && mv "$src/sync.tmp" "$src/sync.sh"
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok strip-red false "the sed did not match — this control tested nothing"
else
  run "$src"
  # Leaked shim is the red we want; the skill loop is untouched by the strip.
  [ -e "$src/dest-filtered/agents/p-winston.md" ] && green=true || green=false
  ok strip-red "$green" "strip removed and the exclusion still held — control 2 proves nothing"
fi

# 4. No --delete: a file only the profile knows about survives a sync. One
# fixture per arm README.md makes the promise for — a skill, an agent, *or a
# style* you keep only in your profile survives a re-sync untouched — because
# the promise is made three times and was seeded twice. A true --delete on the
# output-styles loop alone (prune destination files with no source counterpart,
# every shipped style still arriving) left all controls green while a
# profile-only style was destroyed; the identical regression on the skills loop
# reds this control immediately. A crude whole-directory wipe is caught by
# empty-dests-red and symlink-clobber-red, but only incidentally — neither of
# those is the no-delete property.
scaffold nodelete
mkdir -p "$src/dest-all/skills/local-only" "$src/dest-all/agents" \
  "$src/dest-all/output-styles"
echo local >"$src/dest-all/skills/local-only/SKILL.md"
echo local >"$src/dest-all/agents/some-other-agent.md"
echo local >"$src/dest-all/output-styles/local-only-style.md"
run "$src"
green=true
[ -e "$src/dest-all/skills/local-only/SKILL.md" ] || green=false
[ -e "$src/dest-all/agents/some-other-agent.md" ] || green=false
[ -e "$src/dest-all/output-styles/local-only-style.md" ] || green=false
ok no-delete "$green" "a profile-only skill, agent, or style was removed by the sync"

# 5. Parallel-array guard: fewer EXCLUDES than DESTS must abort rather than
# silently leave the trailing destination unfiltered.
#
# Three rows, because a bare `rc -ne 0` cannot tell "the guard I name fired"
# from "the script died for any other reason", and the shortest fixture alone
# is satisfied by conditions that are not the parity property. Measured on
# the one-row form: garbling the message, and replacing the condition with
# `[ "${#EXCLUDES[@]}" -eq 1 ] && [ "${#DESTS[@]}" -eq 2 ]` — which matches
# this fixture exactly and asserts nothing about parallelism — both left the
# suite fully green.
scaffold parity
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("")
EOF
run "$src"
green=true
[ "$rc" -ne 0 ] || green=false
grep -q "must be parallel" "$work/err" || green=false
# The guard runs pre-flight, so the abort has to precede the first mkdir.
[ ! -e "$src/dest-all/skills" ] || green=false
# Row 2, the other direction: more EXCLUDES than DESTS. Non-parallel is
# non-parallel, and this is the row that separates `-ne` from `-lt` — the
# latter accepts a long EXCLUDES silently, which is the shape where a
# destination gained a slot and the array did not lose one.
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("" "winston")
EOF
run "$src"
[ "$rc" -ne 0 ] || green=false
grep -q "must be parallel" "$work/err" || green=false
# Row 3: an empty EXCLUDES beside a live DESTS is legal and means no
# exclusions anywhere. Without it the `-ne 0` legality clause can be deleted
# and nothing notices — control 8's fixture empties both arrays, so the
# clause is never load-bearing there.
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=()
EOF
run "$src"
[ "$rc" -eq 0 ] || green=false
[ -f "$src/dest-all/skills/winston/SKILL.md" ] || green=false
ok parity-guard "$green" "a non-parallel EXCLUDES was accepted, an empty one was rejected, or the abort was not the parity guard (rc=$rc)"

# 6. Prefix-drift guard: an agent file that does not carry AGENT_PREFIX must
# abort while exclusions are configured, since none of them can match it.
#
# Three rows, for control 5's reason plus one specific to the `case` plus the
# gate's other direction. Row 1's fixture is rejected by any pattern that does
# not name `winston`, so on its own it is satisfied by a `case` widened to
# persona-name globs (`p-*|clove*|briar*`) — measured green on the one-row
# form, as was garbling the message.
scaffold drift
echo 'name: winston' >"$src/claude-agents/winston.md"
run "$src"
green=true
[ "$rc" -ne 0 ] || green=false
grep -q "does not start with AGENT_PREFIX" "$work/err" || green=false
[ ! -e "$src/dest-all/skills" ] || green=false
# Row 2: a file that starts with a persona's own name but not the prefix.
# The property is the prefix, not the persona, and this is the drift shape
# that actually happens — a renamed shim that kept its persona and lost its
# `p-`.
scaffold drift-persona
echo 'name: clove' >"$src/claude-agents/clove-extra.md"
run "$src"
[ "$rc" -ne 0 ] || green=false
grep -q "does not start with AGENT_PREFIX" "$work/err" || green=false

# Row 3: the gate rather than the check. sync.sh runs the prefix check only
# when an exclusion is configured — with none, the prefix is irrelevant to this
# script and a mismatch harms nothing — and rows 1 and 2 assert only that the
# abort fires. Nothing asserted it stays silent, so `any_exclusions` could be
# pinned true, deleting the gate, with the suite fully green. Same unprefixed
# file as row 2 and no exclusions anywhere: the sync has to complete, say
# nothing about the prefix, and still deploy.
scaffold drift-off
echo 'name: clove' >"$src/claude-agents/clove-extra.md"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
EOF
run "$src"
[ "$rc" -eq 0 ] || { green=false; echo "  drift-guard row 3: an unprefixed file aborted a run with no exclusions (rc=$rc): $(tail -1 "$work/err")" >&2; }
grep -q "does not start with AGENT_PREFIX" "$work/err" && { green=false; echo "  drift-guard row 3: the prefix check ran with no exclusion configured" >&2; }
[ -f "$src/dest-all/agents/p-clove.md" ] || { green=false; echo "  drift-guard row 3: the sync did not deploy" >&2; }
ok drift-guard "$green" "an unprefixed agent file synced with exclusions live, the check fired with none configured, or the abort was not the prefix guard (rc=$rc)"

# (7 was the BACKUP_DIR guard. BACKUP_DIR was removed rather than repaired —
# its guard accepted 23 of 28 spellings, and the feature mirrored a repo git
# already backs up. The numbering keeps its gap so the cross-references below
# still name the controls they mean.)

# 8. An empty DESTS is a clean no-op, not a crash. Every array expansion the
# script performs has to be the index form or :--guarded, because on bash 3.2
# "${A[@]}" and "${A[*]}" are both unbound-variable errors under set -u when A
# is empty — so this control covers all of them at once rather than one line.
scaffold emptydests
cat >"$src/sync.local.sh" <<'EOF'
DESTS=()
EXCLUDES=()
EOF
run "$src"
[ "$rc" -eq 0 ] && green=true || green=false
ok empty-dests "$green" "an empty DESTS aborted instead of no-opping (rc=$rc): $(tail -1 "$work/err")"

# 9. The same case with the output-styles loop reverted to the value form must
# go red — otherwise control 8 passes for some reason other than the fix.
scaffold emptydests-red
# python3 rather than sed: the loop header is identical across all three arms,
# so only the following line disambiguates the output-styles one, and matching
# across lines is what sed makes awkward and this makes obvious.
python3 - "$src/sync.sh" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace(
    'for i in "${!DESTS[@]}"; do\n  dst="${DESTS[$i]}"\n  mkdir -p "$dst/output-styles"',
    'for dst in "${DESTS[@]}"; do\n  mkdir -p "$dst/output-styles"')
open(p, 'w').write(s)
PY
chmod +x "$src/sync.sh"
cat >"$src/sync.local.sh" <<'EOF'
DESTS=()
EXCLUDES=()
EOF
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok empty-dests-red false "the mutation did not match — this control tested nothing"
else
  run "$src"
  [ "$rc" -ne 0 ] && green=true || green=false
  ok empty-dests-red "$green" "value-form expansion survived an empty DESTS — control 8 proves nothing"
fi

# 10. Argument guard: the script writes to the user's live ~/.claude
# profile, and this guard is the only thing standing between a typo'd flag
# (`--selftest`, expecting a read-only pass that doesn't exist) and a full
# deploy running silently instead. Same isolation as every other control —
# HOME points inside $work, so even if the guard failed and fell through to
# the write arm, nothing outside the scratch directory would be touched.
scaffold argguard
run "$src" --anything
green=true
[ "$rc" -eq 2 ] || green=false
[ ! -e "$src/dest-all/skills" ] || green=false
ok arg-guard "$green" "an unrecognized argument did not exit 2, or a write happened anyway (rc=$rc)"

# 11. The same case with the guard removed must go red — otherwise control
# 10 passes for some reason other than the guard.
scaffold argguard-red
sed '/^if \[ "\$#" -gt 0 \]; then$/,/^fi$/d' "$src/sync.sh" >"$src/sync.tmp" && mv "$src/sync.tmp" "$src/sync.sh"
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok arg-guard-red false "the guard removal did not match — this control tested nothing"
else
  run "$src" --anything
  [ "$rc" -ne 2 ] && green=true || green=false
  ok arg-guard-red "$green" "guard removed and an unrecognized argument still exited 2 — control 10 proves nothing"
fi

# 12. Symlink-clobber guard: a destination file that is already a symlink
# to something outside the repo (a stray user edit, or a previous sync run
# under a different scheme) must be replaced with a fresh regular file,
# never written through — cp follows a destination symlink to its target,
# so writing through it would silently clobber whatever that target is.
# All four rm-then-cp loops (skills, agents, output-styles, codex) get a
# fixture here. Two of them used to be justified away with "the skills and
# agents loops both ride through controls 2/3's exclusion mechanics, which
# already touch the same rm-before-cp shape" — but controls 2/3 exercise that
# the loop *runs*, never that it refuses to write through a destination
# symlink, which is the only property this control exists to prove. Both
# uncovered arms were reproduced: with the rm stripped, `cp -R` drops
# SKILL.md *inside* the outside directory and `cp` writes *through* the agent
# symlink. Sharing a code shape is not coverage.
scaffold symlink
mkdir -p "$src/outside" "$src/outside/skilldir" "$src/dest-all/output-styles" \
  "$src/dest-all/skills" "$src/dest-all/agents"
echo original-precious-content >"$src/outside/precious"
echo original-precious-agent >"$src/outside/precious-agent"
ln -s "$src/outside/precious" "$src/dest-all/output-styles/scannable.md"
# A directory symlink for the skills loop: `rm -rf` on one unlinks rather
# than descends, so the guard's whole job here is to unlink before `cp -R`
# copies the source directory *into* whatever it points at.
ln -s "$src/outside/skilldir" "$src/dest-all/skills/clove"
ln -s "$src/outside/precious-agent" "$src/dest-all/agents/p-clove.md"
run "$src"
green=true
[ -L "$src/dest-all/output-styles/scannable.md" ] && green=false
[ "$(cat "$src/outside/precious")" = original-precious-content ] || green=false
[ -L "$src/dest-all/skills/clove" ] && green=false
[ -e "$src/outside/skilldir/SKILL.md" ] && green=false
[ -f "$src/dest-all/skills/clove/SKILL.md" ] || green=false
[ -L "$src/dest-all/agents/p-clove.md" ] && green=false
[ "$(cat "$src/outside/precious-agent")" = original-precious-agent ] || green=false
# Second row of the same control: the codex loop, whose rm-before-cp had no
# control behind it at all. Deleting that one line leaves every other control
# green while a file outside the profile is destroyed through a symlink.
echo original-precious-toml >"$src/outside/precious-toml"
mkdir -p "$src/codex-dest"
ln -s "$src/outside/precious-toml" "$src/codex-dest/clove.toml"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-dest"
EOF
run "$src"
[ -L "$src/codex-dest/clove.toml" ] && green=false
[ "$(cat "$src/outside/precious-toml")" = original-precious-toml ] || green=false
ok symlink-clobber "$green" "destination symlink survived the sync, or the outside file was clobbered"

# 13. The same case with all four rm-before-cp lines stripped must go red
# — otherwise control 12 passes for some reason other than the guard.
# python3, not sed, per control 9's own precedent: four distinct lines
# across four loops is easier to match exactly this way than to keep
# four sed expressions in sync with the source.
#
# `|| true` here and on every other python3 mutator below: a failed assert
# exits non-zero, and under `set -e` that ends the run before the `cmp -s`
# handler can name the control — the graceful path every red twin writes was
# unreachable. Each mutator writes the file only after all of its asserts
# pass, so a missed anchor leaves sync.sh byte-identical and cmp reports
# "tested nothing", with the traceback still on stderr naming the anchor and
# the remaining controls still running.
scaffold symlink-red
python3 - "$src/sync.sh" <<'PY' || true
import sys
p = sys.argv[1]
s = open(p).read()
targets = (
    'rm -rf "${dst:?}/skills/${name:?}"  # removes old symlink or stale copy\n',
    'rm -f "$dst/agents/$name.md"\n',
    'rm -f "$dst/output-styles/$(basename "$f")"  # see the agents loop above\n',
    '    rm -f "$CODEX_DEST/$name.toml"\n',
)
for old in targets:
    assert old in s, 'not found: %r' % old
    s = s.replace(old, '', 1)
open(p, 'w').write(s)
PY
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok symlink-clobber-red false "the strip did not match — this control tested nothing"
else
  mkdir -p "$src/outside" "$src/outside/skilldir" "$src/dest-all/output-styles" \
    "$src/dest-all/skills" "$src/dest-all/agents" "$src/codex-dest"
  echo original-precious-content >"$src/outside/precious"
  echo original-precious-toml >"$src/outside/precious-toml"
  echo original-precious-agent >"$src/outside/precious-agent"
  ln -s "$src/outside/precious" "$src/dest-all/output-styles/scannable.md"
  ln -s "$src/outside/precious-toml" "$src/codex-dest/clove.toml"
  ln -s "$src/outside/skilldir" "$src/dest-all/skills/clove"
  ln -s "$src/outside/precious-agent" "$src/dest-all/agents/p-clove.md"
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-dest"
EOF
  run "$src"
  # One arm per stripped line, so the twin reds for all four reasons control
  # 12 now covers rather than for the two it used to.
  if [ "$(cat "$src/outside/precious")" != original-precious-content ] &&
    [ "$(cat "$src/outside/precious-toml")" != original-precious-toml ] &&
    [ "$(cat "$src/outside/precious-agent")" != original-precious-agent ] &&
    [ -e "$src/outside/skilldir/SKILL.md" ]; then
    green=true
  else
    green=false
  fi
  ok symlink-clobber-red "$green" "rm-before-cp removed and an outside file was not clobbered — control 12 proves nothing"
fi

# 14. Stale-exclusion warning: an entry naming a skill directory that does not
# exist warns on stderr and does not abort — sync.sh's pre-flight exclusion
# warnings, named rather than cited by line, because an edit upstream in that
# file has already invalidated this citation once. Both lists are covered:
# EXCLUDES per destination, and the CODEX_EXCLUDES pass beside it. The other
# destination's files still land, proving the warning doesn't quietly turn
# into a partial or skipped sync. Four rows: the two lists firing, the glob
# that must not expand, the live names that must not warn, and the ordering.
scaffold stale
mkdir -p "$src/codex-dest"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("" "ghost-persona")
CODEX_DEST="$src/codex-dest"
CODEX_EXCLUDES="ghost-codex"
EOF
run "$src"
green=true
[ "$rc" -eq 0 ] || green=false
grep -q "stale exclusion for .*ghost-persona" "$work/err" || green=false
grep -q "stale codex exclusion: ghost-codex" "$work/err" || green=false
[ -e "$src/dest-filtered/skills/winston" ] || green=false
[ -e "$src/dest-filtered/skills/clove" ] || green=false

# Second row of the same control: an exclusion written with a `*`. The lists
# are split unquoted, so without `set -f` the `*` pathname-expands against the
# caller's cwd — standing in a directory that holds a file named after a
# persona then excludes that persona, an exclusion the user never wrote. The
# cwd *is* the variable under test, so this row cannot go through run(). The
# destination is cleared first: a clove.toml surviving from the row above
# would leave the assertion below unable to fail.
rm -rf "$src/codex-dest"
mkdir -p "$src/globcwd"
: >"$src/globcwd/clove"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-dest"
CODEX_EXCLUDES='*'
EOF
globrc=0
(cd "$src/globcwd" && HOME="$work/fakehome" "$src/sync.sh" >"$work/out" 2>"$work/err") || globrc=$?
[ "$globrc" -eq 0 ] || green=false
[ -f "$src/codex-dest/clove.toml" ] || green=false
grep -q "stale codex exclusion: [*]" "$work/err" || green=false

# Row 3: the other direction of both `-d` tests. The rows above assert that a
# name with no skills/ directory warns; nothing asserted that a name with one
# stays silent, so both tests could be deleted — warn unconditionally, on every
# exclusion anyone writes — with the suite fully green. Live names on both
# lists, and neither warning may appear.
rm -rf "$src/codex-dest"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("" "winston")
CODEX_DEST="$src/codex-dest"
CODEX_EXCLUDES="clove"
EOF
run "$src"
[ "$rc" -eq 0 ] || green=false
grep -q "stale exclusion for" "$work/err" && { green=false; echo "  stale-exclusion row 3: a live exclusion warned" >&2; }
grep -q "stale codex exclusion" "$work/err" && { green=false; echo "  stale-exclusion row 3: a live codex exclusion warned" >&2; }

# Row 4: the ordering sync.sh states for these warnings — before copying
# anything. The rows above assert the text and that the sync completes, never
# that the warnings precede the rest of the pre-flight; relocating the whole
# warn block below all four copy loops left the suite fully green, and in that
# shape any earlier abort suppresses the warnings entirely. The fixture is a
# stale exclusion on a destination that also aliases the source tree, so the
# self-target refusal fires: the warning has to be on stderr beside it, which
# it can only be if it was printed first.
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src")
EXCLUDES=("ghost-persona")
EOF
run "$src"
[ "$rc" -ne 0 ] || { green=false; echo "  stale-exclusion row 4: the aliasing destination was not refused" >&2; }
grep -q "resolves to this repo's own" "$work/err" || { green=false; echo "  stale-exclusion row 4: the abort was not the self-target refusal" >&2; }
grep -q "stale exclusion for .*ghost-persona" "$work/err" || { green=false; echo "  stale-exclusion row 4: the warning did not precede the refusal that ended the run" >&2; }
ok stale-exclusion "$green" "a stale exclusion did not warn on one of the two lists, a live one warned anyway, a glob exclusion swallowed a persona nobody named, the warning did not precede the pre-flight abort, or the sync aborted (rc=$rc globrc=$globrc)"

# 15. The same case with both warning lines stripped must go red — otherwise
# control 14 passes for some reason other than the warnings. Both, not one: a
# strip that left the codex line standing would let control 14's new arm pass
# here too. cmp against the real file per control 9/13's own precedent, so a
# non-matching edit reports "tested nothing" instead of a false green.
scaffold stale-red
python3 - "$src/sync.sh" <<'PY' || true
import sys
p = sys.argv[1]
s = open(p).read()
old = ('    [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale exclusion for '
       '$dst: $ex — renamed or removed? sync may now include its '
       'successor" >&2\n')
assert old in s, 'not found: %r' % old
s = s.replace(old, '', 1)
old2 = ('  [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale codex exclusion: '
        '$ex — renamed or removed? sync may now include its successor" >&2\n')
assert old2 in s, 'not found: %r' % old2
s = s.replace(old2, '', 1)
open(p, 'w').write(s)
PY
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok stale-exclusion-red false "the strip did not match — this control tested nothing"
else
  mkdir -p "$src/codex-dest"
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("" "ghost-persona")
CODEX_DEST="$src/codex-dest"
CODEX_EXCLUDES="ghost-codex"
EOF
  run "$src"
  if grep -q "stale exclusion\|stale codex exclusion" "$work/err"; then
    green=false
  else
    green=true
  fi
  ok stale-exclusion-red "$green" "warning lines removed and a warning still appeared — control 14 proves nothing"
fi

# 16. Codex projections reach CODEX_DEST, honour CODEX_EXCLUDES, and leave a
# host repo's own agents alone. That last one is the whole reason this loop
# is per-file with no --delete: ~/.codex/agents is shared with whatever repo
# you are standing in, and a sync that pruned it would delete agents it has
# never heard of.
scaffold codex
mkdir -p "$src/codex-dest"
echo 'name = "thrive-architect"' >"$src/codex-dest/thrive-architect.toml"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-dest"
CODEX_EXCLUDES="winston"
EOF
run "$src"
green=true
[ "$rc" -eq 0 ] || green=false
[ -f "$src/codex-dest/clove.toml" ] || green=false
[ -e "$src/codex-dest/winston.toml" ] && green=false
[ -f "$src/codex-dest/thrive-architect.toml" ] || green=false
grep -q "codex-agents ->" "$work/out" || green=false

# Second row of the same control: CODEX_DEST pointed at the source tree's own
# codex-agents/. The rm+cp is destination-first, so with no guard it unlinks
# the toml it is about to copy and set -e halts with the tracked file already
# deleted — reproduced exactly that way. The abort must fire, and the source
# must still be on disk afterwards, which is the arm that goes red if the
# guard is removed (rc is non-zero either way; only the file tells them apart).
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-agents"
EOF
run "$src"
[ "$rc" -ne 0 ] || green=false
[ -f "$src/codex-agents/clove.toml" ] || green=false
grep -q "CODEX_DEST resolves to" "$work/err" || green=false
ok codex-deploy "$green" "codex toml missing, exclusion ignored, a host agent was pruned, the summary line stayed silent, or a self-aliasing CODEX_DEST ate its own sources (rc=$rc)"

# 17. The same case with the copy stripped must go red, or control 16 is
# passing for some reason other than the loop running. cmp against the real
# file first, per control 9/13/15's precedent.
scaffold codex-red
python3 - "$src/sync.sh" <<'PY_INNER' || true
import sys
p = sys.argv[1]
s = open(p).read()
old = '    cp "$f" "$CODEX_DEST/$name.toml"\n'
assert old in s, 'not found: %r' % old
s = s.replace(old, '', 1)
open(p, 'w').write(s)
PY_INNER
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok codex-deploy-red false "the strip did not match — this control tested nothing"
else
  mkdir -p "$src/codex-dest"
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-dest"
EOF
  run "$src"
  if [ -f "$src/codex-dest/clove.toml" ]; then
    green=false
  else
    green=true
  fi
  ok codex-deploy-red "$green" "copy removed and the toml still arrived — control 16 proves nothing"
fi

# 18. Unset CODEX_DEST is the default for every clone, and it must deploy
# nothing rather than creating a stray directory next to the profile. A loop
# that ran unconditionally would silently make ~/.codex on a machine that has
# no Codex install.
scaffold codex-off
run "$src"
green=true
[ "$rc" -eq 0 ] || green=false
[ -e "$src/codex-dest" ] && green=false
[ -e "$work/fakehome/.codex" ] && green=false
grep -q "codex-agents ->" "$work/out" && green=false
# Second row of the same control: the other way a user turns codex off. An
# override that says `unset CODEX_DEST` rather than assigning it "" is the
# same intent and a different state under set -u, and a bare [ -n "$CODEX_DEST" ]
# dies on it before any write. The row above's assertions less the
# fakehome/.codex one, which is row 1's alone, against the spelling that used
# to abort.
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
unset CODEX_DEST
EOF
run "$src"
[ "$rc" -eq 0 ] || { green=false; echo "  codex-default-off row 2: unset CODEX_DEST aborted (rc=$rc): $(tail -1 "$work/err")" >&2; }
[ -e "$src/codex-dest" ] && green=false
grep -q "codex-agents ->" "$work/out" && green=false
ok codex-default-off "$green" "an unset CODEX_DEST still deployed or created a directory (rc=$rc)"

# 19. Self-target refusal: a destination resolving to one of this repo's own
# source directories must abort before any write, with every source file still
# on disk. Seven rows — four arms, one relation, one list entry, and one
# destination index above zero. Rows 5 and 7 each carry a second assertion
# about *when* the refusal runs rather than that it ran, because "before any
# write" is half the property and the half no row used to check. Row 5 is
# the relation: a ./ segment makes the destination inode-equal but not
# string-equal, which is exactly what control 21 proves a string compare
# misses. Row 6 is SRC_DIRS' own "$SRC" entry, the one no arm reaches: a
# destination subdirectory resolving to the repo *root*, whose damage is
# untracked copies landing in the working tree rather than a source file
# deleted. Row 7 is the arm that proves the pre-flight loops over every
# destination rather than checking the first: its second DESTS entry aliases
# the source tree while its first is benign, so a pre-flight restricted to
# DESTS[0] walks straight past it. Rows share one scaffold because a refusal
# writes nothing, so the tree is unchanged between them; dest-all is rebuilt
# per row.
scaffold self-target
green=true
st_row() {  # st_row <row> <file that must survive>
  run "$src"
  [ "$rc" -ne 0 ] || { green=false; echo "  self-target row $1: expected abort, got rc=0" >&2; }
  [ -e "$2" ] || { green=false; echo "  self-target row $1: source $2 was destroyed" >&2; }
  grep -q "resolves to this repo's own" "$work/err" || { green=false; echo "  self-target row $1: no refusal on stderr" >&2; }
}

# Row 1: DESTS pointed straight at the source root, with no symlink anywhere
# — the reproduction that needs nothing left over from a previous sync.
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src")
EXCLUDES=("")
EOF
st_row 1 "$src/skills/clove/SKILL.md"

# Rows 2-4: one arm each, reached through a symlink sitting in the profile —
# the realistic case, and the state a previous sync under a different scheme
# leaves behind.
rm -rf "$src/dest-all"; mkdir -p "$src/dest-all"
ln -s "$src/skills" "$src/dest-all/skills"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
EOF
st_row 2 "$src/skills/clove/SKILL.md"

rm -rf "$src/dest-all"; mkdir -p "$src/dest-all"
ln -s "$src/claude-agents" "$src/dest-all/agents"
st_row 3 "$src/claude-agents/p-clove.md"

rm -rf "$src/dest-all"; mkdir -p "$src/dest-all"
ln -s "$src/output-styles" "$src/dest-all/output-styles"
st_row 4 "$src/output-styles/scannable.md"

# Row 5: the relation rather than a fourth arm. dest-all stays a plain empty
# directory; the ./ segment is the whole fixture.
rm -rf "$src/dest-all"; mkdir -p "$src/dest-all"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/./codex-agents"
EOF
st_row 5 "$src/codex-agents/clove.toml"
# The refusal's *ordering*, on the CODEX_DEST arm: DESTS here is benign, so
# lowering this refusal out of the pre-flight to just above `mkdir -p
# "$CODEX_DEST"` still aborts with every source file intact — every assertion
# st_row makes — after all three DESTS loops have already rewritten a profile.
# Measured green at every control before this line existed.
[ ! -e "$src/dest-all/skills" ] || { green=false; echo "  self-target row 5: the benign DESTS entry was written before the CODEX_DEST refusal" >&2; }

# Row 6: the "$SRC" entry of SRC_DIRS, which the four arms above never touch —
# they all resolve to a subdirectory. A destination whose skills/ points at the
# repo root writes *into* the root: rm -rf finds nothing to unlink and cp -R
# then drops $src/clove beside the tracked directories. Pollution rather than
# deletion, so the surviving-source assertion cannot catch it and the stray
# copy is asserted directly.
rm -rf "$src/dest-all"; mkdir -p "$src/dest-all"
ln -s "$src" "$src/dest-all/skills"
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
EOF
st_row 6 "$src/skills/clove/SKILL.md"
[ -e "$src/clove" ] && { green=false; echo "  self-target row 6: untracked copies landed in the repo root" >&2; }

# Row 7: a destination index above zero. Every other fixture in this file is
# single-entry, so nothing yet distinguishes a pre-flight that loops from one
# that checks DESTS[0] and stops. The first entry is benign and the second
# aliases the source root; the refusal has to name the second, and the source
# skill directories have to be all still there afterwards.
rm -rf "$src/dest-all" "$src/dest-two"; mkdir -p "$src/dest-all" "$src/dest-two"
before=$(ls "$src/skills" | wc -l | tr -d ' ')
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-two" "$src")
EXCLUDES=("" "")
EOF
st_row 7 "$src/skills/clove/SKILL.md"
grep -q "DESTS\[1\]" "$work/err" || { green=false; echo "  self-target row 7: refusal did not name the second destination" >&2; }
[ "$(ls "$src/skills" | wc -l | tr -d ' ')" = "$before" ] || { green=false; echo "  self-target row 7: a source skill directory was destroyed" >&2; }
# The refusal's *ordering*, on the DESTS arm. Every assertion above is about
# the refusal firing and the sources surviving; none is about the destination
# the run walked past first. De-hoisting the pre-flight into the deploy loop
# satisfies all of them — the refusal still fires naming DESTS[1] with every
# source intact — while dest-two has already been rewritten, no summary line
# prints, and the user cannot tell which profiles are current. Measured green
# at every control before this line existed. This is the property the hoist in
# sync.sh exists for, and it is ordering, not content.
[ -z "$(ls -A "$src/dest-two")" ] || { green=false; echo "  self-target row 7: the benign first destination was written before the refusal" >&2; }
ok self-target "$green" "a destination aliasing the source tree was not refused before writing, or a source file did not survive"

# 20. The same case with the pre-flight's three DESTS calls stripped must go
# red, or control 19 is passing for some reason other than the refusal. The
# green condition is stated positively — the source file is *gone* — rather
# than as an absence, because an absence-only assertion passes just as well on
# a harness that did nothing at all.
scaffold self-target-red
python3 - "$src/sync.sh" <<'PY_ST' || true
import sys
p = sys.argv[1]
s = open(p).read()
targets = (
    '  refuse_self_target "DESTS[$i]\'s skills destination" "$dst/skills"\n',
    '  refuse_self_target "DESTS[$i]\'s agents destination" "$dst/agents"\n',
    '  refuse_self_target "DESTS[$i]\'s output-styles destination" "$dst/output-styles"\n',
)
for old in targets:
    assert old in s, 'not found: %r' % old
    s = s.replace(old, '', 1)
open(p, 'w').write(s)
PY_ST
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok self-target-red false "the strip did not match — this control tested nothing"
else
  mkdir -p "$src/dest-all"
  ln -s "$src/skills" "$src/dest-all/skills"
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
EOF
  run "$src"
  [ ! -e "$src/skills/clove/SKILL.md" ] && green=true || green=false
  ok self-target-red "$green" "the refusal was stripped and the source survived anyway — control 19 proves nothing"
fi

# 21. The relation rather than the presence: -ef replaced by a string compare.
# Control 19's row 5 is the fixture, because a ./ segment is inode-equal and
# textually different — so a string compare waves it through and the codex
# loop unlinks the toml it is about to read. Without this twin, control 19
# passes against a guard that only ever compares path text: measured, the same
# mutation left every other control in this file green.
scaffold self-target-string-red
python3 - "$src/sync.sh" <<'PY_ST' || true
import sys
p = sys.argv[1]
s = open(p).read()
old = 'if [ "$dir" -ef "$s" ]; then\n'
assert old in s, 'not found: %r' % old
s = s.replace(old, 'if [ "$dir" = "$s" ]; then\n', 1)
open(p, 'w').write(s)
PY_ST
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok self-target-string-red false "the strip did not match — this control tested nothing"
else
  mkdir -p "$src/dest-all"
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/./codex-agents"
EOF
  run "$src"
  [ ! -e "$src/codex-agents/clove.toml" ] && green=true || green=false
  ok self-target-string-red "$green" "a string compare refused an inode-equal destination — control 19 row 5 proves nothing"
fi

# 22. A multi-name exclusion list excludes every name in it. The lists are
# space-separated strings split by an unquoted expansion under `set -f`, and
# sync.sh's own comment explains at length why quoting would be a regression —
# a quoted expansion is one word, so a two-name list matches no persona and
# silently excludes nothing. Nothing measured that until this control: every
# fixture in this file held a single name, where one word and one list are
# indistinguishable.
scaffold multi-exclude
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("" "winston clove")
EOF
run "$src"
green=true
[ "$rc" -eq 0 ] || green=false
[ -e "$src/dest-filtered/skills/winston" ] && green=false
[ -e "$src/dest-filtered/skills/clove" ] && green=false
[ -e "$src/dest-filtered/agents/p-winston.md" ] && green=false
[ -e "$src/dest-filtered/agents/p-clove.md" ] && green=false
[ -f "$src/dest-all/skills/winston/SKILL.md" ] || green=false
[ -f "$src/dest-all/skills/clove/SKILL.md" ] || green=false
ok multi-exclude "$green" "a two-name exclusion list did not exclude both names, or excluded them from the wrong destination"

# 23. The same case with excluded()'s split quoted must go red, or control 22
# is passing for some reason other than the word splitting. cmp against the
# real file first, per controls 9/13/15/17/20/21's precedent.
scaffold multi-exclude-red
python3 - "$src/sync.sh" <<'PY_MX' || true
import sys
p = sys.argv[1]
s = open(p).read()
old = '  for ex in $list; do\n'
assert old in s, 'not found: %r' % old
s = s.replace(old, '  for ex in "$list"; do\n', 1)
open(p, 'w').write(s)
PY_MX
chmod +x "$src/sync.sh"
if cmp -s "$REPO/sync.sh" "$src/sync.sh"; then
  ok multi-exclude-red false "the quote did not match — this control tested nothing"
else
  cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("" "winston clove")
EOF
  run "$src"
  if [ -e "$src/dest-filtered/skills/winston" ]; then green=true; else green=false; fi
  ok multi-exclude-red "$green" "the split was quoted and a two-name exclusion still held — control 22 proves nothing"
fi

# 24. A BACKUP_DIR left in an existing sync.local.sh is inert, and the script
# says so instead of letting the setting look live. No red twin: the assertion
# is positive — this exact warning is on stderr and the run still succeeds — so
# deleting the echo falsifies it directly, the same reasoning control 19's rows
# 6 and 7 record.
scaffold backup-inert
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
BACKUP_DIR="$src/somewhere"
EOF
run "$src"
green=true
[ "$rc" -eq 0 ] || green=false
grep -q "BACKUP_DIR is set but nothing reads it" "$work/err" || green=false
[ -e "$src/somewhere" ] && green=false
[ -f "$src/dest-all/skills/clove/SKILL.md" ] || green=false
ok backup-inert "$green" "a stale BACKUP_DIR did not warn, aborted the sync, or something created the directory (rc=$rc)"

# 25. The defaults block itself. Every other control in this file writes a
# sync.local.sh before running, so the path README calls the normal case — no
# sync.local.sh at all — was exercised by nothing, and DESTS, EXCLUDES and
# CODEX_EXCLUDES could be changed to anything with the suite still fully
# green. Measured before this control existed: DESTS -> ("$HOME") green,
# DESTS -> an arbitrary absolute path green, CODEX_EXCLUDES -> "winston"
# green. Only CODEX_DEST had a control behind it, because control 18 alone
# declines to set it.
#
# Two rows, because the defaults are not all observable on one path.
# Row 1 is the un-configured run. Row 2 is what it takes to reach the one
# default row 1 cannot: a sync.local.sh replaces the defaults block rather
# than adding to it, so setting CODEX_DEST means restating DESTS and EXCLUDES
# beside it. With CODEX_DEST empty the codex loop never runs, which is why the
# CODEX_EXCLUDES default is unreadable from row 1 by construction.
#
# No red twin, for control 24's reason: every assertion here is positive
# about a documented default, so changing a default falsifies the control
# directly rather than through a mechanism that could rot.
scaffold defaults
rm -f "$src/sync.local.sh"
# A fresh HOME so "nowhere else under $HOME" is an observation rather than a
# claim about whatever earlier controls happened to leave behind.
rm -rf "$work/fakehome"
mkdir -p "$work/fakehome"
run "$src"
green=true
[ "$rc" -eq 0 ] || green=false
# The DESTS default is "$HOME/.claude" — assert the subdirectory *and* that
# nothing landed beside it, since DESTS=("$HOME") writes a skills/ tree that
# is one level up and otherwise identical.
[ -f "$work/fakehome/.claude/skills/clove/SKILL.md" ] || green=false
[ -f "$work/fakehome/.claude/agents/p-clove.md" ] || green=false
[ -f "$work/fakehome/.claude/output-styles/scannable.md" ] || green=false
# The EXCLUDES default is ("") — no exclusions, so the persona every other
# fixture filters out has to arrive here.
[ -f "$work/fakehome/.claude/skills/winston/SKILL.md" ] || green=false
[ -f "$work/fakehome/.claude/agents/p-winston.md" ] || green=false
# Nothing anywhere else under HOME. This is what catches a DESTS default
# pointed one level up, or a CODEX_DEST default that starts creating ~/.codex.
stray="$(ls -A "$work/fakehome" | grep -vx '.claude' || true)"
[ -z "$stray" ] || green=false
# Every assertion above is scoped to the redirected $HOME, which makes a
# default naming a path *outside* the fabricated tree invisible to all of
# them: DESTS defaulting to ("$HOME/.claude" "<somewhere else>") leaves each
# one true and deploys a full roster outside the sandbox, with the suite
# reporting every control green. That is the harness's core safety property —
# nothing escapes the fabricated tree — and it was unasserted. The summary line
# names every destination the run actually used, so matching it whole pins the
# DESTS default's contents *and* its count, and an empty CODEX_DEST default
# with them: the `; codex-agents ->` suffix is absent only when CODEX_DEST is.
# Fixed-string and whole-line on purpose — a substring match is satisfied by an
# extra destination appended after the one it matched, which is the shape of
# the escape. Anything reproducing this must keep its probe path under $TMPDIR.
grep -Fqx "synced: skills + claude-agents + output-styles -> $work/fakehome/.claude" "$work/out" || green=false
# Second row: CODEX_DEST set, CODEX_EXCLUDES left at its default, so both
# tomls must land. Control 12's codex row only ever names clove.toml, which
# is why a default of "winston" survived it.
scaffold codex-defaults
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all")
EXCLUDES=("")
CODEX_DEST="$src/codex-dest"
EOF
run "$src"
[ "$rc" -eq 0 ] || green=false
[ -f "$src/codex-dest/clove.toml" ] || green=false
[ -f "$src/codex-dest/winston.toml" ] || green=false
ok defaults "$green" "an un-configured run did not deploy to \$HOME/.claude alone, or a default excluded something (rc=$rc)"

if [ "$fails" -eq 0 ]; then
  echo "selftest: $controls controls green"
else
  # The denominator rides both exit paths, not just the green one: without it
  # a control that never ran is indistinguishable from one that passed, which
  # is exactly the reading a red run needs and the green run does not.
  echo "selftest: $fails of $controls control(s) failed" >&2
  exit 1
fi
