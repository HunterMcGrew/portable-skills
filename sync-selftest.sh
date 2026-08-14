#!/usr/bin/env bash
# Controls for sync.sh's exclusion logic, in the same shape as
# render-claude-agents.py's --selftest: every control asserts the green case
# and then breaks the mechanism to prove the control goes red. A check that
# cannot fail is not a check.
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
fails=0

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
green=true
[ -e "$src/dest-filtered/skills/clove" ] || green=false
[ -e "$src/dest-filtered/agents/p-clove.md" ] || green=false
[ ! -e "$src/dest-filtered/skills/winston" ] || green=false
[ ! -e "$src/dest-filtered/agents/p-winston.md" ] || green=false
ok exclusion "$green" "excluded persona leaked, or the destination is empty"

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

# 4. No --delete: a file only the profile knows about survives a sync.
scaffold nodelete
mkdir -p "$src/dest-all/skills/local-only" "$src/dest-all/agents"
echo local >"$src/dest-all/skills/local-only/SKILL.md"
echo local >"$src/dest-all/agents/some-other-agent.md"
run "$src"
green=true
[ -e "$src/dest-all/skills/local-only/SKILL.md" ] || green=false
[ -e "$src/dest-all/agents/some-other-agent.md" ] || green=false
ok no-delete "$green" "a profile-only file was removed by the sync"

# 5. Parallel-array guard: fewer EXCLUDES than DESTS must abort rather than
# silently leave the trailing destination unfiltered.
scaffold parity
cat >"$src/sync.local.sh" <<EOF
DESTS=("$src/dest-all" "$src/dest-filtered")
EXCLUDES=("")
EOF
run "$src"
[ "$rc" -ne 0 ] && green=true || green=false
ok parity-guard "$green" "a short EXCLUDES array was accepted (rc=$rc)"

# 6. Prefix-drift guard: an agent file that does not carry AGENT_PREFIX must
# abort while exclusions are configured, since none of them can match it.
scaffold drift
echo 'name: winston' >"$src/claude-agents/winston.md"
run "$src"
[ "$rc" -ne 0 ] && green=true || green=false
ok drift-guard "$green" "an unprefixed agent file synced with exclusions live (rc=$rc)"

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
  ok empty-dests-red false "the sed did not match — this control tested nothing"
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
# output-styles is the loop this control exercises because it is the one
# of the three rm-then-cp loops (skills, agents, output-styles) with no
# other control behind it; the skills and agents loops both ride through
# controls 2/3's exclusion mechanics, which already touch the same
# rm-before-cp shape.
scaffold symlink
mkdir -p "$src/outside" "$src/dest-all/output-styles"
echo original-precious-content >"$src/outside/precious"
ln -s "$src/outside/precious" "$src/dest-all/output-styles/scannable.md"
run "$src"
green=true
[ -L "$src/dest-all/output-styles/scannable.md" ] && green=false
[ "$(cat "$src/outside/precious")" = original-precious-content ] || green=false
ok symlink-clobber "$green" "destination symlink survived the sync, or the outside file was clobbered"

# 13. The same case with all three rm-before-cp lines stripped must go red
# — otherwise control 12 passes for some reason other than the guard.
# python3, not sed, per control 3/9's own precedent: three distinct lines
# across three loops is easier to match exactly this way than to keep
# three sed expressions in sync with the source.
scaffold symlink-red
python3 - "$src/sync.sh" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
targets = (
    'rm -rf "${dst:?}/skills/${name:?}"  # removes old symlink or stale copy\n',
    'rm -f "$dst/agents/$name.md"\n',
    'rm -f "$dst/output-styles/$(basename "$f")"  # see the agents loop above\n',
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
  mkdir -p "$src/outside" "$src/dest-all/output-styles"
  echo original-precious-content >"$src/outside/precious"
  ln -s "$src/outside/precious" "$src/dest-all/output-styles/scannable.md"
  run "$src"
  if [ "$(cat "$src/outside/precious")" != original-precious-content ]; then
    green=true
  else
    green=false
  fi
  ok symlink-clobber-red "$green" "rm-before-cp removed and the outside file was not clobbered — control 12 proves nothing"
fi

# 14. Stale-exclusion warning: an entry naming a skill directory that does not
# exist warns on stderr and does not abort — sync.sh's pre-flight exclusion
# warnings, named rather than cited by line, because an edit upstream in that
# file has already invalidated this citation once. Both lists are covered:
# EXCLUDES per destination, and the CODEX_EXCLUDES pass beside it. The other
# destination's files still land, proving the warning doesn't quietly turn
# into a partial or skipped sync.
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
ok stale-exclusion "$green" "a stale exclusion did not warn on one of the two lists, a glob exclusion swallowed a persona nobody named, or the sync aborted (rc=$rc globrc=$globrc)"

# 15. The same case with both warning lines stripped must go red — otherwise
# control 14 passes for some reason other than the warnings. Both, not one: a
# strip that left the codex line standing would let control 14's new arm pass
# here too. cmp against the real file per control 9/13's own precedent, so a
# non-matching edit reports "tested nothing" instead of a false green.
scaffold stale-red
python3 - "$src/sync.sh" <<'PY'
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
ok codex-deploy "$green" "codex toml missing, exclusion ignored, a host agent was pruned, or the summary line stayed silent (rc=$rc)"

# 17. The same case with the copy stripped must go red, or control 16 is
# passing for some reason other than the loop running. cmp against the real
# file first, per control 9/13/15's precedent.
scaffold codex-red
python3 - "$src/sync.sh" <<'PY_INNER'
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
ok codex-default-off "$green" "an unset CODEX_DEST still deployed or created a directory (rc=$rc)"

if [ "$fails" -eq 0 ]; then
  echo "selftest: 17 controls green"
else
  echo "selftest: $fails control(s) failed" >&2
  exit 1
fi
