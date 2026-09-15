#!/bin/bash
# Cases for push-verify.sh, run with /bin/bash so bash 3.2 is what executes
# both files. Everything happens in a mktemp fixture: a bare origin holding
# main, a clone carrying a manifest and a frontend/ tree, and a feature branch
# with one committed frontend/a.ts. npx, docker, pnpm, and uname are stubs
# prepended to PATH; each logs its argv and exits per STUB_RC (or
# STUB_RC_<name> for one tool), so a case can make prettier fail while the
# container probe passes, or the reverse.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
hook="$here/push-verify.sh"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
fails=0
cases=0

# --- Stubs ---

stubs="$work/stubs"
mkdir -p "$stubs"
for tool in npx docker pnpm uname; do
  cat >"$stubs/$tool" <<'STUB'
#!/bin/bash
name="$(basename "$0")"
printf '%s %s\n' "$name" "$*" >>"${STUB_LOG:-/dev/null}"
if [ "$name" = uname ]; then
  printf '%s\n' "${STUB_UNAME:-Darwin}"
  exit 0
fi
eval "rc=\${STUB_RC_$name:-\${STUB_RC:-0}}"
[ "$rc" -eq 0 ] || echo "stub $name failing on purpose: $*"
exit "$rc"
STUB
  chmod +x "$stubs/$tool"
done
export PATH="$stubs:$PATH"
export STUB_LOG="$work/stub.log"

# --- Fixture ---

git init -q --bare "$work/origin.git"
git init -q -b main "$work/repo"
repo="$work/repo"
git -C "$repo" config user.email test@example.com
git -C "$repo" config user.name test
mkdir -p "$repo/.ai-spec/architect" "$repo/frontend" "$repo/docs"
echo '{}' >"$repo/.ai-spec/architect/manifest.json"
echo 'export const base = 1;' >"$repo/frontend/base.ts"
git -C "$repo" add -A
git -C "$repo" commit -q -m init
git -C "$repo" remote add origin "$work/origin.git"
# The fixture's own bare origin, seeded so origin/main exists for merge-base.
git -C "$repo" push -q origin main
git -C "$repo" checkout -q -b feature
echo 'export const a = 1;' >"$repo/frontend/a.ts"
git -C "$repo" add frontend/a.ts
git -C "$repo" commit -q -m "add a.ts"
git -C "$repo" checkout -q -b docs-only main
echo '# x' >"$repo/docs/x.md"
git -C "$repo" add docs/x.md
git -C "$repo" commit -q -m "add docs"
git -C "$repo" checkout -q feature

# --- Harness ---

payload() {  # payload <cwd> <command>
  CWD="$1" CMD="$2" node -e '
    process.stdout.write(JSON.stringify({
      tool_name: "Bash",
      cwd: process.env.CWD,
      tool_input: { command: process.env.CMD },
    }));
  '
}

run_hook() {  # run_hook <cwd> <command> — sets out, err, rc
  : >"$STUB_LOG"
  rc=0
  out="$(payload "$1" "$2" | /bin/bash "$hook" 2>"$work/err")" || rc=$?
  err="$(cat "$work/err")"
}

deny_reason() {  # prints permissionDecisionReason from $out, or nothing
  OUT="$out" node -e '
    try {
      const o = JSON.parse(process.env.OUT).hookSpecificOutput;
      if (o.permissionDecision === "deny") process.stdout.write(o.permissionDecisionReason);
    } catch (_) {}
  '
}

check() {  # check <name> <true|false> <failure detail>
  cases=$((cases + 1))
  if [ "$2" = true ]; then
    printf 'PASS %s\n' "$1"
  else
    printf 'FAIL %s — %s\n' "$1" "$3"
    fails=$((fails + 1))
  fi
}

silent() {  # true when the last run produced no stdout and exited 0
  [ "$rc" -eq 0 ] && [ -z "$out" ]
}

tools_untouched() {  # true when no check ran; uname is the host probe, not a check
  ! grep -qE '^(npx|docker|pnpm) ' "$STUB_LOG"
}

# 1. A command with no push segment is ignored before git is consulted.
STUB_RC=1 run_hook "$repo" "git status && echo push"
silent && green=true || green=false
check non-push-silent "$green" "rc=$rc out=$out"

# 2. A repo with no manifest above it is outside thrive; nothing runs.
# The clone carries the committed manifest, so it is deleted from disk here.
git clone -q "$work/origin.git" "$work/plain"
rm "$work/plain/.ai-spec/architect/manifest.json"
STUB_RC=1 run_hook "$work/plain" "git push origin main"
silent && tools_untouched && green=true || green=false
check no-manifest-silent "$green" "rc=$rc out=$out log=$(cat "$STUB_LOG")"

# 3. An executable pre-push in the git hooks directory means git runs the
# checks itself.
git_hooks="$(git -C "$repo" rev-parse --git-path hooks)"
case "$git_hooks" in /*) ;; *) git_hooks="$repo/$git_hooks" ;; esac
mkdir -p "$git_hooks"
printf '#!/bin/sh\nexit 0\n' >"$git_hooks/pre-push"
chmod +x "$git_hooks/pre-push"
STUB_RC=1 run_hook "$repo" "git push origin feature"
silent && tools_untouched && green=true || green=false
check installed-hook-yields "$green" "rc=$rc out=$out log=$(cat "$STUB_LOG")"
rm -f "$git_hooks/pre-push"

# 4. .githooks/pre-push with core.hooksPath pointing at that directory.
mkdir -p "$repo/.githooks"
printf '#!/bin/sh\nexit 0\n' >"$repo/.githooks/pre-push"
git -C "$repo" config core.hooksPath .githooks
STUB_RC=1 run_hook "$repo" "git push origin feature"
silent && tools_untouched && green=true || green=false
check hookspath-yields "$green" "rc=$rc out=$out log=$(cat "$STUB_LOG")"
git -C "$repo" config --unset core.hooksPath
rm -rf "$repo/.githooks"

# 5. A failing check denies, and the stub's own output is in the reason.
STUB_RC=1 run_hook "$repo" "git push origin feature"
reason="$(deny_reason)"
green=true
[ "$rc" -eq 0 ] || green=false
case "$reason" in
  "push-verify: prettier failed:"*"stub npx failing on purpose: prettier --check a.ts"*) ;;
  *) green=false ;;
esac
check failure-denies "$green" "rc=$rc out=$out"

# 6. Every check passing is silent, and all three ran on Darwin.
STUB_RC=0 run_hook "$repo" "git push origin feature"
green=true
silent || green=false
grep -q '^npx prettier --check a.ts$' "$STUB_LOG" || green=false
grep -q '^npx next lint --file a.ts$' "$STUB_LOG" || green=false
grep -q '^docker exec thrive-admin-1 bash -lc cd /workspace && pnpm -r run check-types$' "$STUB_LOG" || green=false
check success-silent "$green" "rc=$rc out=$out err=$err log=$(cat "$STUB_LOG")"

# 7. A docs-only change reaches none of the tools.
git -C "$repo" checkout -q docs-only
STUB_RC=1 run_hook "$repo" "git push origin docs-only"
silent && tools_untouched && green=true || green=false
check docs-only-skips-tools "$green" "rc=$rc out=$out log=$(cat "$STUB_LOG")"
git -C "$repo" checkout -q feature

# 8. Darwin with the container down: a stderr notice, no deny, no
# check-types run.
STUB_RC=0 STUB_RC_docker=1 run_hook "$repo" "git push origin feature"
green=true
silent || green=false
case "$err" in *"thrive-admin-1 not running"*"check-types skipped"*) ;; *) green=false ;; esac
grep -q 'pnpm -r run check-types' "$STUB_LOG" && green=false
check docker-down-notice "$green" "rc=$rc out=$out err=$err log=$(cat "$STUB_LOG")"

# 9. `git -C <dir> push` from a cwd outside the repo: the -C directory is
# where the manifest walk and the checks run, so this denies where a cwd-only
# reading would have stayed silent.
STUB_RC=1 run_hook "$work" "git -C $repo push origin feature"
reason="$(deny_reason)"
case "$reason" in
  "push-verify: prettier failed:"*) green=true ;;
  *) green=false ;;
esac
check dash-C-form "$green" "rc=$rc out=$out"

if [ "$fails" -eq 0 ]; then
  echo "push-verify.test: $cases cases green"
else
  echo "push-verify.test: $fails of $cases case(s) failed" >&2
  exit 1
fi
