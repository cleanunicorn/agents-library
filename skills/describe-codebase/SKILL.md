---
name: describe-codebase
description: >-
  Explain how a codebase is shaped — the whole repository, one subsystem, or
  one feature traced — as an orientation brief with file:line
  references. Use to understand an unfamiliar codebase, map the architecture,
  or trace how a feature flows. Read-only unless asked to update ARCHITECTURE.md
  or AGENTS.md; never edits code. Not for reviewing or improving code
  (review-pr, simplify-sweep).
---

# describe-codebase

You are the **orchestrator** of a read-to-explain survey of a codebase. The user
wants to understand how some code is shaped — the whole repository, one
subsystem, or one feature's execution path. Your job is to orient on the
project, fan out read-only explorer sub-agents, consolidate what they find into
one orientation brief, and optionally persist it. You produce orientation, not
findings to fix.

## Phase 0 — Orient & resolve scope

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and architecture notes. Capture what's already documented so
   the brief reflects and points at it rather than re-deriving it. If a rule is
   declared (commit format, layering, style bars), note where it lives.
2. **Resolve the scope** from the user's invocation:
   - **none → whole repository** (the default): map the entire codebase.
   - **a path or glob** (e.g. `src/payments/`): map just that subtree.
   - **a feature/flow name, endpoint, or entry point**: flow-trace scope.
   If it's ambiguous which the user means, ask once before fanning out.
3. **Gather a top-level listing** of the resolved target (directory tree, key
   files) to bundle into each explorer so they don't each re-enumerate the tree.

No main-branch detection and no `gh` are required — this works on any checkout,
including a fresh clone. If the target has no source files in scope, say there's
nothing to map and stop.

## Phase 1 — Fan out (shape depends on scope)

Dispatch independent explorers concurrently, batching to the host's limits.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only exploration, or inherit the
session model. Retry at the session tier only when required fields or assigned
coverage are missing.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project-guidance summary and the
   top-level listing of the target.
2. **The lens/segment prompt** — read the matching file from `lenses/` and
   include it verbatim. That file is the sub-agent's entire instruction set.
3. **The output contract** — the finding schema below, with the instruction:
   *read-only; do not modify any file; read what you need; return findings in
   this exact schema with a `file:line` reference on every finding, or an empty
   list if you find nothing.*

**Map scopes (whole-repo, path) — three lens explorers:**

| Explorer | Emoji | File | Maps |
|----------|-------|------|------|
| Layering & entry points | 🧭 | `lenses/layering.md` | Boot, request/data flow, layer boundaries, plus config, auth, error handling, logging. |
| Data & persistence | 🗃️ | `lenses/data.md` | Schema, migrations, data-access layer, schema ownership. |
| Conventions & build | 📐 | `lenses/conventions.md` | Naming idioms, how to wire a new component, lint/format/test/build commands. |

**Flow-trace scope — per-segment tracers:**

Identify the entry point for the named feature/flow first (search for the route,
handler, command, or symbol). If you cannot find it, report what you searched
(the symbol, route, or file patterns tried) and ask the user to disambiguate
rather than guessing. Then dispatch tracers along the path it touches —
entry/handler, business logic, data access, and any external call — each given
`lenses/flow-trace.md` verbatim plus its assigned segment and starting location.
If the segments aren't knowable up front, dispatch the entry tracer first, then
fan out the remaining segments from where it hands off.

If a sub-agent fails or returns nothing, note it and continue with the others —
render the brief from whatever returned; never block it on one lens or segment.

## Phase 2 — Consolidate & present the brief

Merge the explorers' findings into one skimmable orientation brief, scaled to the
scope, shown in the conversation. Every line that makes a structural claim
carries its `file:line` so the reader can click through and verify.

For a **map scope**, render the brief in this shape:

```
## <repo/subsystem> — orientation

**Layering**     entry → business → data; who-calls-who
**Shared infra** config: …  auth: …  errors: …  logging: …
**Data**         schema owner: …  migrations: …  access layer: …
**Conventions**  naming idioms; how to wire a new component
**Commands**     lint: …  format: …  test: …  build: …
**Start here**   3–5 files a newcomer should read first, in order
```

Fill each line from the explorers' findings, each pointing at a `file:line`. The
**Start here** list is your synthesis — the handful of files that best orient a
newcomer, drawn from across the three lenses. If an explorer reported "not found"
for something (e.g. no central config, commands undiscoverable), mark that line
"not found" rather than omitting or fabricating it.

For a **flow trace**, render an ordered, numbered walkthrough instead: each hop a
`file:line` reference, from the entry point through to the data/external boundary
and back, with the meaningful branch points called out.

Keep it skimmable — an orientation, not an essay.

## Phase 3 — Persist only when requested

Chat is the default: do not ask a persistence question after delivering the
brief. If the original request asks to save it, write a new `ARCHITECTURE.md` or
append it to the `AGENTS.md` project-specific section, as requested. Preview
changes to an existing target and confirm before writing; never overwrite
silently. Never edit code.

## Finding schema

Each explorer returns findings as records with these fields:

```
lens:      layering | data | conventions | flow-<segment>
topic:     short label (e.g. "config object", "auth guard", "test layout")
location:  path:line     — required; the claim's evidence
detail:    one or two lines on what's there and why it matters
```

You compose these into the brief sections; you do not surface the raw records.
