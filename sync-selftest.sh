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
run() {
  rc=0
  HOME="$work/fakehome" "$1/sync.sh" >"$work/out" 2>"$work/err" || rc=$?
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

if [ "$fails" -eq 0 ]; then
  echo "selftest: 7 controls green"
else
  echo "selftest: $fails control(s) failed" >&2
  exit 1
fi
