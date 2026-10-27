---
name: describe-codebase
description: >-
  Explain how a codebase is shaped — the repository, one subsystem, or
  one feature — as an orientation brief with file:line references. Use to
  understand an unfamiliar codebase, map the architecture, or trace how a
  feature flows. Never edits code, only ARCHITECTURE.md or AGENTS.md when
  asked. Not for reviewing or improving code (review-pr,
  simplify-sweep) or planning an unbuilt feature (plan-feature).
---

# describe-codebase

## Overview

Give a newcomer their bearings: how the code is shaped, where to start, and
how to work in it the way its authors do. This is orientation, not review. Do
not critique, rank, or propose changes.

## When to use

- Understanding an unfamiliar repository, subsystem, or path.
- Tracing how one feature, endpoint, or entry point flows end to end.
- Not for finding problems (review-pr, simplify-sweep) or planning something
  unbuilt (plan-feature).

## What good looks like

- **Grounded.** Read the project's own guidance first (AGENTS.md, README,
  CLAUDE.md, CONTRIBUTING, architecture notes) and point at it instead of
  re-deriving it. Every structural claim carries a `file:line` the reader can
  click to verify.
- **Honest.** Report what the code does, not what you would prefer. If
  something is not found (no central config, no discoverable test command),
  say "not found". Never guess or invent commands, layers, or hops.
- **Scoped.** No scope means the whole repository; a path or glob means that
  subtree; a feature, endpoint, or entry point means a flow trace. Ask once
  if the scope is ambiguous. If nothing is in scope, say so and stop.
- **Skimmable.** A brief, not an essay. Scale it to the scope.

Investigate in parallel where the host supports delegation, otherwise
locally. A lens that fails or comes back empty is noted, not blocking.

For a map (repository or path), cover these lenses:

- **Layering and entry points:** where execution starts, how a unit of work
  flows, which layer may call which, plus config, auth, error handling,
  logging.
- **Data and persistence:** where the model is defined, what stores it, who
  owns schema and migrations, the access layer, key relationships. If there is
  no data layer, say so.
- **Conventions and build:** naming idioms, how a new component is wired in,
  declared project rules, and the real lint, format, test, and build commands
  (docs first, then config and CI).

For a flow trace, find the entry point first (route, handler, command, or
symbol). If you cannot find it, report what you searched and ask rather than
guess. Then follow the actual calls through handler, logic, data access, and
external calls, noting meaningful branch points and where data changes shape.
Where the trail goes cold (dynamic dispatch), report the last solid hop.

## Boundaries

- Read-only. Never edit code.
- Chat is the default. Write only when asked, and only `ARCHITECTURE.md` or
  the `AGENTS.md` project-specific section. Preview changes to an existing
  file and confirm before writing; never overwrite silently.
- Needs no `gh`, no remote, and no main-branch detection; any checkout works,
  including a fresh clone.

## Output

For a map, a short brief with a line each for layering, shared infrastructure
(config, auth, errors, logging), data, conventions, commands, and a "Start
here" list of 3 to 5 files a newcomer should read in order, each with
`file:line`.

For a flow trace, an ordered numbered walkthrough from entry point to the
data or external boundary, one `file:line` per hop, with branch points called
out.
