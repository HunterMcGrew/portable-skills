#!/usr/bin/env python3
# Derive codex-agents/*.toml from skills/ — one command instead of a hand-port.
#
# The toml surface used to be maintained by hand alongside skills/, and hand-ports
# drift: the pronoun-consistency run found the two surfaces had quietly diverged —
# 174 lines that had landed in skills/ and never made it across, 63 stale lines
# left over from earlier revisions, and one stale `description` field — none of
# it visible to a plain diff, because nothing asserted the two surfaces stayed in
# sync. render() makes every toml a pure function of its skill's SKILL.md plus
# the shared core, so that class of drift can only come back if someone hand-edits
# a toml directly instead of editing skills/ and re-running this file.
#
# This is a build step (skills/ -> codex-agents/), not a deploy step (repo ->
# profiles) — sync.sh does the latter. Deliberately not wired together: folding
# this in would make sync.sh mutate tracked files on every run, which is a
# different kind of side effect than copying already-committed files out.
#
# Usage: python3 render-agents.py   # regenerates every toml in place, idempotent
#
# Iterates skills/, not codex-agents/: a persona added under skills/ gets a
# toml the first time this runs, and a toml with no matching persona in
# skills/ is reported as an orphan on stderr rather than touched or crashed on.
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

MARK = "## Shared core (inlined for subagent self-containment)"
MARK_HR = "\n\n---\n"        # separator the toml assembler inserts before MARK


def skill_body(path_or_text, is_text=False):
    s = path_or_text if is_text else open(path_or_text).read()
    m = re.match(r'^---\n.*?\n---\n', s, re.S)
    return s[m.end():] if m else s


def frontmatter_desc(sk, name=None):
    """Extract the frontmatter `description:` field. Handles both block-scalar
    forms (`>`, `>-`, `|`, `|-`) and a plain single-line scalar, and raises
    ValueError naming the offending skill on anything else — a bare-YAML
    scalar indicator (`>-`) or a missing description must never come back as
    if it were the description itself."""
    fm_m = re.match(r'^---\n(.*?)\n---\n', sk, re.S)
    if not fm_m:
        raise ValueError('no frontmatter block' + (' in %s' % name if name else ''))
    fm = fm_m.group(1)
    m = re.search(r'^description:[ \t]*[>|]([-+]?)[ \t]*\n((?:[ \t]+.*\n?)+)', fm, re.M)
    if m:
        return ' '.join(x.strip() for x in m.group(2).strip().split('\n'))
    m = re.search(r'^description:[ \t]*(?![>|])(.+)$', fm, re.M)
    if not m:
        raise ValueError('unparsable description in frontmatter'
                          + (' of %s' % name if name else ''))
    return m.group(1).strip()


def render(p, root=ROOT):
    """The canonical codex-agents/<p>.toml, derived entirely from skills/.

    Verified byte-exact: re-rendering each of the 27 tomls from its own current
    parts reproduces the file exactly, 27/27 — so every difference between
    render(p) and the file on disk is content drift, never assembly churn."""
    sk = open('%s/skills/%s/SKILL.md' % (root, p)).read()
    core = open('%s/skills/_shared/core.md' % root).read()
    return ('name = %s\n' % json.dumps(p, ensure_ascii=False)
            + 'description = %s\n' % json.dumps(frontmatter_desc(sk, name=p), ensure_ascii=False)
            + "developer_instructions = '''\n"
            + skill_body(sk, is_text=True).strip('\n')
            + MARK_HR + MARK + '\n\n'
            + core.strip('\n')
            + "\n'''\n")


def has_persona_line(sk_text):
    """True if the skill declares a persona ('You are **X**' as a body line).
    A utility skill (handoff, review-loop) has no such line and gets no toml —
    the absence of the line is the signal, not an oversight."""
    body = skill_body(sk_text, is_text=True)
    return any(l.startswith('You are **') for l in body.split('\n'))


def personas(root=ROOT):
    """Every skills/<p> that should have a codex-agents/<p>.toml: those whose
    SKILL.md declares a persona. Iterating this set (not codex-agents/*.toml)
    is what lets a newly added persona get a toml the first time this runs,
    instead of being silently skipped because no stub toml exists for it yet."""
    out = []
    for f in sorted(glob.glob(root + '/skills/*/SKILL.md')):
        p = os.path.basename(os.path.dirname(f))
        if has_persona_line(open(f).read()):
            out.append(p)
    return out


def regenerate_all(root=ROOT):
    """Rewrites every persona's toml from its skills/ source, creating one for
    any persona that doesn't have one yet. Returns (written, orphans):
    written is the list of persona names whose toml was created or updated;
    orphans is any codex-agents/*.toml with no matching persona in skills/
    (skill dir removed, renamed, or demoted to a utility) — reported by name,
    left untouched, never rendered.

    Renders every persona before writing any file. render() raises ValueError
    on a malformed skills/ source (missing frontmatter, unparsable
    description) instead of crashing with a bare AttributeError; rendering
    everything first means one bad source is reported for every offending
    persona without leaving codex-agents/ half-regenerated."""
    rendered, errors = {}, []
    for p in personas(root):
        try:
            rendered[p] = render(p, root)
        except ValueError as e:
            errors.append('%s.toml: %s' % (p, e))
    if errors:
        raise ValueError('cannot regenerate — fix skills/ source first:\n  '
                          + '\n  '.join(errors))
    out = []
    for p, new in rendered.items():
        t = root + '/codex-agents/%s.toml' % p
        cur = open(t).read() if os.path.exists(t) else None
        if new != cur:
            with open(t, 'w') as fh:
                fh.write(new)
            out.append(p)
    valid = set(personas(root))
    orphans = []
    for t in sorted(glob.glob(root + '/codex-agents/*.toml')):
        p = os.path.basename(t)[:-5]
        if p in valid:
            continue
        if not os.path.exists('%s/skills/%s/SKILL.md' % (root, p)):
            reason = 'no skills/%s/SKILL.md' % p
        else:
            reason = 'skills/%s/SKILL.md has no persona line' % p
        orphans.append('%s.toml (%s)' % (p, reason))
    return out, orphans


if __name__ == '__main__':
    try:
        written, orphans = regenerate_all()
    except ValueError as e:
        print('error: %s' % e, file=sys.stderr)
        sys.exit(1)
    total = len(personas())
    print('regenerated %d/%d tomls: %s'
          % (len(written), total, ' '.join(written) if written else '(all current)'))
    if orphans:
        print('orphan tomls (fix skills/, do not hand-edit): %s' % ', '.join(orphans),
              file=sys.stderr)
