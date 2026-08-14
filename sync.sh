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

# Defaults: one destination, no exclusions. This is the whole
# story for most clones — just run the script.
#
# A gitignored sync.local.sh next to this file, if present, is sourced below
# and can override any of the three: DESTS (profile roots to sync into),
# EXCLUDES (parallel array — EXCLUDES[i] is a space-separated list of skill/
# agent names to skip for DESTS[i], "" for none; kept parallel instead of an
# associative array because the macOS-shipped bash is 3.2, which predates
# them). Its absence is the normal case, not a degraded one — how you sync is
# your own affair; see README.md for the override shape and a worked example.
DESTS=("$HOME/.claude")
EXCLUDES=("")
CODEX_DEST=""
CODEX_EXCLUDES=""

if [ -f "$SRC/sync.local.sh" ]; then
  # shellcheck source=/dev/null
  source "$SRC/sync.local.sh"
fi

# Must equal render-claude-agents.py's AGENT_PREFIX. That file owns the
# value; this is a copy, and the pre-flight check below is what stops the
# copy from drifting silently. Not part of the sync.local.sh override
# contract — it describes the repo's own files, not your setup.
AGENT_PREFIX="p-"

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
# first run where that leak becomes visible. Silent when EXCLUDES is empty.
any_exclusions=false
for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  for ex in ${EXCLUDES[$i]:-}; do
    any_exclusions=true
    [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale exclusion for $dst: $ex — renamed or removed? sync may now include its successor" >&2
  done
done

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

for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  mkdir -p "$dst/skills"
  for s in "$SRC"/skills/*/; do
    [ -d "$s" ] || continue
    name=$(basename "$s")
    skip=false
    for ex in ${EXCLUDES[$i]:-}; do
      [ "$name" = "$ex" ] && skip=true && break
    done
    [ "$skip" = true ] && continue
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
    skip=false
    for ex in ${EXCLUDES[$i]:-}; do
      [ "$persona" = "$ex" ] && skip=true && break
    done
    [ "$skip" = true ] && continue
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
# One destination rather than a DESTS-parallel array, because ~/.codex/agents
# is a single global directory with no work/personal split to mirror.
# CODEX_EXCLUDES is a plain space-separated list for that one destination.
#
# The exclusion means something different here than it does above. A
# claude-agents shim preloads a same-named skill, so shipping it without the
# skill produces a persona with nothing to be; a codex toml inlines the
# persona's whole body (README.md § The codex-agents toml surface) and is
# self-contained. Excluding one is a preference about this machine, not a
# consistency requirement.
#
# Same per-file, no --delete semantics as every loop above, and it matters
# most here: a host repo's own agents (thrive-*.toml and the like) live in
# this same directory and must survive a sync that knows nothing about them.
if [ -n "$CODEX_DEST" ]; then
  mkdir -p "$CODEX_DEST"
  for f in "$SRC"/codex-agents/*.toml; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .toml)
    skip=false
    for ex in ${CODEX_EXCLUDES:-}; do
      [ "$name" = "$ex" ] && skip=true && break
    done
    [ "$skip" = true ] && continue
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
