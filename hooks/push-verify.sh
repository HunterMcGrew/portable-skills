#!/bin/bash

# Claude PreToolUse hook for Bash: runs prettier, next lint, and check-types
# over the commits a `git push` would carry, and denies the push when one
# fails. A port of thrive's .githooks/pre-push (THR-2358) into the harness,
# so the checks run before the push leaves the machine even on a checkout
# that has not installed that git hook. CI stays the gate; this is the
# fast-fail in front of it.
#
# Inert outside thrive: the working directory of the push (the payload cwd,
# or the `-C` directory of the push segment) must sit under a
# .ai-spec/architect/manifest.json, or the hook exits without output.
#
# Yields to the repo's own hook: when .githooks/pre-push exists and
# core.hooksPath resolves to that directory, or an executable pre-push sits
# in the repo's git hooks directory, git itself will run the same checks on
# the push, and running them twice only doubles the wait.
#
# Every path exits 0. A deny travels as the PreToolUse JSON envelope on
# stdout; a skipped check is one line on stderr. Failing open is deliberate:
# a hook that blocks pushes because Docker is off gets worked around, which
# is worse than a visible skip.
#
# Routing follows .ai-spec/rules/command-execution.md: prettier and next lint
# are host-safe; check-types is a Linux binary, so on Darwin it goes through
# the thrive-admin-1 container and is skipped with a notice when that
# container is down. Any other host skips it the same way.
#
# Runs under macOS /bin/bash 3.2: no mapfile, no associative arrays, no
# case-modifying expansions.

set -u

payload="$(cat)"
case "$payload" in
  *push*) ;;
  *) exit 0 ;;
esac

# cwd on the first line, the command on the rest — a command can carry
# newlines, a directory cannot. Malformed JSON prints nothing and exits 0.
fields="$(printf '%s' "$payload" | node -e '
  let raw = "";
  process.stdin.on("data", (chunk) => { raw += chunk; });
  process.stdin.on("end", () => {
    try {
      const p = JSON.parse(raw);
      if (p.tool_name && p.tool_name !== "Bash") return;
      const command = (p.tool_input && p.tool_input.command) || "";
      process.stdout.write((p.cwd || "") + "\n" + command);
    } catch (_) {}
  });
' 2>/dev/null)" || exit 0
[ -n "$fields" ] || exit 0
cwd="${fields%%$'\n'*}"
command="${fields#*$'\n'}"
[ "$command" != "$fields" ] || exit 0

# --- Find the push segment ---

# Prints the directory a `git [-C <dir>] push` segment runs in, or nothing.
# Segments are the command split on the shell's list and pipe operators;
# quoting inside a segment is not honoured beyond stripping the quotes around
# a -C value, which covers the forms an agent writes.
find_push_dir() {
  local segment dir
  while IFS= read -r segment; do
    # shellcheck disable=SC2086
    set -- $segment
    [ "${1:-}" = git ] || continue
    shift
    dir="$cwd"
    while [ "$#" -gt 0 ]; do
      case "$1" in
        -C)
          [ "$#" -ge 2 ] || return 1
          dir="$2"
          dir="${dir#\"}"; dir="${dir%\"}"
          dir="${dir#\'}"; dir="${dir%\'}"
          case "$dir" in
            /*) ;;
            *) dir="$cwd/$dir" ;;
          esac
          shift 2
          ;;
        -*) shift ;;
        push)
          printf '%s' "$dir"
          return 0
          ;;
        *) break ;;
      esac
    done
  done < <(printf '%s\n' "$command" | awk '{ gsub(/&&|\|\||;|\|/, "\n"); print }')
  return 1
}

push_dir="$(find_push_dir)" || exit 0
cd "$push_dir" 2>/dev/null || exit 0

# --- Early exits ---

manifest_dir="$push_dir"
while [ ! -f "$manifest_dir/.ai-spec/architect/manifest.json" ]; do
  [ "$manifest_dir" != / ] || exit 0
  manifest_dir="$(dirname "$manifest_dir")"
done

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

hooks_path="$(git config core.hooksPath 2>/dev/null || true)"
if [ -n "$hooks_path" ] && [ -f "$repo_root/.githooks/pre-push" ]; then
  case "$hooks_path" in
    /*) ;;
    *) hooks_path="$repo_root/$hooks_path" ;;
  esac
  [ "$hooks_path" -ef "$repo_root/.githooks" ] && exit 0
fi
[ -x "$(git rev-parse --git-path hooks)/pre-push" ] && exit 0

host="$(uname -s)"

# --- Collect the changed set ---

upstream="$(git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)" || upstream=origin/main
base="$(git merge-base "$upstream" HEAD 2>/dev/null)" || {
  echo "push-verify: no $upstream to diff against — checks skipped, CI will run them" >&2
  exit 0
}

# Sort and dedupe without `mapfile`. IFS= and -r keep paths with spaces or
# backslashes intact.
changed=()
while IFS= read -r changed_path; do
  [ -n "$changed_path" ] || continue
  # A path deleted at HEAD has nothing to format or lint.
  git cat-file -e "HEAD:$changed_path" 2>/dev/null || continue
  changed+=("$changed_path")
done < <(git diff --name-only "$base" HEAD | sort -u)

[ "${#changed[@]}" -gt 0 ] || exit 0

# --- Filter into the three tool sets ---

extension_of() {
  case "$1" in
    *.*) printf '%s' "${1##*.}" ;;
    *) printf '' ;;
  esac
}

# Paths prettier and next lint reach: the frontend and the three first-party
# plugins' src trees, in the extensions prettier is configured for. The trees
# verification-commands.md § Formatting keeps prettier off — docs/content and
# the plans tree — sit outside this allowlist by construction.
is_lintable_path() {
  case "$1" in
    frontend/*) ;;
    backend/plugins/gravity-platform-core/src/*|backend/plugins/thrive-sss/src/*|backend/plugins/thrive-byo/src/*) ;;
    *) return 1 ;;
  esac
  case "$(extension_of "$1")" in
    js|jsx|ts|tsx|css|scss|json|md|mdx) return 0 ;;
    *) return 1 ;;
  esac
}

is_workspace_ts_path() {
  case "$(extension_of "$1")" in
    ts|tsx) ;;
    *) return 1 ;;
  esac
  case "$1" in
    frontend/*|admin/*|docs/*|packages/*|backend/plugins/gravity-platform-core/*) return 0 ;;
    *) return 1 ;;
  esac
}

# Every prettier and lint command runs from frontend/, so a path is rewritten
# relative to that directory.
relative_to_frontend() {
  case "$1" in
    frontend/*) printf '%s' "${1#frontend/}" ;;
    *) printf '../%s' "$1" ;;
  esac
}

prettier_paths=()
lint_paths=()
needs_types=""
for changed_path in "${changed[@]}"; do
  if is_lintable_path "$changed_path"; then
    prettier_paths+=("$(relative_to_frontend "$changed_path")")
    case "$(extension_of "$changed_path")" in
      js|jsx|ts|tsx) lint_paths+=("$(relative_to_frontend "$changed_path")") ;;
    esac
  fi
  is_workspace_ts_path "$changed_path" && needs_types=1
done

# --- Run ---

deny() {  # deny <check> <output tail> — writes the PreToolUse deny envelope
  CHECK="$1" TAIL="$2" node -e '
    const reason = "push-verify: " + process.env.CHECK + " failed:\n" + process.env.TAIL;
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: reason,
      },
    }));
  '
}

run_check() {
  local label="$1"
  local dir="$2"
  shift 2

  local output
  if ! output="$(cd "$dir" && "$@" 2>&1)"; then
    deny "$label" "$(printf '%s\n' "$output" | tail -n 40)"
    exit 0
  fi
}

if [ "${#prettier_paths[@]}" -gt 0 ]; then
  run_check prettier "$repo_root/frontend" npx prettier --check "${prettier_paths[@]}"
fi

for lint_path in "${lint_paths[@]+"${lint_paths[@]}"}"; do
  run_check "next lint" "$repo_root/frontend" npx next lint --file "$lint_path"
done

if [ -n "$needs_types" ]; then
  case "$host" in
    Linux)
      run_check check-types "$repo_root" pnpm -r run check-types
      ;;
    Darwin)
      if docker exec thrive-admin-1 true >/dev/null 2>&1; then
        run_check check-types "$repo_root" docker exec thrive-admin-1 bash -lc 'cd /workspace && pnpm -r run check-types'
      else
        echo "push-verify: thrive-admin-1 not running — check-types skipped, CI will run it" >&2
      fi
      ;;
    *)
      echo "push-verify: check-types needs Linux or the thrive-admin-1 container — check-types skipped, CI will run it" >&2
      ;;
  esac
fi

exit 0
