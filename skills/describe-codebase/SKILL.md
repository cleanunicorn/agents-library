---
name: describe-codebase
description: >-
  Explain how a codebase is shaped: the whole repository, one subsystem
  (path/glob), or a single feature/flow traced end to end. Produces a skimmable
  orientation brief with file:line references; can optionally write it to
  ARCHITECTURE.md. Use when the user wants to understand or onboard onto an
  unfamiliar codebase, "explain how this works", map the architecture, or trace
  how a feature/endpoint flows. Read-only — it explains, it never judges or
  edits. Do NOT use to review, critique, or improve code (use review-pr for the
  branch diff, simplify-sweep for cleanup opportunities). No `gh` or remote
  required.
---

# describe-codebase

You are the **orchestrator** of a read-to-explain survey of a codebase. The user
wants to understand how some code is shaped — the whole repository, one
subsystem, or one feature's execution path. Your job is to orient on the
project, fan out read-only explorer sub-agents, consolidate what they find into
one orientation brief, and optionally persist it.

This is the inverse of `review-pr`: where that skill reads a diff to *critique*
it, you read a codebase to *explain* it. You produce orientation, not findings to
fix.

## Why this shape

"Where does execution flow?", "how is data stored?", and "what are the
conventions and commands?" are different mental modes — one lens per explorer
maps each more sharply, and you merge the results into a single brief. The
explorers **only read**; the only thing ever written is the optional doc the
user opts into in Phase 3, which is what makes this safe to point at any repo.

## Phase 0 — Orient & resolve scope (do this once, yourself)

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

Dispatch all sub-agents **in parallel** — issue every Agent/Task call in a single
message so they run concurrently (the
`superpowers:dispatching-parallel-agents` pattern).

**Model choice:** unless the user specified a model, run the explorer/tracer
sub-agents on a **lesser model** than your own session — one tier down (e.g.
`haiku` from a `sonnet` session, `sonnet` from an `opus` session), via the
Agent tool's model parameter. Each lens is a bounded read-and-report task, so
the cheaper tier is normally enough. If a lens comes back clearly degraded,
re-run that one lens on the session model.

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
handler, command, or symbol). Then dispatch tracers along the path it touches —
entry/handler, business logic, data access, and any external call — each given
`lenses/flow-trace.md` verbatim plus its assigned segment and starting location.
If the segments aren't knowable up front, dispatch the entry tracer first, then
fan out the remaining segments from where it hands off.

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole brief on one lens or segment.

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
for something (e.g. no central config, commands undiscoverable), say so plainly
rather than omitting the line.

For a **flow trace**, render an ordered, numbered walkthrough instead: each hop a
`file:line` reference, from the entry point through to the data/external boundary
and back, with the meaningful branch points called out.

Keep it skimmable — an orientation, not an essay.

## Phase 3 — Offer to persist

Ask the user whether to write the brief to disk:

- **(a)** a new `ARCHITECTURE.md` at the repo root,
- **(b)** appended to the `AGENTS.md` project-specific section, or
- **(c)** chat only — write nothing (the default).

Only write on an explicit pick. If the chosen target already **exists**, show
what would change (the file's proposed content, or the exact append) and confirm
before writing — never overwrite a hand-written doc silently. You write **no
code** under any path; the only artifact you ever create is this one doc.

## Finding schema

Each explorer returns findings as records with these fields:

```
lens:      layering | data | conventions | flow-<segment>
topic:     short label (e.g. "config object", "auth guard", "test layout")
location:  path:line     — required; the claim's evidence
detail:    one or two lines on what's there and why it matters
```

You compose these into the brief sections; you do not surface the raw records.

## Error handling

- **Empty or unrecognized target** (no source files in scope): report there's
  nothing to map and stop.
- **An explorer fails or returns nothing:** note it, continue with the others;
  render the brief from whatever returned.
- **Flow-trace target not found:** report what you searched (the symbol, route,
  or file patterns tried) and ask the user to disambiguate rather than guessing.
- **Commands not discoverable:** render the brief with the **Commands** line
  marked "not found" rather than fabricating them.
- **Doc-write target already exists:** show the diff/append preview and confirm;
  never overwrite silently.
