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
MARK_VERIF = "## Verification reference (inlined for subagent self-containment)"
MARK_HR = "\n\n---\n"        # separator the toml assembler inserts before MARK

# _shared/verification.md is loaded on demand in Claude Code (core.md points at
# it from the closing battery, and only grading personas follow the pointer).
# A codex agent has no such file to open, so the toml carries it inline for
# every persona rather than for a guessed subset — parity beats a marker that
# would need maintaining, and the cost is one short reference.

# Any other _shared/<name>.md a persona's own SKILL.md text points at (e.g.
# worktree-safety.md, read on demand by zoe/eric/sol/clove) is inlined only
# for the personas that cite it — unlike verification.md, this content is
# relevant to a handful of personas, not all 27, so blanket inlining would
# bloat every other toml with a pointer it never follows. A codex agent has
# no filesystem to resolve the pointer at runtime, so leaving it uninlined
# is a silently broken reference, not a graceful on-demand read.
EXTRA_SHARED_RE = re.compile(r'_shared/([\w-]+)\.md')
EXTRA_SHARED_SKIP = {'core', 'verification'}

# skills/<p>/references/<name>.md is the same problem one directory over. A
# persona's own reference files hold content relocated out of its SKILL.md —
# a rarely-fired mode, an on-demand procedure — and the body points at them by
# path. In Claude Code that pointer resolves against the filesystem; in a codex
# toml it resolves against nothing, so an uninlined reference is the identical
# silently-broken pointer the block above rules out for _shared fragments.
# Cited either as `references/<name>.md` or `skills/<p>/references/<name>.md`;
# the optional prefix names the owning persona, defaulting to the citing one.
# Guarded by a negative lookbehind rejecting path-continuation characters
# rather than left bare: unanchored, a future foreign `.../references/*.md`
# citation — one nested under some other path, not just `skills/<p>/` — would
# match with owner=None and silently resolve against the citing persona. The
# lookbehind rejects exactly that case (the citation is preceded by `/`) while
# an allowlist of legal delimiters would also drop a citation written inside
# quotes, asterisks or brackets, which no check on this file can see: both
# toml-drift and citation-inlined read the surface through this same regex.
REFERENCE_RE = re.compile(r'(?<![\w/.-])(?:skills/([\w-]+)/)?references/([\w-]+)\.md')


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
    verif = open('%s/skills/_shared/verification.md' % root).read()
    body = skill_body(sk, is_text=True).strip('\n')

    extra = ''
    for name in sorted(set(m for m in EXTRA_SHARED_RE.findall(body) if m not in EXTRA_SHARED_SKIP)):
        content = open('%s/skills/_shared/%s.md' % (root, name)).read()
        mark = '## %s reference (inlined for subagent self-containment)' % name
        extra += MARK_HR + mark + '\n\n' + content.strip('\n')

    for owner, name in sorted(set(REFERENCE_RE.findall(body))):
        owner = owner or p
        ref = '%s/skills/%s/references/%s.md' % (root, owner, name)
        if not os.path.exists(ref):
            raise ValueError('cites references/%s.md, which does not exist at '
                             'skills/%s/references/' % (name, owner))
        content = open(ref).read()
        mark = ('## references/%s.md (inlined for subagent self-containment)'
                % name)
        extra += MARK_HR + mark + '\n\n' + content.strip('\n')

    return ('name = %s\n' % json.dumps(p, ensure_ascii=False)
            + 'description = %s\n' % json.dumps(frontmatter_desc(sk, name=p), ensure_ascii=False)
            + "developer_instructions = '''\n"
            + body
            + MARK_HR + MARK + '\n\n'
            + core.strip('\n')
            + MARK_HR + MARK_VERIF + '\n\n'
            + verif.strip('\n')
            + extra
            + "\n'''\n")


PERSONA_DECL_RE = re.compile(
    r'^You are \*\*[A-Z][a-z]+\*\* \((?:he/him|she/her|they/them)\),')


def has_persona_line(sk_text):
    """True if the skill declares a persona in the canonical form
    ('You are **Name** (pronouns), ...') as the first non-blank line of the
    persona body — matching core.md's convention exactly, rather than
    "any line anywhere starts with 'You are **'", which would also match an
    undeclared persona line or one quoted inside a code fence. A utility
    skill (handoff, review-loop) has no such line and gets no toml — the
    absence of the line is the signal, not an oversight."""
    body = skill_body(sk_text, is_text=True).lstrip('\n')
    first = next((l for l in body.split('\n') if l.strip()), '')
    return bool(PERSONA_DECL_RE.match(first))


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


PROFILE_PATH_RE = re.compile(r'~/\.claude[\w.-]*/skills')


def check_all(root=ROOT):
    """Every violation the repo can currently detect, as (kind, detail) pairs,
    plus the counts each check examined. Read-only — writes nothing.

    Returns (violations, counts). `counts` is emitted alongside the verdict on
    purpose: `0 violations` says nothing without the denominator beside it, and
    a check whose denominator is zero because it looked in the wrong place
    reports exactly the same green as one that looked everywhere.

    Five checks:
      toml-drift        — a toml differs from render() of its own source. This
                          proves the tomls agree with their generator, not that
                          the generator is right — it catches hand-edits and
                          stale mirrors, which is the failure it exists for.
      citation-inlined  — an INDEPENDENT check of the same surface toml-drift
                          covers, deliberately not built on render(). toml-drift
                          regenerates via render() and diffs against render() —
                          an internally consistent oracle, not an independent
                          one: a render() bug that is wrong in the same
                          direction on both sides of that comparison (the toml
                          on disk and the fresh render() call) passes both,
                          silently. citation-inlined never calls render(). It
                          re-derives, straight from source, every file a
                          persona's body cites (the same _shared fragments and
                          references/*.md files render() inlines) and checks
                          that each one's raw current content is present
                          verbatim, as a plain substring, inside the toml file
                          as it sits on disk. A rendering bug that drops,
                          truncates, or swaps a cited file's content still
                          shows up here even when it fools toml-drift, because
                          this check's oracle is the cited source files
                          themselves, not render()'s own output.
      profile-path      — a `~/.claude*/skills` literal in any markdown under
                          skills/, which hardcodes one profile into a roster
                          meant to travel. The scan covers every `.md` in the
                          tree, not just SKILL.md and core.md: `references/`
                          files and `_shared/` fragments inline into consumer
                          tomls exactly like the bodies that cite them, so a
                          literal in one of them ships just as far. Scanning
                          the whole tree also means adding an inlinable file
                          cannot silently shrink this check's coverage.

                          Deliberately does not scan output-styles/*.md, even
                          though sync.sh deploys those files to both profiles
                          too. The failure mode this check guards against is a
                          literal riding silently into a generated toml or
                          shim via inlining — render() never reads
                          output-styles/ at all, so a path literal there
                          can't hitch that ride. sync.sh itself already names
                          both profile paths openly (SRC, the dst list), so
                          it isn't a roster meant to travel in the same sense
                          skills/ is. A portability guard for output-styles/
                          is a legitimate idea, but it's a different check
                          against a different failure mode, not a wider glob
                          on this one.
      orphan-toml       — a toml with no persona behind it
      prefixed-reference — a persona's own markdown citing its OWN
                          references/<name>.md via the repo-root-relative
                          form `skills/<same-persona>/references/<name>.md`
                          instead of the bare `references/<name>.md` form
                          `7bfc811` normalized every self-citation onto. The
                          two forms name the identical file for a
                          self-citation, and letting the long form keep
                          appearing there is exactly how bare and prefixed
                          self-citations coexisted unnoticed across eleven
                          review passes (AC-12/AC-18's prefix-stripping blind
                          spot, D20): nothing rejected the long form outright,
                          so it kept re-appearing beside the short one.

                          Scoped to SELF-citations only. REFERENCE_RE's
                          owner-prefix (`skills/<owner>/references/...`) is
                          the only way render() can express a citation of a
                          DIFFERENT persona's references/ directory — no
                          such citation exists today, but it is a deliberate,
                          supported mechanism, not the bug this check guards
                          against. Rejecting every prefixed form outright
                          would also outlaw that legitimate cross-persona
                          citation; this check only flags the case where the
                          named owner is the citing file's own persona.
    """
    v = []
    ps = personas(root)
    for p in ps:
        t = '%s/codex-agents/%s.toml' % (root, p)
        cur = open(t).read() if os.path.exists(t) else None
        if cur is None:
            v.append(('toml-drift', '%s.toml missing' % p))
        elif cur != render(p, root):
            v.append(('toml-drift', '%s.toml differs from its skills/ source' % p))

    for p in ps:
        t = '%s/codex-agents/%s.toml' % (root, p)
        if not os.path.exists(t):
            continue  # already reported above as toml-drift
        toml_text = open(t).read()
        sk = open('%s/skills/%s/SKILL.md' % (root, p)).read()
        body = skill_body(sk, is_text=True).strip('\n')
        if body not in toml_text:
            v.append(('citation-inlined', "%s.toml does not contain %s's own "
                      "current SKILL.md body verbatim" % (p, p)))
        for name in sorted(set(m for m in EXTRA_SHARED_RE.findall(body)
                                if m not in EXTRA_SHARED_SKIP)):
            frag = '%s/skills/_shared/%s.md' % (root, name)
            if not os.path.exists(frag):
                continue  # render() already errors loudly on this
            content = open(frag).read().strip('\n')
            if content not in toml_text:
                v.append(('citation-inlined', '%s.toml is missing the current '
                          'verbatim content of _shared/%s.md, which its body '
                          'cites' % (p, name)))
        for owner, name in sorted(set(REFERENCE_RE.findall(body))):
            owner = owner or p
            ref = '%s/skills/%s/references/%s.md' % (root, owner, name)
            if not os.path.exists(ref):
                continue  # render() already errors loudly on this
            content = open(ref).read().strip('\n')
            if content not in toml_text:
                v.append(('citation-inlined', '%s.toml is missing the current '
                          'verbatim content of references/%s.md, which its '
                          'body cites' % (p, name)))

    md = sorted(glob.glob(root + '/skills/**/*.md', recursive=True))
    for f in md:
        for i, line in enumerate(open(f), 1):
            m = PROFILE_PATH_RE.search(line)
            if m:
                v.append(('profile-path', '%s:%d hardcodes %s'
                          % (os.path.relpath(f, root), i, m.group(0))))

    for f in md:
        rel = os.path.relpath(f, root)
        parts = rel.split(os.sep)
        if len(parts) < 2 or parts[0] != 'skills' or parts[1] == '_shared':
            continue  # not owned by a single persona; no "self" to check
        owner = parts[1]
        for i, line in enumerate(open(f), 1):
            # REFERENCE_RE, not a private copy: this check's denominator has to
            # be exactly the set of citations render() resolves, or it grades a
            # different population than the one that ships. A second pattern
            # diverges in both directions the moment either is tightened —
            # missing self-citations render() does resolve, flagging nested
            # foreign paths it does not. group(1) is None for the bare form,
            # which never equals a persona name, so only the prefixed form can
            # match here.
            for pm in REFERENCE_RE.finditer(line):
                if pm.group(1) == owner:
                    v.append(('prefixed-reference', '%s:%d cites its own %s '
                              'via the repo-root-relative form instead of '
                              'the bare references/ form'
                              % (rel, i, pm.group(0))))

    tomls = sorted(glob.glob(root + '/codex-agents/*.toml'))
    valid = set(ps)
    for t in tomls:
        p = os.path.basename(t)[:-5]
        if p not in valid:
            v.append(('orphan-toml', '%s.toml has no persona in skills/' % p))

    return v, {'personas': len(ps), 'markdown files': len(md), 'tomls': len(tomls)}


def selftest(root=ROOT):
    """Positive control for each check: break one input, confirm that check
    goes red, restore, confirm green. Runs against a throwaway copy so the
    real tree is never mutated. Prints red/green for each and returns True
    only if every check both fired and cleared."""
    import shutil, tempfile
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        r = os.path.join(tmp, 'repo')
        shutil.copytree(root, r, ignore=shutil.ignore_patterns('.git', '__pycache__'))

        base, counts = check_all(r)
        if base:
            print('selftest: baseline copy is not clean (%d violations) — '
                  'fix the tree before trusting the controls' % len(base))
            for k, d in base:
                print('  %-13s %s' % (k, d))
            return False
        print('selftest: baseline green over %s'
              % ', '.join('%d %s' % (n, k) for k, n in counts.items()))

        plant = lambda s: s + "\nSee `~/.claude-work/skills/_shared/core.md`.\n"
        cases = [
            ('toml-drift', 'toml-drift',
             '%s/codex-agents/%s.toml' % (r, personas(r)[0]),
             lambda s: s + "\n# drift\n"),
            ('profile-path', 'profile-path/core',
             '%s/skills/_shared/core.md' % r, plant),
        ]
        # profile-path is only as wide as the file list check_all builds, and
        # that list is the thing that silently fell behind when the tree gained
        # reference files and fragments. Plant the literal in one file of every
        # kind the glob reaches — persona body, reference file, non-core
        # fragment — so a future narrowing of the glob shows up here as a NO
        # instead of as a green check over a surface it stopped reading. Each
        # label names the kind it actually plants in: a control whose name and
        # target disagree reports coverage of a class nobody is testing.
        bodies = sorted(glob.glob(r + '/skills/*/SKILL.md'))
        refs = sorted(glob.glob(r + '/skills/*/references/*.md'))
        frags = sorted(f for f in glob.glob(r + '/skills/_shared/*.md')
                       if os.path.basename(f) not in ('core.md',))
        for label, found in (('profile-path/skill', bodies),
                             ('profile-path/reference', refs),
                             ('profile-path/fragment', frags)):
            if found:
                cases.append(('profile-path', label, found[0], plant))
            else:
                ok = False
                print('selftest: %-22s NO FILE — nothing of this kind in the '
                      'tree to plant in' % label)

        # prefixed-reference: a persona's SKILL.md gains a self-citation
        # written in the repo-root-relative form instead of the bare form.
        # Cites a references/ file that actually exists (reusing `refs` from
        # the profile-path setup above) so render() — which check_all()'s
        # toml-drift arm also calls this same pass — resolves the citation
        # instead of raising on a made-up path; the point is to prove this
        # specific check fires, not to also exercise render()'s missing-file
        # error path. The persona keeps its frontmatter and body otherwise
        # intact — only a sentence is appended — so it stays on personas()
        # and this reaches the same check_all() pass every other citation is
        # read from, rather than the vacuous-fence trap (a broken '---'
        # fence drops the persona from personas() entirely and no check ever
        # sees it).
        if refs:
            pref_owner = os.path.basename(os.path.dirname(os.path.dirname(refs[0])))
            pref_name = os.path.basename(refs[0])[:-3]
            cases.append((
                'prefixed-reference', 'prefixed-reference/self',
                '%s/skills/%s/SKILL.md' % (r, pref_owner),
                lambda s, _o=pref_owner, _n=pref_name: s + (
                    '\nSee `skills/%s/references/%s.md`.\n' % (_o, _n))))
        else:
            ok = False
            print('selftest: %-22s NO FILE — nothing of this kind in the '
                  'tree to plant in' % 'prefixed-reference/self')

        for kind, label, path, mutate in cases:
            orig = open(path).read()
            open(path, 'w').write(mutate(orig))
            red = [x for x in check_all(r)[0] if x[0] == kind]
            open(path, 'w').write(orig)
            green = [x for x in check_all(r)[0] if x[0] == kind]
            fired, cleared = bool(red), not green
            ok &= fired and cleared
            print('selftest: %-22s red=%s green-after-restore=%s'
                  % (label, 'yes' if fired else 'NO', 'yes' if cleared else 'NO'))

        # citation-inlined: prove this check is independent of toml-drift's
        # oracle, not a second copy of it. Monkey-patch the module-level
        # render() to drop the tail of its own output (the last inlined
        # section), then write the toml using that SAME buggy render — so
        # toml-drift, which also calls render() to get its expectation, sees
        # the buggy toml match the buggy render exactly and stays green. That
        # is the AC-16/AC-18 trap named verbatim: a renderer bug that is
        # wrong in the same direction on both sides of toml-drift's
        # comparison. citation-inlined never calls render() — it reads the
        # cited source files and the toml's raw bytes directly — so it still
        # catches the same bug toml-drift missed.
        p = personas(r)[0]
        t = '%s/codex-agents/%s.toml' % (r, p)
        orig_toml = open(t).read()
        real_render = globals()['render']
        # Only p's own render is buggy — every other persona's render() must
        # stay correct, or their toml-drift would fire too and the control
        # would no longer isolate what it's testing.
        buggy_render = (lambda pp, rroot=r:
                         real_render(pp, rroot)[:-500] if pp == p
                         else real_render(pp, rroot))
        globals()['render'] = buggy_render
        try:
            open(t, 'w').write(buggy_render(p))
            violations = check_all(r)[0]
            drift_stayed_green = not [x for x in violations if x[0] == 'toml-drift']
            fired = bool([x for x in violations if x[0] == 'citation-inlined'])
        finally:
            globals()['render'] = real_render
            open(t, 'w').write(orig_toml)
        cleared = not [x for x in check_all(r)[0] if x[0] == 'citation-inlined']
        ok &= fired and cleared and drift_stayed_green
        print('selftest: %-22s red=%s green-after-restore=%s '
              '(toml-drift stayed green=%s, proving independence)'
              % ('citation-inlined', 'yes' if fired else 'NO',
                 'yes' if cleared else 'NO',
                 'yes' if drift_stayed_green else 'NO'))

        # orphan-toml: a toml whose skill dir is gone
        p = personas(r)[0]
        shutil.rmtree('%s/skills/%s' % (r, p))
        red = [x for x in check_all(r)[0] if x[0] == 'orphan-toml']
        ok &= bool(red)
        print('selftest: %-22s red=%s (skill dir removed; not restored — '
              'temp copy is discarded)' % ('orphan-toml', 'yes' if red else 'NO'))
    return ok


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == '--selftest':
        sys.exit(0 if selftest() else 1)
    if mode == '--check':
        violations, counts = check_all()
        print('%d violations over %s'
              % (len(violations), ', '.join('%d %s' % (n, k) for k, n in counts.items())))
        for kind, detail in violations:
            print('  %-13s %s' % (kind, detail), file=sys.stderr)
        sys.exit(1 if violations else 0)
    if mode:
        print('usage: render-agents.py [--check | --selftest]', file=sys.stderr)
        sys.exit(2)
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
