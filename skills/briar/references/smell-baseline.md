# Smell baseline

Pasted in full into the Standards subagent's prompt — it is context-isolated
and has no other route to this file. A fixed list of Fowler-style code
smells, for spotting patterns a diff-only read might otherwise miss.

Two binding rules travel with this list:

- **The repo's own standards docs override this baseline.** Where a rule
  here conflicts with the repo's documented conventions (per the repo
  map), the repo wins.
- **Every smell below is a labelled heuristic, never a hard violation.**
  Report it as "possible Feature Envy," "possible Shotgun Surgery," never
  as a flat rule break — a smell names a pattern worth a second look, not
  a verdict.

Skip anything the repo's own tooling already enforces (a linter rule, a
type-checker constraint) — flagging what the toolchain already catches is
noise, not signal.

## The list

- **Long Method** — a function doing more than one job, identifiable by
  needing more than a sentence to describe what it does.
- **Large Class** — a class or module accumulating unrelated
  responsibilities rather than one cohesive purpose.
- **Duplicated Code** — the same logic or data shape appearing at multiple
  sites instead of one shared source.
- **Feature Envy** — a method that uses another object's data more than its
  own; the logic likely belongs on the object it keeps reaching into.
- **Data Clumps** — the same group of fields or parameters traveling
  together across multiple call sites without a name of their own.
- **Primitive Obsession** — a domain concept (money, a range, an ID)
  represented as a bare primitive instead of a small type that carries its
  own invariants.
- **Switch Statements / Conditional Complexity** — the same conditional
  logic repeated at multiple sites instead of a single dispatch point or
  polymorphic structure.
- **Shotgun Surgery** — a single conceptual change that requires edits
  across many unrelated files — a sign of scattered responsibility.
- **Divergent Change** — one class or module that changes for many
  unrelated reasons — a sign of accumulated, uncohesive responsibility.
- **Speculative Generality** — an abstraction, parameter, or hook built for
  a future need that isn't concretely required yet.
- **Message Chains** — a caller reaching through a long chain of accessors
  (`a.b.c.d.doSomething()`) to get to what it actually needs.
- **Middle Man** — a class whose methods mostly just delegate to another
  object, adding a layer without adding behavior.
- **Inappropriate Intimacy** — two classes or modules reaching into each
  other's internals rather than communicating through a defined interface.
- **Comments Compensating for Unclear Code** — a comment explaining what
  the code does because the code itself doesn't make it clear; the fix is
  usually to rename or restructure, not to keep the comment.
