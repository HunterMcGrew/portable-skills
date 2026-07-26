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
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

MARK = "## Shared core (inlined for subagent self-containment)"
MARK_HR = "\n\n---\n"        # separator the toml assembler inserts before MARK


def skill_body(path_or_text, is_text=False):
    s = path_or_text if is_text else open(path_or_text).read()
    m = re.match(r'^---\n.*?\n---\n', s, re.S)
    return s[m.end():] if m else s


def frontmatter_desc(sk):
    fm = re.match(r'^---\n(.*?)\n---\n', sk, re.S).group(1)
    m = re.search(r'^description: >\n((?:  .*\n?)+)', fm, re.M)
    if m:
        return ' '.join(x.strip() for x in m.group(1).strip().split('\n'))
    return re.search(r'^description: (.*)$', fm, re.M).group(1).strip()


def render(p, root=ROOT):
    """The canonical codex-agents/<p>.toml, derived entirely from skills/.

    Verified byte-exact: re-rendering each of the 27 tomls from its own current
    parts reproduces the file exactly, 27/27 — so every difference between
    render(p) and the file on disk is content drift, never assembly churn."""
    sk = open('%s/skills/%s/SKILL.md' % (root, p)).read()
    core = open('%s/skills/_shared/core.md' % root).read()
    return ('name = %s\n' % json.dumps(p, ensure_ascii=False)
            + 'description = %s\n' % json.dumps(frontmatter_desc(sk), ensure_ascii=False)
            + "developer_instructions = '''\n"
            + skill_body(sk, is_text=True).strip('\n')
            + MARK_HR + MARK + '\n\n'
            + core.strip('\n')
            + "\n'''\n")


def regenerate_all(root=ROOT):
    """Rewrites every toml from its skills/ source. Returns the list of files changed."""
    out = []
    for t in sorted(glob.glob(root + '/codex-agents/*.toml')):
        p = os.path.basename(t)[:-5]
        new = render(p, root)
        if new != open(t).read():
            with open(t, 'w') as fh:
                fh.write(new)
            out.append(p)
    return out


if __name__ == '__main__':
    written = regenerate_all()
    total = len(glob.glob(ROOT + '/codex-agents/*.toml'))
    print('regenerated %d/%d tomls: %s'
          % (len(written), total, ' '.join(written) if written else '(all current)'))
