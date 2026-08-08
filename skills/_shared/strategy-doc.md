# The business strategy doc

Read by the nine business-layer skills — vera, kora, ellis, charlie, quinn,
tess, remy, penny, lex — and nobody else. It is an opt-in fragment, not core:
only these nine cite it, and each does so from its own SKILL.md body per
`core.md:34`'s path-ownership delegation.

**Location.** `<plans>/business/strategy.md`, unless the repo map defines a
`strategy` role — the map's location wins over the default.

**Ownership.** vera owns the doc and writes every section freely. Every other
business persona reads the whole doc but appends only to its owned section:
kora → `## Market Research`, charlie → `## Marketing`, quinn → `## Sales`,
tess → `## Metrics`, penny → `## People`, lex → `## Legal & Compliance`,
ellis → finance content, remy → customer-success content. `## Decisions` is
shared, append-only working memory — each entry is an implicit do-not-undo.

**Created lazily.** The doc comes into existence on the first real write,
never seeded empty or header-only. If it's absent, offer to start it or to
append — write it only when there's actual content to record.

**Shape**, in full:

```markdown
# Strategy: <company or product name>
> Quarter: <e.g. Q3 2026> · Last updated: YYYY-MM-DD
## Mission & Positioning        — what the company is for; who it serves,
                                   against whom, why it wins
## OKRs                          — objectives as directions, key results as
                                   measurable outcomes
## Cross-Functional Priorities   — ranked; names what the company will NOT
                                   do as clearly as what it will
## Decisions                     — append-only, one line each with the why;
                                   each entry is an implicit do-not-undo.
                                   A rejected alternative gets a TL;DR of
                                   why it lost, so it isn't re-proposed
## History                       — append-only dated one-liners
## Sessions                      — one line per session: the orientation
                                   battery's open: line, closed with the
                                   scope verdict (`core.md` § Opening
                                   Orientation Battery owns the shape)
## Metrics                       — targets and measured outcomes (tess's
                                   landing spot)
## Initiatives → PRDs            — pointers from strategy sections to
                                   parker's PRDs
```

Persona-owned sections (`## Market Research`, `## Marketing`, `## Sales`,
`## Metrics`, `## People`, `## Legal & Compliance`, and finance /
customer-success content) aren't shipped in the template above — each is
added by its owner on that owner's first write.

**Reconcile, don't overwrite.** When a new finding conflicts with a recorded
Decision, update the entry with the reason it changed — never silently
replace a documented choice. If the conflict needs input nobody in the
session has, surface it rather than resolve it unilaterally.

**Open questions stay visible.** A call that needs input you don't have yet
gets recorded instead of blocking work:

```markdown
- **OPEN — TBD, needs <name> input.** <the open question>. **Default path
  (used until resolved):** <what work follows in the meantime>.
```

When the question resolves, replace the entry with a normal Decision and
note the resolution in `## History`.
