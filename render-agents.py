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
# it from § Session close's Close bullet, and only grading personas follow the
# pointer).
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
    s = path_or_text if is_text else open(path_or_text, encoding='utf-8').read()
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
    sk = open('%s/skills/%s/SKILL.md' % (root, p), encoding='utf-8').read()
    core = open('%s/skills/_shared/core.md' % root, encoding='utf-8').read()
    verif = open('%s/skills/_shared/verification.md' % root, encoding='utf-8').read()
    body = skill_body(sk, is_text=True).strip('\n')

    extra = ''
    for name in sorted(set(m for m in EXTRA_SHARED_RE.findall(body) if m not in EXTRA_SHARED_SKIP)):
        content = open('%s/skills/_shared/%s.md' % (root, name), encoding='utf-8').read()
        mark = '## %s reference (inlined for subagent self-containment)' % name
        extra += MARK_HR + mark + '\n\n' + content.strip('\n')

    for owner, name in sorted(set(REFERENCE_RE.findall(body))):
        owner = owner or p
        ref = '%s/skills/%s/references/%s.md' % (root, owner, name)
        if not os.path.exists(ref):
            raise ValueError('cites references/%s.md, which does not exist at '
                             'skills/%s/references/' % (name, owner))
        content = open(ref, encoding='utf-8').read()
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
        if has_persona_line(open(f, encoding='utf-8').read()):
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
        cur = open(t, encoding='utf-8').read() if os.path.exists(t) else None
        if new != cur:
            with open(t, 'w', encoding='utf-8') as fh:
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


# W2-T9: the `§`-resolver. No check before this one reads prose cross-
# references — all five checks verify *structure* (tomls match, paths
# exist, frontmatter parses, fragments inline) and are blind to whether a
# `§ X` citation actually resolves to content. That gap is what let a Wave 1
# defect ship: a definition deleted out from under a surviving `§` pointer,
# with every structural check green. This check closes the dangling-pointer
# half of that class.
#
# Scope, stated plainly rather than oversold: this catches a citation that
# fails to *resolve* — no heading or bold-label anywhere in its resolvable
# set starts with (or is a prefix of) the cited text. It does NOT catch a
# citation that resolves to a heading whose *content* was hollowed out from
# under it — that is the other half of the defect class, and it is not
# mechanically checkable the same way; a human read is what caught it.
#
# A `§ X` citation's resolvable target set is: the citing file's own
# `^#{1,4}` headings and bold list-item labels (`- **Label** —`, e.g.
# `_shared/review-angles.md`'s `§ External-system claims`, which is the
# repo's deliberate convention for citing a named angle that lives as a
# bullet, not a heading); its `references/` siblings' headings/labels if
# it's a persona SKILL.md; `_shared/core.md`'s headings/labels always (every
# persona reads core.md, so a bare `§ Session close` et al. must resolve
# regardless of which file cites it); and, per blank-line-delimited
# paragraph, the headings/labels of any `_shared/*.md` or `references/*.md`
# file explicitly named in that same paragraph — this is what lets a
# cross-file citation like `` `_shared/review-angles.md` § Finding anatomy ``
# resolve against review-angles.md rather than the citing file's own
# headings. An early pass that skipped this cross-file handling produced 59
# false positives on exactly this shape; all 59 were noise, not real
# citation breaks.
#
# Matching is a bidirectional word-boundary prefix check, not equality,
# because citation text and heading text disagree in both directions in
# real usage: `§ Phases 1–2` cites a heading titled
# `### Phases 1–2: Setup + context gathering` (citation shorter than
# heading), while `§ Enumeration owns that verification` over-captures past
# the heading `## Enumeration` because prose continues without a clean
# delimiter (citation longer than heading). Either direction resolves, so
# long as the boundary after the shorter string is a non-word character —
# a `§ Assessment` citing a real `Assessment frameworks` heading DOES
# resolve: the character actually tested at that boundary is the space
# separating the two words, not `frameworks` itself (D40). This direction
# is deliberately permissive with no floor — see `_resolves`'s docstring
# for why that permissiveness cannot be tightened without a diff to tell a
# coincidence apart from a real deletion, and `citation-orphaned` (W2-T18)
# for the check that covers the deletion case instead.
# A hard newline inside a paragraph is a soft wrap, not a sentence end —
# markdown reflows it — so it is deliberately NOT a terminator here; only
# the blank-line paragraph boundary (`_citation_paragraphs`, and this
# pattern's own `\Z` against a paragraph-scoped search string) stops a
# citation that runs to the end of its paragraph. An earlier version
# stopped at `\n`, which truncated every citation split across a wrapped
# line (e.g. `review-loop/SKILL.md`'s own wrapped prose) into a false
# unresolved fragment.
#
# The capture group is anchored `[A-Z]` — a `§ x...` citation starting
# lowercase is never extracted, so it is never graded, and an unresolvable
# lowercase citation would read identically to a resolving one. Deliberate,
# not an oversight: every heading and bold-label target this check resolves
# against starts capitalized (`HEADING_RE`/`BOLD_LABEL_RE` impose no such
# rule themselves, but the repo's own convention is Title Case), so a
# lowercase `§` mention in the tree today is prose referring back to an
# earlier citation rather than pointing at a new target — e.g. the `(§
# below)` idiom (twice, in the Standards- and Spec-axis bullets):
# stale-reference: "(§ below)" @ skills/eric/SKILL.md
# Widening the anchor to `[A-Za-z]`
# would start capturing that idiom as a citation needing its own resolvable
# target and require carving out an exception for it, for zero live
# lowercase citations that need resolving. `grep -rn '§[ \t]\+[a-z]'
# skills/` is the check for whether that trade has changed.
#
# `>` is also a stop delimiter, alongside `)`: the repo's own
# `<appended ...; see § X>` placeholder idiom —
# stale-reference: "see § Run close>" @ skills/sol/SKILL.md
# stale-reference: "see § Session close>" @ skills/_shared/core.md
# closes a citation the same way a parenthetical does, and without it the
# capture over-runs into the placeholder's own closing bracket (`Run
# close>` instead of `Run close`) — harmless for `citation-unresolved`,
# which resolves it anyway via the permissive citation-longer direction,
# but exactly the over-capture `citation-orphaned` (W2-T18) cannot forgive
# by design, since it only ever matches in the target-longer direction.
CITATION_RE = re.compile(
    r'§[ \t]+([A-Z][^)>]*?)(?=[)>]|,\s|\.\s|\.\Z|—|;\s|\s§|\+\s*§|\Z)')
HEADING_RE = re.compile(r'^#{1,4}[ \t]+(.+?)[ \t]*$', re.M)
BOLD_LABEL_RE = re.compile(r'^[ \t]*(?:[-*][ \t]+)?\*\*([^*\n]+)\*\*', re.M)
CITED_FILE_RE = re.compile(
    r'((?:skills/[\w-]+/)?(?:_shared|references)/[\w-]+\.md)')


def _norm_citation_text(s):
    return re.sub(r'\s+', ' ', s.strip(' `"\'.,;:)')).strip()


FENCE_RE = re.compile(r'^([ \t]*)(`{3,}|~{3,}).*?\n.*?^\1\2[ \t]*$\n?',
                       re.M | re.S)


def _strip_fences(text):
    """`text` with every fenced code block's interior blanked to newlines,
    opening fence to matching close (D41). A `#`-prefixed line or a
    `**bold**` label quoted verbatim inside a fence (a worked example, a
    template snippet) is not a real heading or label in the file it
    appears in — it donates a target no live citation was ever written
    against, so a heading deleted from prose can still "resolve" against
    its own quoted-then-removed copy inside a fence, or a fence full of
    invented headings can silently pad the resolvable set. Blanking to
    the same number of newlines (not deleting the block) keeps every
    surrounding line number stable for the callers that report `file:line`
    against this same text."""
    return FENCE_RE.sub(lambda m: '\n' * m.group(0).count('\n'), text)


def _citation_targets(text):
    """Every heading and bold list-item label in `text`, normalized — the
    resolvable-target vocabulary a `§` citation is checked against. Fenced
    code blocks are stripped first (D41) — a heading or label quoted
    inside a fence is not a live target in the file it appears in."""
    text = _strip_fences(text)
    out = set()
    for m in HEADING_RE.finditer(text):
        out.add(_norm_citation_text(m.group(1)))
    for m in BOLD_LABEL_RE.finditer(text):
        out.add(_norm_citation_text(m.group(1)))
    out.discard('')
    return out


def _citation_paragraphs(text):
    """(start, end) byte offsets of blank-line-delimited paragraphs — the
    unit a cross-file mention's scope is bounded to, so a file named in one
    paragraph doesn't silently license a citation three paragraphs away."""
    out, start = [], 0
    for m in re.finditer(r'\n[ \t]*\n', text):
        out.append((start, m.start()))
        start = m.end()
    out.append((start, len(text)))
    return out


def _resolves_exact(citation, targets):
    for t in targets:
        if not t:
            continue
        if citation == t:
            return True
        if t.startswith(citation) and (len(t) == len(citation)
                                        or not t[len(citation)].isalnum()):
            return True
        if citation.startswith(t) and (len(citation) == len(t)
                                        or not citation[len(t)].isalnum()):
            return True
    return False


def _resolves(citation, targets):
    """`_resolves_exact`, retried over right-truncated word-prefixes of
    `citation` when the full string doesn't resolve.

    `CITATION_RE` deliberately over-captures — it has no way to know where
    a heading name actually ends, so it runs until the next hard delimiter
    (`)`, a comma, a sentence end, `Z`), which is frequently past the real
    target when the citation is followed by unpunctuated prose. `§ Phase 1
    already does` and `§ Decompose chains (winston -> ... -> park at merge`
    are both live examples:
    stale-reference: "briar's § Phase 1 already does" @ skills/eric/SKILL.md
    stale-reference: "§ Decompose chains (winston" @ skills/sol/references/fleet-runs.md
    neither the raw capture nor its target is a prefix of the other, but
    dropping the trailing words one at a time reaches `Phase 1` and
    `Decompose`, both of which resolve cleanly. Truncating is safe in this
    direction only — a heading name is never split across an earlier stop
    point than the real one, since `_resolves_exact` already tries citation-
    is-prefix-of-target for the untruncated string first.

    No length floor on a truncated or single-word candidate (D34). A floor
    here was tried and failed: it can only compare string length against
    the tree it's calibrated on, and a coincidental short-word collision
    (`Run` matching an unrelated `Run report`) is not distinguishable *as a
    string* from a legitimate short citation (`Decompose`, `Budgets`) or
    from a citation whose real target was deleted by the change under
    review — the same three characters arise from all three causes. The
    real bound: prefix matching in the target-shorter direction cannot
    tell an over-captured citation apart from a citation naming a heading
    that no longer exists, at any length. `citation-orphaned` (W2-T18) is
    what actually covers the deletion case — it has diff information this
    function does not, and needs no threshold because of it."""
    words = citation.split(' ')
    for n in range(len(words), 0, -1):
        candidate = ' '.join(words[:n])
        if _resolves_exact(candidate, targets):
            return True
    return False


def _resolves_forward(citation, targets):
    """The one-directional half of `_resolves_exact`: true when `citation`
    equals a target, or a target starts with `citation` at a clean
    boundary — never the reverse (`citation` starting with a shorter
    target). `citation-orphaned` (W2-T18) uses this, not `_resolves_exact`,
    on purpose: the reverse direction is exactly what let a deleted
    `### Accessibility Review` heading escape detection while a surviving
    bold `**Accessibility**` label forgave the citation through
    `citation.startswith(target)` — 13 characters, so no floor on
    `_resolves` could ever have caught it. This direction is the only one
    a removed-heading check can safely use: a target *longer than or equal
    to* the citation is a plausible match a change could have deleted; a
    target *shorter than* the citation is not evidence of anything — a
    long citation isn't "for" a short substring just because it starts
    with it."""
    for t in targets:
        if not t:
            continue
        if citation == t:
            return True
        if t.startswith(citation) and (len(t) == len(citation)
                                        or not t[len(citation)].isalnum()):
            return True
    return False


def _iter_citation_sites(root=ROOT):
    """Every `§ X` citation under `skills/`, yielded as `(rel, line, cite,
    targets)` — `targets` is the resolvable set at that citation's
    paragraph, built exactly once here so `check_citations` (grades against
    it with `_resolves`) and `check_orphaned_citations` (grades against it
    with `_resolves_forward`) share one extraction pass instead of two that
    could quietly drift apart on what counts as "resolvable"."""
    md = sorted(glob.glob(root + '/skills/**/*.md', recursive=True))
    text_by_path = {f: open(f, encoding='utf-8').read() for f in md}
    targets_by_path = {f: _citation_targets(t) for f, t in text_by_path.items()}
    core_path = os.path.join(root, 'skills', '_shared', 'core.md')
    core_targets = targets_by_path.get(core_path, set())

    # Persona (and utility-skill) directory names. Read by name only: a
    # mention of "review-loop's § Admissibility…" or "briar's § Phase 1…"
    # cites a DIFFERENT persona's own SKILL.md heading directly, the
    # identical pattern `_shared/*.md` and `references/*.md` mentions cover
    # one directory over — verified live, so it is a real repo convention,
    # not a hypothetical:
    # stale-reference: "its § Admissibility on" @ skills/eric/SKILL.md
    # stale-reference: "review-loop's § Admissibility on the repair surface" @ skills/briar/SKILL.md
    persona_dirs = sorted(os.path.basename(os.path.dirname(f))
                           for f in glob.glob(root + '/skills/*/SKILL.md'))
    persona_name_re = {
        p: re.compile(r'(?<![\w-])' + re.escape(p) + r'(?![\w-])')
        for p in persona_dirs}

    for f in md:
        text = text_by_path[f]
        rel = os.path.relpath(f, root)
        parts = rel.split(os.sep)
        owner = parts[1] if len(parts) >= 2 and parts[0] == 'skills' else None

        default_targets = set(targets_by_path[f])
        if owner and owner != '_shared':
            pdir = os.path.join(root, 'skills', owner)
            for rf in sorted(glob.glob(os.path.join(pdir, 'references', '*.md'))):
                default_targets |= targets_by_path.get(
                    rf, _citation_targets(open(rf, encoding='utf-8').read()))
            # A references/ file's own citations resolve against its
            # OWNING persona's SKILL.md too, not just its reference
            # siblings — the relationship the loop above builds runs
            # SKILL.md -> references/*, and this is the reverse edge.
            if len(parts) >= 3 and parts[2] == 'references':
                owner_skill = os.path.join(pdir, 'SKILL.md')
                default_targets |= targets_by_path.get(
                    owner_skill,
                    _citation_targets(open(owner_skill, encoding='utf-8').read())
                    if os.path.exists(owner_skill) else set())
        if os.path.abspath(f) != os.path.abspath(core_path):
            default_targets |= core_targets

        for pstart, pend in _citation_paragraphs(text):
            para = text[pstart:pend]
            extra_targets = set()
            for m in CITED_FILE_RE.finditer(para):
                mentioned = m.group(1)
                candidates = [os.path.join(root, 'skills', mentioned),
                              os.path.join(root, mentioned)]
                if owner:
                    candidates.append(
                        os.path.join(root, 'skills', owner, mentioned))
                for c in candidates:
                    if os.path.exists(c):
                        extra_targets |= targets_by_path.get(
                            c, _citation_targets(open(c, encoding='utf-8').read()))
            for p in persona_dirs:
                if p == owner:
                    continue  # already in default_targets
                if persona_name_re[p].search(para):
                    other = os.path.join(root, 'skills', p, 'SKILL.md')
                    if os.path.exists(other):
                        extra_targets |= targets_by_path.get(
                            other,
                            _citation_targets(open(other, encoding='utf-8').read()))
            targets = default_targets | extra_targets

            for m in CITATION_RE.finditer(para):
                cite = _norm_citation_text(m.group(1))
                if not cite:
                    continue
                line = text.count('\n', 0, pstart + m.start()) + 1
                yield rel, line, cite, targets


def check_citations(root=ROOT):
    """Every `§ X` citation under `skills/` that fails to resolve against
    its resolvable target set, as `('citation-unresolved', 'citation-
    unresolved', detail)` triples — see the block comment above
    `CITATION_RE` for the resolution rules and this check's stated bound.
    The middle element is the arm id (ARMS, D46) — one arm here, so it
    always equals the kind, but it is still threaded explicitly: G1 reads
    the literal at this append site, not a rule about when arm equals
    kind."""
    v = []
    for rel, line, cite, targets in _iter_citation_sites(root):
        if not _resolves(cite, targets):
            v.append(('citation-unresolved', 'citation-unresolved',
                      '%s:%d § %s' % (rel, line, cite)))
    return v


def _citation_multi_match_stats(root=ROOT):
    """`(matched_multiple, total)` over every `§` citation under `skills/`
    (D35) — the population no single heading deletion can turn red, because
    more than one live target would still satisfy it. For each citation,
    count how many *individual* targets in its resolvable set independently
    satisfy `_resolves(cite, {t})`; the citation counts toward
    `matched_multiple` when two or more do. Informational only — never a
    violation, never a gate; printed beside `--check`'s counts so a change
    to `_resolves` shows up as a movement in this number rather than a
    silent re-baseline."""
    total = multi = 0
    for _rel, _line, cite, targets in _iter_citation_sites(root):
        total += 1
        hits = sum(1 for t in targets if t and _resolves(cite, {t}))
        if hits >= 2:
            multi += 1
    return multi, total


def removed_targets_from_git(root=ROOT):
    """Heading and bold-label text removed from `skills/` by the change
    under review, as a normalized set — the parameter `check_orphaned_
    citations` grades against (D34). Diffs `git merge-base HEAD main` (or,
    with no `main`, `origin/HEAD`) against `HEAD`: for every `skills/` path
    the two revisions disagree on, runs `_citation_targets` (D41's fence-
    stripping vocabulary function — the same one the survival side uses)
    against that path's content at the base revision, then drops any target
    whose normalized text still appears anywhere in the post-change tree's
    target vocabulary — a heading moved from one file to another, not
    deleted, is not orphaned. Sharing `_citation_targets` on both sides
    (D47) is deliberate: a diff is a line stream and a fence cannot be
    matched reliably across hunks, so the two sides used to disagree about
    what a target is (a heading deleted from inside a fenced example
    counted as a real removal) — re-deriving both sides through the same
    function makes that asymmetry impossible instead of something to keep
    in sync by hand.

    Returns `(removed_targets, skip_reason)`. `skip_reason` is `None` on a
    clean run; otherwise a short string naming why the diff couldn't be
    computed (no `.git`, no merge-base, or a failing `git` invocation) — the
    empty set on success and the empty set on failure must never look alike
    to a caller, so failure is always paired with a reason, never returned
    as a bare empty set standing in for "ran cleanly, found nothing."""
    import subprocess

    def run(args):
        return subprocess.run(['git'] + args, cwd=root,
                               capture_output=True, text=True, encoding='utf-8')

    # `os.path.isdir('.git')` is wrong for a worktree (`.git` is a regular
    # `gitdir: <path>` file there), a submodule, or `GIT_DIR` — every one of
    # those is the same mistake: inferring a git fact from the filesystem
    # instead of asking git (D45). Ask git instead; its exit code is the
    # actual fact this function needs.
    probe = run(['rev-parse', '--git-dir'])
    if probe.returncode != 0:
        return set(), 'not a git repo'

    mb = run(['merge-base', 'HEAD', 'main'])
    if mb.returncode != 0:
        mb = run(['merge-base', 'HEAD', 'origin/HEAD'])
    if mb.returncode != 0:
        return set(), 'no merge-base against main or origin/HEAD'
    base = mb.stdout.strip()

    names = run(['diff', '--name-only', base, 'HEAD', '--', 'skills/'])
    if names.returncode != 0:
        return set(), 'git diff failed: %s' % names.stderr.strip()[:200]

    # Both sides of the orphan diff run through `_citation_targets` (D47),
    # not a private raw-line scan here — that is what makes fence-stripping,
    # HEADING_RE, and BOLD_LABEL_RE identical on both sides by construction
    # instead of two implementations kept in sync by hand. A path that
    # doesn't exist at `base` (added by this change) contributes nothing:
    # `git show` fails for it and that failure is silently skipped, not
    # treated as a diff error — a file being new is not a diff failure.
    base_targets = set()
    for path in names.stdout.splitlines():
        if not path:
            continue
        shown = run(['show', '%s:%s' % (base, path)])
        if shown.returncode != 0:
            continue
        base_targets |= _citation_targets(shown.stdout)

    survives_somewhere = set()
    for f in glob.glob(os.path.join(root, 'skills', '**', '*.md'), recursive=True):
        survives_somewhere |= _citation_targets(open(f, encoding='utf-8').read())
    removed = base_targets - survives_somewhere
    return removed, None


def check_orphaned_citations(removed_targets, root=ROOT):
    """`('citation-orphaned', 'citation-orphaned', detail)` triples for every
    `§` citation naming a heading or bold label removed by the change under
    review (D34). The middle element is the ARMS (D46) arm id.
    `removed_targets` is a parameter, not derived internally — that is what
    lets `--selftest` grade this check's behaviour with no git plumbing,
    and what makes it diff-scoped rather than tree-wide: it has nothing to
    tune, because provenance (was this target removed by THIS change) is
    diff information `_resolves`'s tree-wide matching never had.

    Matching rule, exactly: flag citation `C` against removed target `T`
    when `C == T`, or when `T.startswith(C)` at a clean boundary — never
    the reverse. Then suppress the flag if `C` still resolves, in that same
    one-directional sense, against a target that survives at that
    citation's site — `_resolves_forward` both times, deliberately not the
    bidirectional `_resolves`: the bidirectional reverse direction
    (`C.startswith(T)`) is the exact one that let a deleted
    `### Accessibility Review` heading escape detection via a surviving
    `**Accessibility**` label, so reusing it here to decide suppression
    would silently reopen the same hole this check exists to close."""
    if not removed_targets:
        return []
    v = []
    for rel, line, cite, targets in _iter_citation_sites(root):
        for t in removed_targets:
            if not t:
                continue
            hit = (cite == t or (t.startswith(cite)
                   and (len(t) == len(cite) or not t[len(cite)].isalnum())))
            if not hit:
                continue
            # Suppression checks against every OTHER target at this site,
            # `t` itself excluded — otherwise a removed heading whose text
            # is still physically present in the tree (the shape a direct,
            # non-git call passes for testing, and a theoretical shape in
            # production if a target were ever re-derived stale) would
            # trivially "still resolve" against itself and suppress every
            # flag this check exists to raise.
            if _resolves_forward(cite, targets - {t}):
                break  # still resolves against a surviving target — suppress
            v.append(('citation-orphaned', 'citation-orphaned',
                      '%s:%d § %s — heading "%s" removed by this change'
                      % (rel, line, cite, t)))
            break
    return v


PROFILE_PATH_RE = re.compile(r'~/\.claude[\w.-]*/skills')

# W2-T40 (D49): a cross-reference in these renderers' own block comments
# used to be a persona name, a colon, and a line number — a pointer that
# rots silently the moment the named file is edited. Two such references
# went stale in the same commit that left a third, sibling reference in
# the same block updated, which is the tell that the mechanism holding it
# accurate was human diligence, not anything mechanical. A quoted phrase
# is self-verifying and greppable instead: every cross-reference in
# `render-agents.py` and `render-claude-agents.py` is now a marker of the
# shape `stale-reference:` a quoted phrase, `@`, a path, one per line so
# line-wrap can never split a phrase from its file, and
# `check_stale_references` asserts every phrase is still findable,
# verbatim, in the file it names.
STALE_REF_RE = re.compile(r'stale-reference:\s*"([^"]+)"\s*@\s*(\S+)')


ROLE_LINE_RE = re.compile(r'^-[ \t]+\*\*([^*]+)\*\*:[^\n]*?\(([^)]*)\)', re.M)


def _role_consumer_violations(root=ROOT):
    """`('stale-reference', 'role-consumer', detail)` for every persona
    `repo-map.template.md`'s `## Roles` section names beside the `ticket
    pattern` role (in that bullet's trailing parenthetical — `read by X,
    Y`) whose own `SKILL.md` never mentions that role by name (D50). A
    persona can be *named* as a consumer without *being* one — docs
    claiming a consumer that doesn't consume is the failure this closes:
    verified, `.repo-map.template.md` and `README.md` both named nora
    beside `ticket pattern` while `grep -ci 'ticket pattern'
    skills/nora/SKILL.md` returned 0.

    Scoped to the one role D50 actually found broken, not every role in
    the file: `architect docs`' own consumers describe it as "architecture
    docs"/"architecture context" rather than the bold label's exact
    wording, which is a real phrasing mismatch, not a persona that fails
    to consume the role — flagging it would be inventing a second finding
    nobody measured, the exact thing this run's brief warns against doing
    with the missing Spec minors. `ticket pattern` is the one D50 measured
    live."""
    tpl_path = os.path.join(root, 'repo-map.template.md')
    if not os.path.exists(tpl_path):
        return []
    tpl = open(tpl_path, encoding='utf-8').read()
    persona_dirs = sorted(os.path.basename(os.path.dirname(f))
                           for f in glob.glob(root + '/skills/*/SKILL.md'))
    v = []
    for role, consumers_text in ROLE_LINE_RE.findall(tpl):
        role = role.strip()
        if role.lower() != 'ticket pattern':
            continue
        for p in persona_dirs:
            if not re.search(r'(?<![\w-])' + re.escape(p.capitalize())
                              + r"(?![\w-])", consumers_text):
                continue
            sk_path = os.path.join(root, 'skills', p, 'SKILL.md')
            sk = open(sk_path, encoding='utf-8').read()
            if role.lower() not in sk.lower():
                v.append(('stale-reference', 'role-consumer',
                          'repo-map.template.md names %s as a consumer of '
                          'the %r role, but skills/%s/SKILL.md never '
                          'mentions it' % (p, role, p)))
    return v


def check_stale_references(root=ROOT):
    """`('stale-reference', <arm>, detail)` for two things: a `stale-
    reference: "<phrase>" @ <path>` marker (arm `stale-reference`) in
    `render-agents.py` or `render-claude-agents.py` whose phrase no longer
    appears verbatim in the file it names — a comment pointing at another
    file that stopped pointing at the right place after that file was
    edited; and (arm `role-consumer`, D50) a persona `repo-map.template.md`
    names beside a role whose own SKILL.md doesn't mention that role."""
    v = []
    for fn in ('render-agents.py', 'render-claude-agents.py'):
        src_path = os.path.join(root, fn)
        if not os.path.exists(src_path):
            continue
        src = open(src_path, encoding='utf-8').read()
        for phrase, rel_path in STALE_REF_RE.findall(src):
            target = os.path.join(root, rel_path)
            content = (open(target, encoding='utf-8').read()
                       if os.path.exists(target) else None)
            if content is None or phrase not in content:
                v.append(('stale-reference', 'stale-reference',
                          '%s cites "%s" @ %s, which no longer contains it '
                          'verbatim' % (fn, phrase, rel_path)))
    v.extend(_role_consumer_violations(root))
    return v


# ARMS / CONTROLS (D46). Five findings from the pass-3 sweep — skipped-is-
# loud calling the producer instead of grading through check_all;
# never-reverse passing vacuously; profile-path's four controls never
# varying the literal; citation-inlined's truncation reaching one arm of
# three; a narrowed citation denominator being invisible to every control —
# turned out to be one property, not five point fixes: a 220-line selftest()
# in which controls and arms were related only by whoever last read both.
#
# ARMS is one row per way a check can produce a result — one row per
# `v.append` site (arm id threaded as the middle element of every violation
# triple, see check_citations/check_orphaned_citations/check_all above),
# plus one row per producer skip reason (removed_targets_from_git's three
# `return set(), '<reason>'` sites). Not one row per check: toml-drift and
# citation-inlined each have more than one arm, and no control run against
# only one of them proves anything about the others.
#
# Fields: kind (the string a violation's first tuple element carries),
# arm (the id; unique, used as ARMS' key), reachable ('check_all' — this
# arm's violations flow through check_all's return — or 'direct', for the
# three skip reasons, which never become a violation and instead land in
# check_all's `notes`), variance (None, or the dimension G4 requires ≥2
# controls to span: 'payload' for a pattern-driven arm like profile-path,
# where a control that always plants the same literal can't tell a correct
# regex from one narrowed to that one string; 'corpus_kind' for a glob-
# driven arm like the citation checks, where a control that only ever
# plants into one kind of file can't tell a correct glob from one that
# silently stopped covering another kind), and bound (the text this arm's
# own known limits are printed as, when it has any beyond what its
# `variance` control already exercises — most arms have none).
ARMS = {
    'citation-unresolved': dict(
        kind='citation-unresolved', reachable='check_all',
        variance='corpus_kind',
        bound='tree-wide only; has no diff information, so a coincidental '
              'short-word collision cannot be told apart from a citation '
              'whose real target was deleted by the change under review'),
    'toml-drift/missing': dict(
        kind='toml-drift', reachable='check_all', variance=None, bound=''),
    'toml-drift/differs': dict(
        kind='toml-drift', reachable='check_all', variance=None, bound=''),
    'citation-inlined/body': dict(
        kind='citation-inlined', reachable='check_all', variance=None,
        bound=''),
    'citation-inlined/shared-fragment': dict(
        kind='citation-inlined', reachable='check_all', variance=None,
        bound=''),
    'citation-inlined/reference': dict(
        kind='citation-inlined', reachable='check_all', variance=None,
        bound=''),
    'profile-path': dict(
        kind='profile-path', reachable='check_all', variance='payload',
        bound=''),
    'prefixed-reference': dict(
        kind='prefixed-reference', reachable='check_all', variance=None,
        bound=''),
    'orphan-toml': dict(
        kind='orphan-toml', reachable='check_all', variance=None, bound=''),
    'citation-orphaned': dict(
        kind='citation-orphaned', reachable='check_all',
        variance=None,
        bound='diff-scoped to the change under review; does not cover '
              'pre-existing breakage, uncommitted deletions, or a citation '
              'suppressed by a surviving target (D48, printed in notes on '
              'every run)'),
    'skip/not-a-git-repo': dict(
        kind='skip', reachable='direct', variance=None, bound=''),
    'skip/no-merge-base': dict(
        kind='skip', reachable='direct', variance=None, bound=''),
    'skip/git-diff-failed': dict(
        kind='skip', reachable='direct', variance=None, bound=''),
    'stale-reference': dict(
        kind='stale-reference', reachable='check_all', variance=None,
        bound=''),
    'role-consumer': dict(
        kind='stale-reference', reachable='check_all', variance=None,
        bound=''),
}


def _g1_code_arms(root=ROOT):
    """AST-scans `render-agents.py` itself for every arm-id string literal
    reaching a `v.append(...)` call inside `check_all`, `check_citations`,
    and `check_orphaned_citations` — the three functions that build
    violation triples. Reads the code, not a hand-kept list: an arm added
    to a `v.append` call with no matching `ARMS` row is invisible to every
    other gate, so this is the one gate with no gate of its own above it.

    Bound, stated because it is real (D46): this only sees arm ids written
    as a string literal at the append site. An arm id computed at runtime —
    built from a variable, an f-string, string concatenation — escapes it.
    That is a constraint on how checks in this file are written, not a
    limitation to work around."""
    import ast
    src = open(os.path.join(root, 'render-agents.py'), encoding='utf-8').read()
    tree = ast.parse(src)
    target_fns = {'check_all', 'check_citations', 'check_orphaned_citations',
                  'check_stale_references', '_role_consumer_violations'}
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in target_fns:
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == 'append'
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == 'v'
                        and sub.args and isinstance(sub.args[0], ast.Tuple)
                        and len(sub.args[0].elts) >= 2
                        and isinstance(sub.args[0].elts[1], ast.Constant)
                        and isinstance(sub.args[0].elts[1].value, str)):
                    found.add(sub.args[0].elts[1].value)
    return found


def _g1_arms_closure(root=ROOT):
    """G1 (D46): code arms and `ARMS` rows must be exactly the same set —
    scoped to the `v.append`-reachable rows only (`kind != 'skip'`); the 3
    producer skip-reason rows are a different mechanism (a bare `return`,
    never a `v.append`) and are validated by G2's coverage requirement
    instead, not by this AST scan. Returns (ok, extra_in_code, extra_in_arms)
    — `extra_in_code` is an arm the code emits with no `ARMS` row (the
    new-arm-with-no-row case this gate exists to reject); `extra_in_arms` is
    a row nothing emits (a stale entry, or a typo in the row's own id)."""
    code = _g1_code_arms(root)
    declared = {a for a, row in ARMS.items() if row['kind'] != 'skip'}
    return (code == declared, sorted(code - declared), sorted(declared - code))


def check_all(root=ROOT):
    """Every violation the repo can currently detect, as (kind, detail) pairs,
    plus the counts each check examined, plus informational notes. Read-only
    — writes nothing. Internally, every violation carries a third element —
    an arm id (ARMS, D46) naming exactly which way of producing that kind of
    result fired — but the public return strips it back to (kind, detail),
    so no existing caller has to change.

    Returns (violations, counts, notes). `counts` is emitted alongside the
    verdict on purpose: `0 violations` says nothing without the denominator
    beside it, and a check whose denominator is zero because it looked in
    the wrong place reports exactly the same green as one that looked
    everywhere. `notes` carries lines that belong beside the verdict but are
    never a violation and never a gate — the citation-orphaned skip reason
    when git isn't available, and the ungradeable-population count (D35).

    Eight checks:
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
                          though sync.sh deploys those files to every
                          destination too. The failure mode this check guards
                          against is a literal riding silently into a
                          generated toml or shim via inlining — render()
                          never reads output-styles/ at all, so a path
                          literal there cannot hitch that ride. That is the
                          whole argument, and it stands on the inlining path
                          alone. A portability guard for output-styles/ is a
                          legitimate idea, but it's a different check against
                          a different failure mode, not a wider glob on this
                          one.
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
      citation-unresolved — a `§ X` prose citation that resolves against
                          neither its own file's headings/bold-labels, its
                          `references/` siblings', `_shared/core.md`'s, nor
                          those of any `_shared/*.md` or `references/*.md`
                          file named in the same paragraph. See the block
                          comment above `CITATION_RE` (W2-T9) for the
                          resolution rules and this check's stated bound —
                          it catches a citation that fails to resolve, not
                          one that resolves to a heading whose content was
                          hollowed out from under it.
      citation-orphaned  — a `§ X` citation naming a heading or bold label
                          removed by the change under review (W2-T18, D34).
                          Diff-scoped, not tree-wide: it grades only against
                          `removed_targets_from_git(root)`, so it has no
                          threshold to calibrate — provenance (was this
                          target removed by THIS change) is diff
                          information `citation-unresolved`'s tree-wide
                          matching never had. With no git repo, no
                          merge-base, or a failing `git` invocation, this
                          check contributes nothing to `violations` and the
                          reason is reported in `notes` instead — never a
                          silent green standing in for "didn't run."
      stale-reference    — a marker of the shape `stale-reference:` a quoted phrase, `@`, a path,
                          in `render-agents.py` or `render-claude-agents.py`
                          whose quoted phrase no longer appears verbatim in
                          the file it names (W2-T40, D49).
    """
    v = []
    v.extend(check_citations(root))
    v.extend(check_stale_references(root))
    ps = personas(root)
    for p in ps:
        t = '%s/codex-agents/%s.toml' % (root, p)
        cur = open(t, encoding='utf-8').read() if os.path.exists(t) else None
        if cur is None:
            v.append(('toml-drift', 'toml-drift/missing', '%s.toml missing' % p))
        elif cur != render(p, root):
            v.append(('toml-drift', 'toml-drift/differs',
                      '%s.toml differs from its skills/ source' % p))

    for p in ps:
        t = '%s/codex-agents/%s.toml' % (root, p)
        if not os.path.exists(t):
            continue  # already reported above as toml-drift
        toml_text = open(t, encoding='utf-8').read()
        sk = open('%s/skills/%s/SKILL.md' % (root, p), encoding='utf-8').read()
        body = skill_body(sk, is_text=True).strip('\n')
        if body not in toml_text:
            v.append(('citation-inlined', 'citation-inlined/body',
                      "%s.toml does not contain %s's own "
                      "current SKILL.md body verbatim" % (p, p)))
        for name in sorted(set(m for m in EXTRA_SHARED_RE.findall(body)
                                if m not in EXTRA_SHARED_SKIP)):
            frag = '%s/skills/_shared/%s.md' % (root, name)
            if not os.path.exists(frag):
                continue  # render() already errors loudly on this
            content = open(frag, encoding='utf-8').read().strip('\n')
            if content not in toml_text:
                v.append(('citation-inlined', 'citation-inlined/shared-fragment',
                          '%s.toml is missing the current '
                          'verbatim content of _shared/%s.md, which its body '
                          'cites' % (p, name)))
        for owner, name in sorted(set(REFERENCE_RE.findall(body))):
            owner = owner or p
            ref = '%s/skills/%s/references/%s.md' % (root, owner, name)
            if not os.path.exists(ref):
                continue  # render() already errors loudly on this
            content = open(ref, encoding='utf-8').read().strip('\n')
            if content not in toml_text:
                v.append(('citation-inlined', 'citation-inlined/reference',
                          '%s.toml is missing the current '
                          'verbatim content of references/%s.md, which its '
                          'body cites' % (p, name)))

    md = sorted(glob.glob(root + '/skills/**/*.md', recursive=True))
    for f in md:
        for i, line in enumerate(open(f, encoding='utf-8'), 1):
            m = PROFILE_PATH_RE.search(line)
            if m:
                v.append(('profile-path', 'profile-path', '%s:%d hardcodes %s'
                          % (os.path.relpath(f, root), i, m.group(0))))

    for f in md:
        rel = os.path.relpath(f, root)
        parts = rel.split(os.sep)
        if len(parts) < 2 or parts[0] != 'skills' or parts[1] == '_shared':
            continue  # not owned by a single persona; no "self" to check
        owner = parts[1]
        for i, line in enumerate(open(f, encoding='utf-8'), 1):
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
                    v.append(('prefixed-reference', 'prefixed-reference',
                              '%s:%d cites its own %s '
                              'via the repo-root-relative form instead of '
                              'the bare references/ form'
                              % (rel, i, pm.group(0))))

    tomls = sorted(glob.glob(root + '/codex-agents/*.toml'))
    valid = set(ps)
    for t in tomls:
        p = os.path.basename(t)[:-5]
        if p not in valid:
            v.append(('orphan-toml', 'orphan-toml',
                      '%s.toml has no persona in skills/' % p))

    notes = []
    removed_targets, skip_reason = removed_targets_from_git(root)
    if skip_reason:
        notes.append('citation-orphaned: skipped (%s)' % skip_reason)
    else:
        v.extend(check_orphaned_citations(removed_targets, root))
    # D48: the bound is printed where the verdict is printed, on every run —
    # not only on the skip path. Two of the five classes this check could
    # miss are now fixed behaviour (worktrees, D45; fence-donated removals,
    # D47) and are deliberately not listed here — a bound that no longer
    # applies is the same dishonesty one direction over. The three that
    # remain: pre-existing breakage (this check is diff-scoped to the
    # change under review, never the whole tree); uncommitted deletions
    # (the diff is merge-base..HEAD, so a heading deleted only in the
    # working tree, not yet committed, is invisible — documented nowhere
    # before this line); and a citation suppressed because it still
    # resolves against a surviving target.
    notes.append(
        'citation-orphaned: examined %d removed target%s; does not cover '
        'pre-existing breakage, uncommitted deletions, or a citation '
        'suppressed by a surviving target'
        % (len(removed_targets), '' if len(removed_targets) == 1 else 's'))
    multi, total = _citation_multi_match_stats(root)
    notes.append('%d of %d § citations match more than one target' % (multi, total))
    # The harvest and the surviving-target set are both globbed over
    # skills/**/*.md and nothing else — not codex-agents/*.toml, which this
    # note used to claim — so a `§` citation written into a toml, README.md
    # or a shell script resolves by hand and by nothing else. The branch that
    # added the first cross-file citation found the gap only by reading the
    # glob; stating
    # the corpus where the result is stated is the property AC-53 names, and
    # it is cheaper than widening a check nobody asked for. A note whose job
    # is naming what is unchecked overstates in the one direction that buys
    # false confidence, so its reach is read off the globs, never recalled.
    notes.append('citation corpus: skills/**/*.md only — § citations in '
                 'codex-agents/*.toml, README.md, shell scripts, or any '
                 'other file are unchecked')

    # v accumulated as (kind, arm, detail) triples (D46) so an arm id exists
    # at the site that emits it; the public return stays (kind, detail)
    # pairs, unchanged, so no existing caller has to change.
    violations = [(kind, detail) for kind, arm, detail in v]
    return violations, {'personas': len(ps), 'markdown files': len(md),
                         'tomls': len(tomls)}, notes


def _mutate_and_grade(r, kind, path, mutate):
    """Shared shape behind most CONTROLS rows (D46/W2-T38): mutate `path`,
    grade `kind` through `check_all(r)`, restore, grade again. Returns
    (fired, cleared) — both booleans, never combined here, because a
    `never-fires` row (G5) reads `fired` alone and a `fires` row reads
    both."""
    orig = open(path, encoding='utf-8').read()
    open(path, 'w', encoding='utf-8').write(mutate(orig))
    fired = bool([x for x in check_all(r)[0] if x[0] == kind])
    open(path, 'w', encoding='utf-8').write(orig)
    cleared = not [x for x in check_all(r)[0] if x[0] == kind]
    return fired, cleared


def _build_controls(r):
    """Runs every control against the throwaway copy `r` and returns the
    CONTROLS rows (D46/W2-T38) as a list of result dicts: `id`, `arm` (FK
    into ARMS), `label`, `via` ('check_all' | 'direct'), `payload`,
    `corpus_kind`, `expect` ('fires' | 'never-fires'), `twin` (an `id`,
    required when `expect == 'never-fires'`), and `ok`/`note` — the graded
    outcome.

    A module-level table of pre-built rows can't hold these: every row's
    grading needs the live throwaway copy `r`, created fresh per
    `--selftest` run. What is static is `ARMS` — each row here names a real
    `ARMS` key, and G2 checks that both directions hold. This function IS
    the table: one call, one entry per control, closed against `ARMS`
    exactly like a static table would be, just built against `r` instead of
    read off disk."""
    import shutil, subprocess
    tmp_parent = os.path.dirname(r)
    rows = []

    def add(id_, arm, label, via, ok, payload=None, corpus_kind=None,
             expect='fires', twin=None, note=None):
        rows.append(dict(id=id_, arm=arm, label=label, via=via, ok=ok,
                          payload=payload, corpus_kind=corpus_kind,
                          expect=expect, twin=twin, note=note))

    plant = lambda payload: (lambda s: s + '\nSee `%s/_shared/core.md`.\n' % payload)

    # toml-drift/differs, via check_all: a toml edited directly, out of
    # sync with render() of its own source.
    fired, cleared = _mutate_and_grade(
        r, 'toml-drift', '%s/codex-agents/%s.toml' % (r, personas(r)[0]),
        lambda s: s + '\n# drift\n')
    add('toml-drift', 'toml-drift/differs', 'toml-drift', 'check_all',
        fired and cleared)

    # profile-path, via check_all, payload AND corpus_kind variance (G4,
    # W2-T39): plant the literal in one file of every kind check_all's md
    # glob reaches — persona body, reference file, non-core fragment, and
    # core.md itself — so a future narrowing of that glob shows up as a
    # missing corpus_kind rather than a green check over a surface it
    # stopped reading. The payload also varies across rows now: all four
    # planting the identical `~/.claude-work/skills` literal let
    # `PROFILE_PATH_RE` be narrowed to exactly that string with every
    # control still green (D46's payload-variance finding) — three
    # distinct payloads here, each still matching the real regex.
    bodies = sorted(glob.glob(r + '/skills/*/SKILL.md'))
    refs = sorted(glob.glob(r + '/skills/*/references/*.md'))
    frags = sorted(f for f in glob.glob(r + '/skills/_shared/*.md')
                   if os.path.basename(f) not in ('core.md',))
    for id_, corpus_kind, found, payload in (
            ('profile-path/core', 'core', ['%s/skills/_shared/core.md' % r],
             '~/.claude/skills'),
            ('profile-path/skill', 'skill', bodies, '~/.claude-work/skills'),
            ('profile-path/reference', 'reference', refs,
             '~/.claude.bak/skills'),
            ('profile-path/fragment', 'fragment', frags,
             '~/.claude-work/skills')):
        if not found:
            add(id_, 'profile-path', id_, 'check_all', False,
                payload=payload, corpus_kind=corpus_kind,
                note='NO FILE — nothing of this kind in the tree to plant in')
            continue
        fired, cleared = _mutate_and_grade(r, 'profile-path', found[0],
                                            plant(payload))
        add(id_, 'profile-path', id_, 'check_all', fired and cleared,
            payload=payload, corpus_kind=corpus_kind)

    # prefixed-reference: a persona's SKILL.md gains a self-citation written
    # in the repo-root-relative form. Cites a references/ file that
    # actually exists (reusing `refs`) so render() — which toml-drift's
    # arm also calls — resolves the citation instead of raising, and stays
    # on personas() (a broken '---' fence would drop it from that set and
    # no check would ever see it).
    if refs:
        pref_owner = os.path.basename(os.path.dirname(os.path.dirname(refs[0])))
        pref_name = os.path.basename(refs[0])[:-3]
        fired, cleared = _mutate_and_grade(
            r, 'prefixed-reference', '%s/skills/%s/SKILL.md' % (r, pref_owner),
            lambda s, _o=pref_owner, _n=pref_name: s + (
                '\nSee `skills/%s/references/%s.md`.\n' % (_o, _n)))
        add('prefixed-reference/self', 'prefixed-reference',
            'prefixed-reference/self', 'check_all', fired and cleared)
    else:
        add('prefixed-reference/self', 'prefixed-reference',
            'prefixed-reference/self', 'check_all', False,
            note='NO FILE — nothing of this kind in the tree to plant in')

    # citation-inlined/reference, via check_all: prove this check is
    # independent of toml-drift's oracle, not a second copy of it.
    # Monkey-patch the module-level render() to drop the tail of its own
    # output, then write the toml using that SAME buggy render — toml-drift,
    # which also calls render() to get its expectation, sees the buggy toml
    # match the buggy render exactly and stays green. citation-inlined never
    # calls render(): it reads the cited source files and the toml's raw
    # bytes directly, so it still catches the bug toml-drift missed.
    #
    # This control's arm is 'reference', not 'body' — render() puts the
    # body first, so the `[:-500]` tail truncation only ever reaches the
    # LAST inlined section, which for personas()[0] (briar) is
    # references/smell-baseline.md. A control shaped like this cannot reach
    # 'body' or 'shared-fragment' no matter how it's tuned; W2-T39 adds
    # those as their own rows.
    p = personas(r)[0]
    t = '%s/codex-agents/%s.toml' % (r, p)
    orig_toml = open(t, encoding='utf-8').read()
    real_render = globals()['render']
    buggy_render = (lambda pp, rroot=r:
                     real_render(pp, rroot)[:-500] if pp == p
                     else real_render(pp, rroot))
    globals()['render'] = buggy_render
    try:
        open(t, 'w', encoding='utf-8').write(buggy_render(p))
        violations = check_all(r)[0]
        drift_stayed_green = not [x for x in violations if x[0] == 'toml-drift']
        fired = bool([x for x in violations if x[0] == 'citation-inlined'])
    finally:
        globals()['render'] = real_render
        open(t, 'w', encoding='utf-8').write(orig_toml)
    cleared = not [x for x in check_all(r)[0] if x[0] == 'citation-inlined']
    add('citation-inlined/reference', 'citation-inlined/reference',
        'citation-inlined/reference', 'check_all',
        fired and cleared and drift_stayed_green)

    # citation-unresolved/no-target, via check_all, corpus_kind variance:
    # plant a `§` citation whose target exists nowhere in the tree.
    # `Zzyzx9…` is deliberately not a prefix of any real heading or bold
    # label, so this proves the wholly-absent-target case only.
    core_path = '%s/skills/_shared/core.md' % r
    fired, cleared = _mutate_and_grade(
        r, 'citation-unresolved', core_path,
        lambda s: s + '\n\nSee § Zzyzx9Unresolvable Selftest Marker '
                       'Heading for details.\n')
    add('citation-unresolved/no-target', 'citation-unresolved',
        'citation-unresolved/no-target', 'check_all', fired and cleared,
        corpus_kind='core')

    # citation-unresolved/no-target-reference, corpus_kind='reference'
    # (G4, W2-T39): the same absent-target plant, but into a references/
    # file instead of core.md, so a future narrowing of
    # `_iter_citation_sites`'s glob to drop `references/` shows up as a
    # missing corpus_kind rather than a green check over a surface it
    # stopped reading.
    if refs:
        fired, cleared = _mutate_and_grade(
            r, 'citation-unresolved', refs[0],
            lambda s: s + '\n\nSee § Zzyzx9Unresolvable Selftest Marker '
                           'Heading for details.\n')
        add('citation-unresolved/no-target-reference', 'citation-unresolved',
            'citation-unresolved/no-target-reference', 'check_all',
            fired and cleared, corpus_kind='reference')
    else:
        add('citation-unresolved/no-target-reference', 'citation-unresolved',
            'citation-unresolved/no-target-reference', 'check_all', False,
            corpus_kind='reference',
            note='NO FILE — nothing of this kind in the tree to plant in')

    # citation-unresolved/fence-only, corpus_kind='shared-fragment' (G4,
    # W2-T39, and `_strip_fences`'s first control, D41): plant BOTH a
    # fenced `#`-heading and a `§` citation naming it, into the same
    # _shared/*.md fragment. A heading that exists only inside a fenced
    # code block donates no live target — this control fails if that
    # stops being true, i.e. if a citation naming a fence-quoted heading
    # started silently resolving.
    if frags:
        marker = 'Zzyzx8 Selftest Fence-Only Heading'

        def _fence_plant(s, _m=marker):
            return (s + '\n\n```markdown\n# %s\n```\n\n'
                    'See § %s for details.\n' % (_m, _m))
        fired, cleared = _mutate_and_grade(
            r, 'citation-unresolved', frags[0], _fence_plant)
        add('citation-unresolved/fence-only', 'citation-unresolved',
            'citation-unresolved/fence-only', 'check_all', fired and cleared,
            corpus_kind='shared-fragment')
    else:
        add('citation-unresolved/fence-only', 'citation-unresolved',
            'citation-unresolved/fence-only', 'check_all', False,
            corpus_kind='shared-fragment',
            note='NO FILE — nothing of this kind in the tree to plant in')

    # citation-orphaned. check_orphaned_citations() directly with a
    # removed-target set — no git, no commit, no diff plumbing, exactly
    # because the signature takes `removed_targets` as a parameter. `r` has
    # no `.git` (copytree excludes it), which the skipped-is-loud control
    # below leans on.
    hits = check_orphaned_citations({'Run close'}, r)
    fired_named = any(k == 'citation-orphaned' and 'Run close' in d
                       for k, a, d in hits)
    clean_empty = not check_orphaned_citations(set(), r)
    add('citation-orphaned/named', 'citation-orphaned',
        'citation-orphaned/named', 'direct', fired_named and clean_empty)

    hits = check_orphaned_citations(
        {'Phase 4: GitHub writes (one batch — all writes together'}, r)
    fired_abbrev = any(k == 'citation-orphaned' and 'eric' in d
                        and 'Phase 4' in d for k, a, d in hits)
    add('citation-orphaned/abbreviated', 'citation-orphaned',
        'citation-orphaned/abbreviated', 'direct', fired_abbrev)

    # citation-orphaned/never-reverse (G5, W2-T39): rebuilt on a synthetic
    # fixture, not the real tree. Against the real tree this passed
    # vacuously (AC-50) — `### Accessibility Review` is still a live
    # heading at briar's own SKILL.md, so the suppression path
    # (`_resolves_forward(cite, targets - {t})`) forgives the citation
    # whichever direction the hit test uses, and the control's fired/
    # not-fired outcome was identical under correct code and under the
    # reverse-direction mutant. This fixture has NO heading or bold label
    # anywhere resembling "Accessibility" — nothing left to suppress with —
    # so a citation `§ Accessibility Review` against removed target
    # `{'Accessibility'}` (13 chars, shorter) can only stay unflagged under
    # the correct one-directional hit test (`t.startswith(cite)`, false
    # here since `t` is shorter) and WOULD flag under the mutant that adds
    # `cite.startswith(t)`.
    nr_root = os.path.join(tmp_parent, 'scratch-never-reverse')
    os.makedirs(os.path.join(nr_root, 'skills', '_shared'), exist_ok=True)
    os.makedirs(os.path.join(nr_root, 'skills', 'testp'), exist_ok=True)
    open(os.path.join(nr_root, 'skills', '_shared', 'core.md'), 'w',
         encoding='utf-8').write('# Shared Core\n\n## Session close\n\n'
                                  'placeholder.\n')
    open(os.path.join(nr_root, 'skills', 'testp', 'SKILL.md'), 'w',
         encoding='utf-8').write(
        '---\nname: testp\ndescription: test\n---\n'
        'You are **Testp** (they/them), a test persona.\n\n'
        'See § Accessibility Review.\n')
    hits = check_orphaned_citations({'Accessibility'}, nr_root)
    never_reversed = not any(
        k == 'citation-orphaned' and 'Accessibility Review' in d
        for k, a, d in hits)
    add('citation-orphaned/never-reverse', 'citation-orphaned',
        'citation-orphaned/never-reverse', 'direct', never_reversed,
        expect='never-fires', twin='citation-orphaned/never-reverse-twin')

    # citation-orphaned/never-reverse-twin (G5): the SAME fixture, an
    # EXACT-match removed target (`cite == t`, no direction question at
    # all) — proves the fixture's citation is actually reachable and
    # gradable by this call path, not silently inert. Without this, the
    # never-fires control above would read "never-flagged=yes" even if the
    # fixture were broken and no citation were extracted from it at all.
    hits = check_orphaned_citations({'Accessibility Review'}, nr_root)
    twin_fired = any(k == 'citation-orphaned' and 'Accessibility Review' in d
                      for k, a, d in hits)
    add('citation-orphaned/never-reverse-twin', 'citation-orphaned',
        'citation-orphaned/never-reverse-twin', 'direct', twin_fired)

    removed, reason = removed_targets_from_git(r)
    skip_loud = reason is not None and removed == set()
    add('citation-orphaned/skipped-is-loud', 'skip/not-a-git-repo',
        'citation-orphaned/skipped-is-loud', 'direct', skip_loud,
        note='skip-reason=%r' % reason)

    # toml-drift/missing, via check_all (W2-T39): delete a toml outright
    # rather than editing it — the existing toml-drift control only ever
    # exercised the "differs" arm.
    ps = personas(r)
    p_missing = ps[1] if len(ps) > 1 else ps[0]
    toml_missing_path = '%s/codex-agents/%s.toml' % (r, p_missing)
    orig = open(toml_missing_path, encoding='utf-8').read()
    os.remove(toml_missing_path)
    fired = bool([x for x in check_all(r)[0] if x[0] == 'toml-drift'])
    open(toml_missing_path, 'w', encoding='utf-8').write(orig)
    cleared = not [x for x in check_all(r)[0] if x[0] == 'toml-drift']
    add('toml-drift/missing', 'toml-drift/missing', 'toml-drift/missing',
        'check_all', fired and cleared)

    # citation-inlined/body, via check_all (W2-T39): mutate the SOURCE
    # SKILL.md so its body content diverges from what the (unregenerated)
    # toml already contains — this is the arm the existing truncation
    # control cannot reach (see the note above the /reference control).
    p_body = ps[2] if len(ps) > 2 else ps[0]
    body_sk_path = '%s/skills/%s/SKILL.md' % (r, p_body)
    orig = open(body_sk_path, encoding='utf-8').read()
    open(body_sk_path, 'w', encoding='utf-8').write(
        orig + '\n\nSelftest body mutation marker.\n')
    fired = bool([x for x in check_all(r)[0] if x[0] == 'citation-inlined'])
    open(body_sk_path, 'w', encoding='utf-8').write(orig)
    cleared = not [x for x in check_all(r)[0] if x[0] == 'citation-inlined']
    add('citation-inlined/body', 'citation-inlined/body',
        'citation-inlined/body', 'check_all', fired and cleared)

    # citation-inlined/shared-fragment, via check_all (W2-T39): same idea,
    # for a _shared/*.md fragment some persona's body cites — find the
    # first (persona, fragment) pair via EXTRA_SHARED_RE, the same pattern
    # render() and check_all's own citation-inlined loop use.
    frag_name = None
    for pp in ps:
        pbody = skill_body(
            open('%s/skills/%s/SKILL.md' % (r, pp), encoding='utf-8').read(),
            is_text=True)
        matches = [m for m in EXTRA_SHARED_RE.findall(pbody)
                   if m not in EXTRA_SHARED_SKIP]
        if matches:
            frag_name = matches[0]
            break
    if frag_name:
        frag_path = '%s/skills/_shared/%s.md' % (r, frag_name)
        orig = open(frag_path, encoding='utf-8').read()
        open(frag_path, 'w', encoding='utf-8').write(
            orig + '\n\nSelftest fragment mutation marker.\n')
        fired = bool([x for x in check_all(r)[0] if x[0] == 'citation-inlined'])
        open(frag_path, 'w', encoding='utf-8').write(orig)
        cleared = not [x for x in check_all(r)[0] if x[0] == 'citation-inlined']
        add('citation-inlined/shared-fragment', 'citation-inlined/shared-fragment',
            'citation-inlined/shared-fragment', 'check_all', fired and cleared)
    else:
        add('citation-inlined/shared-fragment', 'citation-inlined/shared-fragment',
            'citation-inlined/shared-fragment', 'check_all', False,
            note='NO FILE — no persona body cites a non-core _shared fragment')

    # citation-orphaned via check_all (W2-T39): the control G3 demands, and
    # the one whose absence let the shipping path (check_all's own
    # `v.extend(check_orphaned_citations(...))` line) be deleted with every
    # control still green (D46's mutation proof). A real scratch git repo —
    # `r` deliberately has no `.git` (see skipped-is-loud above), so this
    # needs its own copy: init, commit the current tree as base on `main`,
    # then commit a real heading deletion, and grade THROUGH `check_all`,
    # not a direct call to `check_orphaned_citations`.
    co_root = os.path.join(tmp_parent, 'scratch-citation-orphaned')
    shutil.copytree(r, co_root, ignore=shutil.ignore_patterns('__pycache__'))

    def _git(args, cwd=co_root):
        return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                               text=True, encoding='utf-8')
    _git(['init', '-q', '-b', 'main'])
    _git(['config', 'user.email', 'selftest@example.com'])
    _git(['config', 'user.name', 'selftest'])
    _git(['add', '-A'])
    _git(['commit', '-q', '-m', 'base'])
    # `main` has to stay AT the base commit while HEAD moves ahead — a
    # branch checked out and committed directly on `main` makes
    # `merge-base HEAD main` resolve to HEAD itself (they're the same
    # commit), so the diff is empty and nothing is ever "removed". A
    # feature branch mirrors what a real PR looks like.
    _git(['checkout', '-q', '-b', 'work'])
    briar_path = os.path.join(co_root, 'skills', 'briar', 'SKILL.md')
    content = open(briar_path, encoding='utf-8').read()
    mutated = content.replace('### Accessibility Review\n', '', 1)
    co_ok_setup = mutated != content
    open(briar_path, 'w', encoding='utf-8').write(mutated)
    _git(['add', '-A'])
    _git(['commit', '-q', '-m', 'delete a heading'])
    co_violations = check_all(co_root)[0]
    co_fired = co_ok_setup and any(k == 'citation-orphaned'
                                    for k, d in co_violations)
    add('citation-orphaned/via-check_all', 'citation-orphaned',
        'citation-orphaned/via-check_all', 'check_all', co_fired)

    # skip/no-merge-base (W2-T39): a git repo with no `main` branch and no
    # `origin/HEAD` — `removed_targets_from_git` must return that skip
    # reason, and nothing else.
    nomb_root = os.path.join(tmp_parent, 'scratch-no-merge-base')
    os.makedirs(nomb_root, exist_ok=True)

    def _git_nomb(args, cwd=nomb_root):
        return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                               text=True, encoding='utf-8')
    _git_nomb(['init', '-q', '-b', 'trunk'])
    _git_nomb(['config', 'user.email', 'selftest@example.com'])
    _git_nomb(['config', 'user.name', 'selftest'])
    open(os.path.join(nomb_root, 'README.md'), 'w', encoding='utf-8').write('x')
    _git_nomb(['add', '-A'])
    _git_nomb(['commit', '-q', '-m', 'x'])
    nomb_removed, nomb_reason = removed_targets_from_git(nomb_root)
    add('skip/no-merge-base', 'skip/no-merge-base', 'skip/no-merge-base',
        'direct',
        nomb_reason == 'no merge-base against main or origin/HEAD'
        and nomb_removed == set(),
        note='skip-reason=%r' % nomb_reason)

    # skip/git-diff-failed (W2-T39): a valid merge-base, then the `git
    # diff --name-only` call itself fails. Monkey-patches the process-wide
    # `subprocess.run` for the duration of one call, restored in `finally`
    # — the same monkey-patch shape citation-inlined/reference already uses
    # on `render()` above, applied one layer down. Runs against the actual
    # running checkout (`ROOT`), which has a real `main` to find a merge-
    # base against; the call is read-only.
    real_sp_run = subprocess.run

    def _fake_run(args, *a, **kw):
        if len(args) >= 2 and args[0] == 'git' and args[1] == 'diff':
            class _R:
                returncode = 1
                stdout = ''
                stderr = 'selftest-forced diff failure'
            return _R()
        return real_sp_run(args, *a, **kw)
    subprocess.run = _fake_run
    try:
        gdf_removed, gdf_reason = removed_targets_from_git(ROOT)
    finally:
        subprocess.run = real_sp_run
    add('skip/git-diff-failed', 'skip/git-diff-failed', 'skip/git-diff-failed',
        'direct',
        bool(gdf_reason) and gdf_reason.startswith('git diff failed')
        and gdf_removed == set(),
        note='skip-reason=%r' % gdf_reason)

    # stale-reference, via check_all (W2-T40): corrupt one character of a
    # live `stale-reference:` marker's quoted phrase in the copy's own
    # `render-agents.py`, so it no longer appears verbatim in the file it
    # names.
    ra_path = '%s/render-agents.py' % r
    orig = open(ra_path, encoding='utf-8').read()
    mutated = orig.replace('"(§ below)"', '"(§ nowhere)"', 1)
    sr_ok_setup = mutated != orig
    open(ra_path, 'w', encoding='utf-8').write(mutated)
    fired = bool([x for x in check_all(r)[0] if x[0] == 'stale-reference'])
    open(ra_path, 'w', encoding='utf-8').write(orig)
    cleared = not [x for x in check_all(r)[0] if x[0] == 'stale-reference']
    add('stale-reference/renderer', 'stale-reference', 'stale-reference/renderer',
        'check_all', sr_ok_setup and fired and cleared)

    # role-consumer, via check_all (W2-T41, D50): strip the mention of the
    # `ticket pattern` role out of nora's own copy so repo-map.template.md
    # still names her as a consumer but her SKILL.md no longer says so.
    nora_path = '%s/skills/nora/SKILL.md' % r
    orig = open(nora_path, encoding='utf-8').read()
    mutated = re.sub(r'(?i)ticket pattern', 'ticket shape', orig)
    rc_ok_setup = mutated != orig
    open(nora_path, 'w', encoding='utf-8').write(mutated)
    fired = any(k == 'stale-reference' and 'nora' in d and 'ticket pattern' in d
                for k, d in check_all(r)[0])
    open(nora_path, 'w', encoding='utf-8').write(orig)
    cleared = not any(k == 'stale-reference' and 'nora' in d
                       and 'ticket pattern' in d for k, d in check_all(r)[0])
    add('role-consumer/nora', 'role-consumer', 'role-consumer/nora',
        'check_all', rc_ok_setup and fired and cleared)

    # orphan-toml: a toml whose skill dir is gone. No restore — the temp
    # copy is discarded, and this control runs last for exactly that reason.
    shutil.rmtree('%s/skills/%s' % (r, p))
    red = bool([x for x in check_all(r)[0] if x[0] == 'orphan-toml'])
    add('orphan-toml', 'orphan-toml', 'orphan-toml', 'check_all', red,
        note='skill dir removed; not restored — temp copy is discarded')

    return rows


def _g2_coverage(rows):
    """G2 (D46): every `ARMS` row has >=1 `CONTROLS` row grading it through
    the path its `reachable` field promises — a `check_all`-reachable arm
    needs a `via='check_all'` control (a `direct` control is admissible in
    addition, never instead, per G3's own separate statement of this — see
    that gate's docstring for why the two overlap on purpose); a `direct`
    (skip-reason) arm needs any control at all. And every control names a
    real arm. This is the gate that makes "an arm with no control" a line
    in the output instead of something a reviewer has to notice."""
    missing = []
    for arm, row in sorted(ARMS.items()):
        matches = [c for c in rows if c['arm'] == arm]
        if row['reachable'] == 'check_all':
            covered = any(c['via'] == 'check_all' for c in matches)
            # Print "<arm> via check_all" (not the bare arm) when direct
            # controls already exist for it — that is the shape D46's
            # citation-orphaned finding actually is: 4 direct controls, 0
            # exercising the check_all integration path the mutation proof
            # walks through.
            label = ('%s via check_all' % arm) if matches else arm
        else:
            covered = bool(matches)
            label = arm
        if not covered:
            missing.append(label)
    unknown = sorted(c['id'] for c in rows if c['arm'] not in ARMS)
    return (not missing and not unknown), missing, unknown


def _g3_integration(rows):
    """G3 (D46): every arm reachable through `check_all` has >=1 control
    with `via='check_all'`. Deliberately the same predicate G2 already
    applies to `check_all`-reachable arms — this is the gate D46 names for
    "the integration path" specifically, and the mutation AC-48 walks
    (deleting the line that runs a check inside `check_all`) is what a
    `via='check_all'` control catches and a `via='direct'` control cannot:
    a direct call to `check_orphaned_citations` never executes the line in
    `check_all` that wires it in."""
    missing = [arm for arm, row in sorted(ARMS.items())
               if row['reachable'] == 'check_all'
               and not any(c['arm'] == arm and c['via'] == 'check_all'
                           for c in rows)]
    return (not missing), missing


def _g4_variance(rows):
    """G4 (D46): an arm declaring a `variance` dimension needs >=2 controls
    spanning distinct values of it — `payload` for a pattern-driven arm
    (profile-path's regex: four controls planting the identical literal
    can't tell a correct regex from one narrowed to that one string),
    `corpus_kind` for a glob-driven arm (the citation checks: a control
    that only ever plants into one kind of file can't tell a correct glob
    from one that silently stopped covering another kind)."""
    failing = []
    for arm, row in sorted(ARMS.items()):
        dim = row['variance']
        if not dim:
            continue
        vals = {c[dim] for c in rows if c['arm'] == arm and c.get(dim)}
        if len(vals) < 2:
            failing.append(arm)
    return (not failing), failing


def _g5_twins(rows):
    """G5 (D46): a control asserting something is *not* flagged
    (`expect='never-fires'`) proves nothing about a fixture that never
    reached the check in the first place — it needs a named `twin` control
    on the same fixture whose `expect='fires'`, and both have to actually
    have run. Every row in `rows` already ran (`_build_controls` executes
    every control unconditionally), so this checks only that the twin
    relationship is declared and resolves."""
    by_id = {c['id']: c for c in rows}
    broken = []
    for c in rows:
        if c['expect'] != 'never-fires':
            continue
        twin = by_id.get(c['twin']) if c['twin'] else None
        if not twin or twin['expect'] != 'fires':
            broken.append(c['id'])
    return (not broken), broken


def selftest(root=ROOT):
    """Positive control for each check: break one input, confirm that check
    goes red, restore, confirm green. Runs against a throwaway copy so the
    real tree is never mutated. Prints red/green for each and returns True
    only if every check both fired and cleared, and G1 through G5 (D46) all
    hold."""
    import shutil, tempfile
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        r = os.path.join(tmp, 'repo')
        shutil.copytree(root, r, ignore=shutil.ignore_patterns('.git', '__pycache__'))

        # G1 reads the module's source text via AST, not check_all's
        # behaviour, so it runs — and can fail — before the baseline-clean
        # check below: an unregistered arm reaching v.append is exactly the
        # shape of bug that also makes the baseline copy dirty (the arm
        # fires unconditionally), and G1's own verdict must still print in
        # that case rather than being swallowed by the early return.
        g1_ok, g1_extra_code, g1_extra_arms = _g1_arms_closure(r)
        ok &= g1_ok
        print('selftest: G1/arms-closure     %s%s'
              % ('ok' if g1_ok else 'NO',
                 '' if g1_ok else ' (unregistered in code: %s; unmatched in '
                 'ARMS: %s)' % (g1_extra_code, g1_extra_arms)))

        base, counts, base_notes = check_all(r)
        if base:
            print('selftest: baseline copy is not clean (%d violations) — '
                  'fix the tree before trusting the controls' % len(base))
            for k, d in base:
                print('  %-13s %s' % (k, d))
            return False
        print('selftest: baseline green over %s'
              % ', '.join('%d %s' % (n, k) for k, n in counts.items()))

        rows = _build_controls(r)
        for c in rows:
            ok &= c['ok']
            print('selftest: %-32s %s%s'
                  % (c['label'], 'ok' if c['ok'] else 'NO',
                     '' if not c['note'] else ' (%s)' % c['note']))
        print('selftest: %d controls run' % len(rows))

        g2_ok, g2_missing, g2_unknown = _g2_coverage(rows)
        ok &= g2_ok
        print('selftest: G2/arms-covered     %s%s'
              % ('ok' if g2_ok else 'NO',
                 '' if g2_ok else ' (uncovered arms: %s%s)'
                 % (g2_missing, '; unknown arm in control: %s' % g2_unknown
                    if g2_unknown else '')))

        g3_ok, g3_missing = _g3_integration(rows)
        ok &= g3_ok
        print('selftest: G3/integration-path %s%s'
              % ('ok' if g3_ok else 'NO',
                 '' if g3_ok else ' (no via=check_all control: %s)' % g3_missing))

        g4_ok, g4_missing = _g4_variance(rows)
        ok &= g4_ok
        print('selftest: G4/variance         %s%s'
              % ('ok' if g4_ok else 'NO',
                 '' if g4_ok else ' (needs >=2 distinct values: %s)' % g4_missing))

        g5_ok, g5_broken = _g5_twins(rows)
        ok &= g5_ok
        print('selftest: G5/never-fires-twin %s%s'
              % ('ok' if g5_ok else 'NO',
                 '' if g5_ok else ' (no live twin: %s)' % g5_broken))

    return ok


if __name__ == '__main__':
    # W2-T36 (D45's sibling fix, same subprocess.run call): the tree is full
    # of em dashes and § marks, and stdout/stderr fall back to the process's
    # locale encoding, not UTF-8, when that locale is ASCII (a bare `LC_ALL=C`
    # environment, common in CI and minimal shells). Reconfigure both streams
    # to UTF-8 at entry rather than hunting non-ASCII characters out of every
    # print — that policy is unenforceable in a tree this full of them.
    # `reconfigure` was added in 3.7; the guard is for an interpreter old
    # enough, or a stream type, that lacks it, not for a normal failure mode.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            _stream.reconfigure(encoding='utf-8')

    # Branch on argument COUNT, not truthiness of the argument (D42): the
    # regenerate arm below must only be reachable with zero arguments.
    # `mode = sys.argv[1] if len(sys.argv) > 1 else ''` used to fall through
    # to the regenerate arm on `python3 render-agents.py ""`, because an
    # empty-string mode is falsy exactly like "no argument" — verified on a
    # throwaway copy, that command used to reach the write arm at exit 0.
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == '--selftest':
            sys.exit(0 if selftest() else 1)
        if mode == '--check':
            violations, counts, notes = check_all()
            print('%d violations over %s'
                  % (len(violations),
                     ', '.join('%d %s' % (n, k) for k, n in counts.items())))
            for note in notes:
                print(note)
            for kind, detail in violations:
                print('  %-13s %s' % (kind, detail), file=sys.stderr)
            sys.exit(1 if violations else 0)
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
