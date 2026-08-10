#!/usr/bin/env bash
# Push this repo's skills, agent shims, and output styles into a Claude
# profile. Per-file copy on purpose: profile-only skills/agents/styles (no
# counterpart in this repo) must survive, so the loops below never use
# --delete semantics against a destination directory.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults: one destination, no exclusions, no backup. This is the whole
# story for most clones — just run the script.
#
# A gitignored sync.local.sh next to this file, if present, is sourced below
# and can override any of the three: DESTS (profile roots to sync into),
# EXCLUDES (parallel array — EXCLUDES[i] is a space-separated list of skill/
# agent names to skip for DESTS[i], "" for none; kept parallel instead of an
# associative array because the macOS-shipped bash is 3.2, which predates
# them), and BACKUP_DIR (an optional extra full-tree copy target). Its
# absence is the normal case, not a degraded one — how you sync is your own
# affair; see README.md for the override shape and a worked example.
DESTS=("$HOME/.claude")
EXCLUDES=("")
BACKUP_DIR=""

if [ -f "$SRC/sync.local.sh" ]; then
  # shellcheck source=/dev/null
  source "$SRC/sync.local.sh"
fi

# Warn loudly on a stale exclusion (a listed name with no matching skills/
# dir) before copying anything — a renamed or removed skill silently starts
# syncing to that destination under its new name otherwise, and this is the
# first run where that leak becomes visible. Silent when EXCLUDES is empty.
for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  for ex in ${EXCLUDES[$i]:-}; do
    [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale exclusion for $dst: $ex — renamed or removed? sync may now include its successor" >&2
  done
done

for i in "${!DESTS[@]}"; do
  dst="${DESTS[$i]}"
  mkdir -p "$dst/skills"
  for s in "$SRC"/skills/*/; do
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
    # prefix (render-claude-agents.py's AGENT_PREFIX), so the comparison runs
    # on the stripped name — otherwise every exclusion silently stops
    # matching and the excluded persona's shim ships anyway.
    persona="${name#p-}"
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
for dst in "${DESTS[@]}"; do
  mkdir -p "$dst/output-styles"
  for f in "$SRC"/output-styles/*.md; do
    [ -e "$f" ] || continue
    rm -f "$dst/output-styles/$(basename "$f")"  # see the agents loop above
    cp "$f" "$dst/output-styles/$(basename "$f")"
  done
done

if [ -n "$BACKUP_DIR" ]; then
  mkdir -p "$BACKUP_DIR"
  rsync -a --delete "$SRC/" "$BACKUP_DIR/"
fi

echo "synced: skills + claude-agents + output-styles -> ${DESTS[*]}${BACKUP_DIR:+; full tree -> $BACKUP_DIR}"
