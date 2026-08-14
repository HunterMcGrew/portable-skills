#!/usr/bin/env bash
# Push this repo's skills, agent shims, and output styles into a Claude
# profile. Per-file copy on purpose: profile-only skills/agents/styles (no
# counterpart in this repo) must survive, so the loops below never use
# --delete semantics against a destination directory.
set -euo pipefail

# This script takes no arguments — there is no --check/--dry-run mode, only
# the real deploy below. An unrecognized argument must never fall through to
# the write arm: `bash sync.sh --selftest`, typed expecting a read-only pass
# (there is none; that's sync-selftest.sh, a separate file), instead ran a
# full deploy because the flag was silently ignored. Same defect class as
# render-claude-agents.py's argv guard, fixed there and not here until now.
if [ "$#" -gt 0 ]; then
  echo "usage: sync.sh (no arguments)" >&2
  exit 2
fi

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults: one destination, no exclusions, no codex deploy. This is the whole
# story for most clones — just run the script.
#
# A gitignored sync.local.sh next to this file, if present, is sourced below
# and can override any of these: DESTS (profile roots to sync into), EXCLUDES
# (parallel array — EXCLUDES[i] is a space-separated list of skill/agent names
# to skip for DESTS[i], "" for none; kept parallel instead of an associative
# array because the macOS-shipped bash is 3.2, which predates them), CODEX_DEST
# (the single directory codex tomls deploy to; empty deploys none and creates
# nothing) and CODEX_EXCLUDES (a flat space-separated list for that directory
# alone). A missing sync.local.sh is the normal case, not a degraded one — how
# you sync is your own affair; README.md has the shape and a worked example.
DESTS=("$HOME/.claude")
EXCLUDES=("")
CODEX_DEST=""
CODEX_EXCLUDES=""

if [ -f "$SRC/sync.local.sh" ]; then
  # shellcheck source=/dev/null
  source "$SRC/sync.local.sh"
fi

# BACKUP_DIR was an override once and is now read by nothing. A gitignored
# sync.local.sh that still sets it is sourced without complaint, so the
# setting looks live while no backup runs — the same silent-config failure
# the CODEX_DEST default was fixed for. Warn rather than abort: the lost
# artifact mirrored a repo that git already backs up, so nothing is at risk
# except the user's belief.
if [ -n "${BACKUP_DIR:-}" ]; then
  echo "sync.sh: BACKUP_DIR is set but nothing reads it — the backup was removed, git history is the mirror. Delete it from sync.local.sh." >&2
fi

# Must equal render-claude-agents.py's AGENT_PREFIX. That file owns the
# value; this is a copy, and the pre-flight check below is what stops the
# copy from drifting silently. Not part of the sync.local.sh override
# contract — it describes the repo's own files, not your setup.
AGENT_PREFIX="p-"

# Exclusion lists are space-separated strings, so matching one means letting
# the shell word-split it — and an unquoted expansion pathname-expands in the
# same breath. CODEX_EXCLUDES="*" then becomes whatever files happen to sit
# in the caller's cwd: it matches no persona, every toml deploys, and nothing
# is said. `set -f` for the length of the split is the fix. Quoting is not —
# a quoted expansion is one word, so a two-name list stops matching at all.
# The lists stay strings because bash 3.2 has no arrays inside arrays.
#
# The restore is conditional so this function cannot clear an option it never
# owned. No call site reaches it that way as the file stands, and that is
# measured rather than assumed: every call reports `$-=ehuB`, both with and
# without a `set -f` in sync.local.sh, because the pre-flight window below
# ends in an unconditional `set +f` that normalizes the option before the
# first call. The branch is therefore inert today. It stays because restoring
# what the caller had is the correct shape for a helper that touches a
# shell-global option, and the unconditional alternative is safe only while
# no call site sits inside a `set -f` window — a property of the call sites,
# not of this function. `local -` is the idiomatic version and is not
# available here: bash 3.2.57 rejects it outright with `-': not a valid
# identifier`, leaving the option set, so the prior state is read and put back
# by hand instead.
excluded() {  # excluded <name> <list> — true when name appears in the list
  local name="$1" list="$2" ex rc=1 had_noglob
  case $- in *f*) had_noglob=1 ;; *) had_noglob= ;; esac
  set -f
  for ex in $list; do
    if [ "$name" = "$ex" ]; then rc=0; break; fi
  done
  [ -n "$had_noglob" ] || set +f
  return "$rc"
}

# Every copy loop below is destination-first: it unlinks the destination path
# and then writes onto it. If a destination directory *is* one of this repo's
# own source directories, the unlink deletes the tracked file the copy is
# about to read, and set -e halts partway with that file already gone. Two
# ways in, both reproduced: DESTS=("$SRC") directly, and a profile whose
# skills/ is a symlink back into the repo — the state a previous sync under a
# different scheme leaves behind.
#
# The relation is equality of the *write target*, not containment of the repo
# by the destination. The loops only ever touch "$dst/<fixed-subdir>", so
# DESTS=("$HOME") with this repo somewhere under $HOME aliases nothing and is
# fine, while DESTS=("$SRC") aliases $SRC/skills exactly. -ef compares device
# and inode, so trailing slashes, . and .. segments, symlinks, relative paths
# and a case-insensitive volume all collapse to one answer — none of which a
# string compare survives, which is what the removed BACKUP_DIR guard got
# wrong. There is no realpath or readlink -f here to build an ancestor walk
# on, and none is needed.
#
# A destination that does not exist yet compares false on bash 3.2 — measured,
# both-missing and one-missing — and is correctly allowed: mkdir -p then makes
# a fresh directory, which cannot be a source. Do not "fix" that case.
#
# $SRC leads the list rather than only the four directories the loops read: a
# destination subdirectory resolving to the repo root drops untracked copies
# into the working tree, and the walk is already happening.
SRC_DIRS=("$SRC" "$SRC/skills" "$SRC/claude-agents" "$SRC/output-styles" "$SRC/codex-agents")

# refuse_self_target <label> <dir> — aborts when dir resolves to a source
# directory. One owner for all four arms: four inline guards is the shape
# that let three of them ship unguarded.
refuse_self_target() {
  local label="$1" dir="$2" s
  # :--guarded like every other array expansion in this file. SRC_DIRS is a
  # fixed literal and cannot be empty, so this is the convention holding rather
  # than a live bug — but it was the one value-form expansion left, and the
  # rule control 8 states ("the index form or :--guarded, every one of them")
  # is worth less with an exception in it than the guard costs.
  for s in "${SRC_DIRS[@]:-}"; do
    if [ "$dir" -ef "$s" ]; then
      echo "sync.sh: $label resolves to this repo's own $s — the copy is destination-first, so syncing there would delete the files it deploys (destination: $dir)" >&2
      exit 1
    fi
  done
}

# EXCLUDES and DESTS are parallel, so a missing slot means an unfiltered
# destination. Left to ${EXCLUDES[i]:-} that degrades to "no exclusions"
# without a word, which is the wrong direction to fail in — an override that
# gained a profile and forgot its slot would ship a full roster to it. An
# empty EXCLUDES is still legal and means no exclusions anywhere.
if [ "${#EXCLUDES[@]}" -ne 0 ] && [ "${#EXCLUDES[@]}" -ne "${#DESTS[@]}" ]; then
  echo "sync.sh: EXCLUDES has ${#EXCLUDES[@]} entries for ${#DESTS[@]} destinations — they must be parallel (use \"\" for a destination with no exclusions)" >&2
  exit 1
fi

# Warn loudly on a stale exclusion (a listed name with no matching skills/
# dir) before copying anything — a renamed or removed skill silently starts
# syncing to that destination under its new name otherwise, and this is the
# first run where that leak becomes visible. Silent when the lists are empty.
# One `set -f` window covers both passes, for the reason excluded() gives.
any_exclusions=false
set -f
for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  for ex in ${EXCLUDES[$i]:-}; do
    any_exclusions=true
    [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale exclusion for $dst: $ex — renamed or removed? sync may now include its successor" >&2
  done
done
# CODEX_EXCLUDES is not parallel to DESTS and names the one codex destination,
# so it gets its own pass — and deliberately does not set any_exclusions, which
# gates the AGENT_PREFIX check below: that check is about claude-agents shims
# and has nothing to say about tomls, which deploy unprefixed. Warns whether or
# not CODEX_DEST is set, like the loop above, which does not check that its own
# destination exists either.
for ex in ${CODEX_EXCLUDES:-}; do
  [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale codex exclusion: $ex — renamed or removed? sync may now include its successor" >&2
done
set +f

# Exclusions match on the agent name with AGENT_PREFIX stripped, so a prefix
# that no longer matches the files on disk makes every exclusion silently
# inert and ships the excluded persona's shim anyway. Abort instead: the
# whole point of an exclusion is that it is not quietly optional. Only
# checked when an exclusion is configured — with none, the prefix is
# irrelevant to this script and a mismatch harms nothing.
if [ "$any_exclusions" = true ]; then
  for f in "$SRC"/claude-agents/*.md; do
    [ -e "$f" ] || continue
    case "$(basename "$f")" in
      "$AGENT_PREFIX"*) ;;
      *)
        echo "sync.sh: $(basename "$f") does not start with AGENT_PREFIX '$AGENT_PREFIX', so exclusions would not match it — set AGENT_PREFIX in this script to render-claude-agents.py's value" >&2
        exit 1
        ;;
    esac
  done
fi

# Runs before the first mkdir, across every destination and every arm, so a
# bad entry late in DESTS cannot be discovered after an earlier destination
# has already been rewritten. Abort rather than skip: an aliasing destination
# is a configuration error in sync.local.sh, and skipping it would print a
# summary line for a sync that did not happen. Index form "${!DESTS[@]}", not
# the value form — an empty array under set -u on bash 3.2 is the landmine
# control 9 exists for.
for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  refuse_self_target "DESTS[$i]'s skills destination" "$dst/skills"
  refuse_self_target "DESTS[$i]'s agents destination" "$dst/agents"
  refuse_self_target "DESTS[$i]'s output-styles destination" "$dst/output-styles"
done
if [ -n "${CODEX_DEST:-}" ]; then
  refuse_self_target "CODEX_DEST" "$CODEX_DEST"
fi

for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  mkdir -p "$dst/skills"
  for s in "$SRC"/skills/*/; do
    [ -d "$s" ] || continue
    name=$(basename "$s")
    if excluded "$name" "${EXCLUDES[$i]:-}"; then continue; fi
    rm -rf "${dst:?}/skills/${name:?}"  # removes old symlink or stale copy
    cp -R "$s" "$dst/skills/$name"
  done
done

# Subagent projections ride along to every destination. Built by
# render-claude-agents.py from the same skills/ sources as codex-agents/, and
# deployed here rather than by the renderer for the same reason: rendering is
# a build step that mutates tracked files, syncing only copies committed
# ones.
#
# What this does and does not buy you turns on skills-vs-subagents
# precedence, stated once in README.md § The claude-agents subagent surface.
# Same per-file, no-delete semantics as the loop above: a profile-only agent
# nobody here knows about survives the sync.
# EXCLUDES applies here too, and it has to: an agent file is a shim whose
# `skills:` field preloads the same-named skill. Copying a persona's agent
# shim to a destination that excludes that persona's skill produces an agent
# pointing at something that isn't installed there — a persona that launches
# and then has nothing to be.
for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  mkdir -p "$dst/agents"
  for f in "$SRC"/claude-agents/*.md; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .md)
    # EXCLUDES lists skill names, while agent files are registered under a
    # prefix, so the comparison runs on the stripped name — otherwise every
    # exclusion silently stops matching and the excluded persona's shim ships
    # anyway. The pre-flight check above guarantees the strip actually bites.
    persona="${name#"$AGENT_PREFIX"}"
    if excluded "$persona" "${EXCLUDES[$i]:-}"; then continue; fi
    # rm first, same as the skills loop: cp writes *through* a destination
    # symlink, clobbering whatever it points at outside the profile
    # directory.
    rm -f "$dst/agents/$name.md"
    cp "$f" "$dst/agents/$name.md"
  done
done

# Output styles ride along to every destination, unfiltered — a profile
# running this roster without the matching style is running a different
# configuration from the one the roster was tuned against. Per-file copy
# with no --delete, same reasoning as the loops above: profile-only styles
# must survive a sync that doesn't know about them.
for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  mkdir -p "$dst/output-styles"
  for f in "$SRC"/output-styles/*.md; do
    [ -e "$f" ] || continue
    rm -f "$dst/output-styles/$(basename "$f")"  # see the agents loop above
    cp "$f" "$dst/output-styles/$(basename "$f")"
  done
done

# Codex agent projections, deployed only when CODEX_DEST is set — a clone on
# a machine with no Codex install does nothing rather than creating the
# directory. Rendered by render-agents.py from the same skills/ sources as
# claude-agents/, and deployed here for the same reason: rendering mutates
# tracked files, syncing only copies committed ones.
#
# CODEX_EXCLUDES is a flat space-separated list rather than a DESTS-parallel
# array, and an exclusion means something different on this surface than it
# does above. Both are stated once in README.md § sync.sh, not restated here.
#
# Same per-file, no --delete semantics as every loop above, and it matters
# most here: a host repo's own agents (thrive-*.toml and the like) live in
# this same directory and must survive a sync that knows nothing about them
# — differently-named ones. A host agent sharing a basename with one this
# repo ships is overwritten by the rm+cp below, which README.md § sync.sh
# states plainly and this comment used to promise away.
if [ -n "${CODEX_DEST:-}" ]; then
  # Self-target refusal for this destination happens with the others, in the
  # pre-flight above — hoisted so no mkdir precedes a refusal.
  mkdir -p "$CODEX_DEST"
  for f in "$SRC"/codex-agents/*.toml; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .toml)
    if excluded "$name" "${CODEX_EXCLUDES:-}"; then continue; fi
    # rm first, same as the agents loop: cp writes *through* a destination
    # symlink, clobbering whatever it points at outside the profile.
    rm -f "$CODEX_DEST/$name.toml"
    cp "$f" "$CODEX_DEST/$name.toml"
  done
fi

# ${DESTS[*]:-} rather than ${DESTS[*]}: on bash 3.2 an empty array expands to
# an unbound variable under set -u, which would abort here after every loop had
# already correctly done nothing.
echo "synced: skills + claude-agents + output-styles -> ${DESTS[*]:-(none)}${CODEX_DEST:+; codex-agents -> $CODEX_DEST}"
