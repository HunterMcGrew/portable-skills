#!/usr/bin/env bash
# Push canonical skills to both Claude profiles + the Downloads backup.
# Per-skill copy on purpose: profile-only skills (no counterpart in canonical)
# must survive, so never use --delete semantics against the profile dirs.
set -euo pipefail
SRC=~/Documents/portable-skills
for dst in ~/.claude/skills ~/.claude-work/skills; do
  mkdir -p "$dst"
  for s in "$SRC"/skills/*/; do
    name=$(basename "$s")
    rm -rf "${dst:?}/$name"          # removes old symlink or stale copy
    cp -R "$s" "$dst/$name"
  done
done
mkdir -p ~/Downloads/portable-skills-backup
rsync -a --delete "$SRC/" ~/Downloads/portable-skills-backup/
# Guarded on purpose: this file is the last statement in the script, after
# the real sync work above already succeeded. Left bare under set -e, a
# rename or delete of this one plan file would abort here and misreport a
# completed sync as a failure — so a miss is noted, not fatal.
if [ -f ~/worklogs/portable-skills/plans/sol-internal-autonomy.md ]; then
  cp ~/worklogs/portable-skills/plans/sol-internal-autonomy.md ~/Downloads/portable-skills-backup/
else
  echo "sync.sh: sol-internal-autonomy.md not found, skipped (backup otherwise complete)" >&2
fi
echo "synced: 2 profiles + Downloads backup"
