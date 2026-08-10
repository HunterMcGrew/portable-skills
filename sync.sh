#!/usr/bin/env bash
# Push canonical skills to both Claude profiles + the Downloads backup.
# Per-skill copy on purpose: profile-only skills (no counterpart in canonical)
# must survive, so never use --delete semantics against either profile dir —
# that's what lets graphify (both profiles) and humanizer (work profile only)
# ride alongside the synced roster untouched.
#
# ~/.claude-work takes the full canonical set: the thrive repo's own
# dev-workflow personas are all `thrive-`-prefixed (thrive-architect,
# thrive-code-dev, thrive-debugger, thrive-code-review-pr, and so on, under
# each thrive worktree's own .claude/skills/), so there is no name collision
# with this roster's `winston`/`clove`/`briar`-style names for either skills
# or their agent shims — the two sets coexist rather than one shadowing the
# other. Default-sync semantics otherwise — a new skill under skills/
# reaches both profiles automatically without a list edit, unless its name
# is added here. lilac stays excluded from the work profile, a standing
# decision unrelated to the collision concern above.
EXCLUDE_WORK="lilac"
set -euo pipefail
SRC=~/Documents/portable-skills

# Warn loudly on a stale exclusion (a listed name with no matching skills/
# dir) before copying anything — a renamed or removed skill silently starts
# syncing to the work profile under its new name otherwise, and this is the
# first run where that leak becomes visible.
for ex in $EXCLUDE_WORK; do
  [ -d "$SRC/skills/$ex" ] || echo "sync.sh: stale exclusion: $ex — renamed or removed? work-profile sync may now include its successor" >&2
done

for dst in ~/.claude/skills ~/.claude-work/skills; do
  mkdir -p "$dst"
  for s in "$SRC"/skills/*/; do
    name=$(basename "$s")
    if [ "$dst" = ~/.claude-work/skills ]; then
      skip=false
      for ex in $EXCLUDE_WORK; do
        [ "$name" = "$ex" ] && skip=true && break
      done
      [ "$skip" = true ] && continue
    fi
    rm -rf "${dst:?}/$name"            # removes old symlink or stale copy
    cp -R "$s" "$dst/$name"
  done
done
# Subagent projections ride along to both profiles. Built by
# render-claude-agents.py from the same skills/ sources as codex-agents/, and
# deployed here rather than by the renderer for the same reason: rendering is a
# build step that mutates tracked files, syncing only copies committed ones.
#
# What this does and does not buy you turns on skills-vs-subagents precedence,
# stated once in README.md § The claude-agents subagent surface.
# Same per-file, no-delete semantics as the loops above: a profile-only agent
# nobody here knows about survives the sync.
# EXCLUDE_WORK applies here too, and it has to: an agent file is a shim whose
# `skills:` field preloads the same-named skill. Copying winston.md to the work
# profile while the winston *skill* is excluded from it produces an agent
# pointing at something that isn't installed — a persona that launches and then
# has nothing to be.
for dst in ~/.claude/agents ~/.claude-work/agents; do
  mkdir -p "$dst"
  for f in "$SRC"/claude-agents/*.md; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .md)
    if [ "$dst" = ~/.claude-work/agents ]; then
      skip=false
      for ex in $EXCLUDE_WORK; do
        [ "$name" = "$ex" ] && skip=true && break
      done
      [ "$skip" = true ] && continue
    fi
    # rm first, same as the skills loop: cp writes *through* a destination
    # symlink, clobbering whatever it points at outside the profile directory.
    rm -f "$dst/$name.md"
    cp "$f" "$dst/$name.md"
  done
done

# Output styles ride along to both profiles. This was the sync's real gap: the
# THR-851 bake-off measured the output style as a *larger* lever on response
# shape than the entire skill redesign (+113% chat output from the style alone,
# vs ~500 words for slim-vs-fat), so a profile running the roster without the
# matching style is running a different experiment than the one that was tuned.
# Per-file copy with no --delete, same reasoning as the skills loop above:
# profile-only styles (eli5) must survive a sync that doesn't know about them.
for dst in ~/.claude/output-styles ~/.claude-work/output-styles; do
  mkdir -p "$dst"
  for f in "$SRC"/output-styles/*.md; do
    [ -e "$f" ] || continue
    # rm first — see the claude-agents loop above; a symlinked destination
    # would otherwise be written through.
    rm -f "$dst/$(basename "$f")"
    cp "$f" "$dst/$(basename "$f")"
  done
done

mkdir -p ~/Downloads/portable-skills-backup
# --exclude protects the guarded copy below: sol-internal-autonomy.md lives in
# ~/worklogs, outside $SRC, so --delete would remove the previous backup of it
# on every run *before the guarded cp below runs*. Excluded files are skipped on the receiving
# side unless --delete-excluded is also passed, so the prior copy survives a run
# where the source is missing — which is what makes the "skipped" note truthful.
rsync -a --delete --exclude='sol-internal-autonomy.md' "$SRC/" ~/Downloads/portable-skills-backup/
# Guarded on purpose: this file is the last statement in the script, after
# the real sync work above already succeeded. Left bare under set -e, a
# rename or delete of this one plan file would abort here and misreport a
# completed sync as a failure — so a miss is noted, not fatal.
if [ -f ~/worklogs/portable-skills/plans/sol-internal-autonomy.md ]; then
  cp ~/worklogs/portable-skills/plans/sol-internal-autonomy.md ~/Downloads/portable-skills-backup/
else
  echo "sync.sh: sol-internal-autonomy.md not found, skipped (backup otherwise complete)" >&2
fi
echo "synced: skills + claude-agents + output-styles -> ~/.claude and ~/.claude-work; full tree -> Downloads backup"
