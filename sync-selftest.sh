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
  mkdir -p "$src"/{skills/winston,skills/clove,claude-agents,output-styles}
  echo skill >"$src/skills/winston/SKILL.md"
  echo skill >"$src/skills/clove/SKILL.md"
  echo 'name: p-winston' >"$src/claude-agents/p-winston.md"
  echo 'name: p-clove' >"$src/claude-agents/p-clove.md"
  echo style >"$src/output-styles/scannable.md"
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

# 7. Backup guard: a BACKUP_DIR that is not a dedicated directory must abort
# before rsync --delete runs. HOME is the fake one, so a broken guard prunes
# scratch rather than a home directory.
scaffold backup
mkdir -p "$work/fakehome"
echo precious >"$work/fakehome/unrelated-file"
cat >>"$src/sync.local.sh" <<EOF
BACKUP_DIR="$work/fakehome"
EOF
run "$src"
green=true
[ "$rc" -ne 0 ] || green=false
[ -e "$work/fakehome/unrelated-file" ] || green=false
ok backup-guard "$green" "BACKUP_DIR=\$HOME was accepted, or rsync --delete ran (rc=$rc)"

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

if [ "$fails" -eq 0 ]; then
  echo "selftest: 11 controls green"
else
  echo "selftest: $fails control(s) failed" >&2
  exit 1
fi
