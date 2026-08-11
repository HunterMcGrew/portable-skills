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
# a `§ Assessment` citing a real `§ Assessment frameworks` heading would NOT
# resolve, because `frameworks` is still a word character at that boundary.
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
# below)` idiom (`eric:130`, `eric:131`). Widening the anchor to `[A-Za-z]`
# would start capturing that idiom as a citation needing its own resolvable
# target and require carving out an exception for it, for zero live
# lowercase citations that need resolving. `grep -rn '§[ \t]\+[a-z]'
# skills/` is the check for whether that trade has changed.
CITATION_RE = re.compile(
    r'§[ \t]+([A-Z][^)]*?)(?=[)]|,\s|\.\s|\.\Z|—|;\s|\s§|\+\s*§|\Z)')
HEADING_RE = re.compile(r'^#{1,4}[ \t]+(.+?)[ \t]*$', re.M)
BOLD_LABEL_RE = re.compile(r'^[ \t]*(?:[-*][ \t]+)?\*\*([^*\n]+)\*\*', re.M)
CITED_FILE_RE = re.compile(
    r'((?:skills/[\w-]+/)?(?:_shared|references)/[\w-]+\.md)')


def _norm_citation_text(s):
    return re.sub(r'\s+', ' ', s.strip(' `"\'.,;:)')).strip()


def _citation_targets(text):
    """Every heading and bold list-item label in `text`, normalized — the
    resolvable-target vocabulary a `§` citation is checked against."""
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


# Floor for a single retained word after truncation (or for an
# already-one-word citation) in `_resolves`. Calibrated against briar's
# Wave-2-review Major, not chosen in the abstract: deleting a heading and
# re-running `--check` stayed green because the truncation retry forgave
# the deletion against an unrelated sibling sharing only its FIRST word —
# `Run close` -> `Run` (3 chars) matching `Run report`; `PR Label` -> `PR`
# (2) matching `PR Readiness`; `AC Verification Mode` -> `AC` (2) matching
# `AC conformance`; `How Tess Thinks` -> `How` (3) matching `How Briar
# Thinks`; `Mode selection` -> `Mode` (4) matching the bold label `Mode
# gate`. Every one of those collisions is a short, common English word or
# acronym — exactly the shape that turns up as an unrelated heading's first
# word by coincidence. Contrast the two live citations that legitimately
# need this same truncation retry to resolve at all: `Phase 1 already does`
# -> `Phase 1` (`eric:97`, two words, unaffected by a single-word floor) and
# `Decompose chains (winston -> ... -> park at merge` -> `Decompose`
# (`sol/references/fleet-runs.md:5`, one word, 9 characters). 5 is the
# threshold that rejects every collision above while keeping both live
# single/short matches (`Decompose` at 9 chars, and `references/fleet-
# runs.md:10`'s `Budgets` at 7 chars) — verified against the full live
# citation population, not just these examples (see `_resolves`'s
# docstring).
MIN_SINGLE_WORD_MATCH_LEN = 5


def _resolves(citation, targets):
    """`_resolves_exact`, retried over right-truncated word-prefixes of
    `citation` when the full string doesn't resolve.

    `CITATION_RE` deliberately over-captures — it has no way to know where
    a heading name actually ends, so it runs until the next hard delimiter
    (`)`, a comma, a sentence end, `Z`), which is frequently past the real
    target when the citation is followed by unpunctuated prose. `§ Phase 1
    already does` and `§ Decompose chains (winston -> ... -> park at merge`
    are both live examples (`eric:97`, `sol/references/fleet-runs.md:5`):
    neither the raw capture nor its target is a prefix of the other, but
    dropping the trailing words one at a time reaches `Phase 1` and
    `Decompose`, both of which resolve cleanly. Truncating is safe in this
    direction only — a heading name is never split across an earlier stop
    point than the real one, since `_resolves_exact` already tries citation-
    is-prefix-of-target for the untruncated string first.

    A candidate of exactly one word is rejected below
    `MIN_SINGLE_WORD_MATCH_LEN` characters, truncated or not. Without this
    floor, a genuinely deleted heading resolves silently against any
    surviving sibling that happens to start with the same short leading
    word — the retry has no way to tell a real single-word heading name
    (`Decompose`) apart from a common word a deleted multi-word heading
    used to start with (`Run`, from a deleted `Run close` matching a
    surviving `Run report`). See `MIN_SINGLE_WORD_MATCH_LEN` above for the
    calibration evidence. Multi-word candidates carry no such floor — two
    or more words in agreement is specific enough on its own; the failure
    mode this guards against is single-word-only."""
    words = citation.split(' ')
    for n in range(len(words), 0, -1):
        candidate = ' '.join(words[:n])
        if n == 1 and len(candidate) < MIN_SINGLE_WORD_MATCH_LEN:
            continue
        if _resolves_exact(candidate, targets):
            return True
    return False


def check_citations(root=ROOT):
    """Every `§ X` citation under `skills/` that fails to resolve against
    its resolvable target set, as `('citation-unresolved', detail)` pairs —
    see the block comment above `CITATION_RE` for the resolution rules and
    this check's stated bound."""
    v = []
    md = sorted(glob.glob(root + '/skills/**/*.md', recursive=True))
    text_by_path = {f: open(f).read() for f in md}
    targets_by_path = {f: _citation_targets(t) for f, t in text_by_path.items()}
    core_path = os.path.join(root, 'skills', '_shared', 'core.md')
    core_targets = targets_by_path.get(core_path, set())

    # Persona (and utility-skill) directory names, longest first so a
    # search never matches "eric" inside a longer name before trying the
    # longer one — the roster has no such collision today, but the check
    # shouldn't depend on that staying true. Read by name only: a mention
    # of "review-loop's § Admissibility…" or "briar's § Phase 1…" cites a
    # DIFFERENT persona's own SKILL.md heading directly, the identical
    # pattern `_shared/*.md` and `references/*.md` mentions cover one
    # directory over — verified live at `eric:97` and `eric:303`/
    # `briar:133`, so it is a real repo convention, not a hypothetical.
    persona_dirs = sorted(
        (os.path.basename(os.path.dirname(f))
         for f in glob.glob(root + '/skills/*/SKILL.md')),
        key=len, reverse=True)
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
                    rf, _citation_targets(open(rf).read()))
            # A references/ file's own citations resolve against its
            # OWNING persona's SKILL.md too, not just its reference
            # siblings — the relationship the loop above builds runs
            # SKILL.md -> references/*, and this is the reverse edge.
            if len(parts) >= 3 and parts[2] == 'references':
                owner_skill = os.path.join(pdir, 'SKILL.md')
                default_targets |= targets_by_path.get(
                    owner_skill, _citation_targets(open(owner_skill).read())
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
                            c, _citation_targets(open(c).read()))
            for p in persona_dirs:
                if p == owner:
                    continue  # already in default_targets
                if persona_name_re[p].search(para):
                    other = os.path.join(root, 'skills', p, 'SKILL.md')
                    if os.path.exists(other):
                        extra_targets |= targets_by_path.get(
                            other, _citation_targets(open(other).read()))
            targets = default_targets | extra_targets

            for m in CITATION_RE.finditer(para):
                cite = _norm_citation_text(m.group(1))
                if not cite:
                    continue
                if not _resolves(cite, targets):
                    line = text.count('\n', 0, pstart + m.start()) + 1
                    v.append(('citation-unresolved',
                              '%s:%d § %s' % (rel, line, cite)))
    return v


PROFILE_PATH_RE = re.compile(r'~/\.claude[\w.-]*/skills')


def check_all(root=ROOT):
    """Every violation the repo can currently detect, as (kind, detail) pairs,
    plus the counts each check examined. Read-only — writes nothing.

    Returns (violations, counts). `counts` is emitted alongside the verdict on
    purpose: `0 violations` says nothing without the denominator beside it, and
    a check whose denominator is zero because it looked in the wrong place
    reports exactly the same green as one that looked everywhere.

    Six checks:
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
    """
    v = []
    v.extend(check_citations(root))
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

        # citation-unresolved/no-target (W2-T9): plant a `§` citation whose
        # target heading exists nowhere in the tree, into a file
        # `check_citations` actually reads (`skills/_shared/core.md`,
        # unioned into every other file's resolvable set too, so this also
        # proves the plant is reachable from a persona file's citation, not
        # just core's own). The trap this guards against, named in this
        # run's brief: a control that plants its failure somewhere the
        # checked code path never touches passes green while testing
        # nothing. `Zzyzx9…` is deliberately not a prefix of any real
        # heading or bold label in the tree, so this control proves the
        # wholly-absent-target case only — it says nothing about a citation
        # whose real target WAS deleted while a same-first-word sibling
        # survives (`Run close` -> `Run report`), which is the shape briar's
        # Wave 2 Major found this exact control blind to by construction.
        # `citation-unresolved/truncation-floor` below covers that case.
        core_path = '%s/skills/_shared/core.md' % r
        orig_core = open(core_path).read()
        open(core_path, 'w').write(
            orig_core
            + '\n\nSee § Zzyzx9Unresolvable Selftest Marker Heading for '
              'details.\n')
        red = [x for x in check_all(r)[0] if x[0] == 'citation-unresolved']
        open(core_path, 'w').write(orig_core)
        green = [x for x in check_all(r)[0] if x[0] == 'citation-unresolved']
        fired, cleared = bool(red), not green
        ok &= fired and cleared
        print('selftest: %-22s red=%s green-after-restore=%s'
              % ('citation-unresolved/no-target', 'yes' if fired else 'NO',
                 'yes' if cleared else 'NO'))

        # citation-unresolved/truncation-floor (briar Wave 2 Major): mutate
        # a REAL colliding pair already in the tree, not a planted string —
        # the whole point is that the no-target control above is built
        # around avoiding this exact weak spot, so it proves nothing about
        # it. Two live pairs, each a heading sharing only its leading word
        # with a surviving sibling, cited by name in the Major:
        # `skills/sol/SKILL.md`'s `## Run close` (cited by its own `§ Run
        # close`, right beside `## Run report`) and `skills/eric/SKILL.md`'s
        # `## PR Label` (cited by `§ PR Label`, beside `## PR Readiness`).
        # Renaming the real target heading — never touching the citation —
        # reproduces exactly what a slimming pass does when it deletes a
        # section: pre-fix, `_resolves`'s truncation retry forgave both
        # down to `Run`/`PR` against the sibling; post-fix,
        # MIN_SINGLE_WORD_MATCH_LEN rejects both and the citation reports
        # unresolved, as it should.
        mutation_cases = [
            ('sol', '%s/skills/sol/SKILL.md' % r, '## Run close',
             '## XYZ close (selftest mutation)', 'Run close'),
            ('eric', '%s/skills/eric/SKILL.md' % r, '## PR Label',
             '## XYZ Label (selftest mutation)', 'PR Label'),
        ]
        for label, path, old_heading, new_heading, cite_fragment in mutation_cases:
            orig = open(path).read()
            mutated = orig.replace(old_heading, new_heading, 1)
            if mutated == orig:
                ok = False
                print('selftest: %-22s NO MATCH — %r not found in %s to '
                      'mutate' % ('citation-unresolved/truncation-floor/'
                                  + label, old_heading, path))
                continue
            open(path, 'w').write(mutated)
            red = [x for x in check_all(r)[0] if x[0] == 'citation-unresolved'
                   and cite_fragment in x[1]]
            open(path, 'w').write(orig)
            green = [x for x in check_all(r)[0]
                     if x[0] == 'citation-unresolved' and cite_fragment in x[1]]
            fired, cleared = bool(red), not green
            ok &= fired and cleared
            print('selftest: %-22s red=%s green-after-restore=%s'
                  % ('citation-unresolved/truncation-floor/' + label,
                     'yes' if fired else 'NO', 'yes' if cleared else 'NO'))

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
