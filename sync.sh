#!/usr/bin/env bash
# Push canonical skills to both Claude profiles + the Downloads backup.
# Per-skill copy on purpose: profile-only skills (no counterpart in canonical)
# must survive, so never use --delete semantics against either profile dir —
# that's what lets graphify (both profiles) and humanizer (work profile only)
# ride alongside the synced roster untouched.
#
# ~/.claude-work excludes the dev-workflow skills on purpose, not by
# oversight: the thrive repo (worked from that profile) provides its own
# dev-workflow personas, so the work profile takes only the business-layer/
# canonical set. Default-sync semantics otherwise — a new skill under
# skills/ reaches both profiles automatically without a list edit, unless
# its name is added here.
EXCLUDE_WORK="briar clove eli eric handoff iris lilac mira nora pixel reese ren review-loop sage sasha sol winston zoe"
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
echo "synced: ~/.claude/skills + ~/.claude-work/skills + Downloads backup"
