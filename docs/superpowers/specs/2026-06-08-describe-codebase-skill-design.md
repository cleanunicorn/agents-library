# describe-codebase — design

**Status:** approved for planning
**Date:** 2026-06-08
**Repo:** agents-library (Claude Code plugin marketplace)

## Summary

`describe-codebase` is a new orchestrator skill for the agents-library plugin.
It is the **read-to-explain** counterpart to `review-pr`: where `review-pr`
reads a branch diff to *critique* it, `describe-codebase` reads a codebase to
*explain* it — producing an orientation brief for someone landing in an
unfamiliar repository or subsystem.

It surveys a target — the whole repository (default), a path/glob, or a single
feature/flow — by fanning out read-only explorer sub-agents, consolidates what
they find into one skimmable brief shown in the conversation, and then
optionally persists that brief to a doc on the user's explicit confirmation. It
**never modifies code**; the only artifact it can write is an architecture doc,
and only when the user opts in.

## Why this skill

The library already reviews a diff (`review-pr`), batch-merges PRs
(`batch-merge-prs`), and surveys a repo for simplifications (`simplify-sweep`).
Every one of those — and every single-purpose agent — *orients on the project
first* (the "orient yourself" step in `AGENTS.md`) but treats that orientation
as private scaffolding that's thrown away after the real work. What's missing is
a skill that makes the orientation itself the deliverable: an explanation of how
the codebase is shaped, for a human (or a fresh agent) who needs to get their
bearings. This is the most frequent day-to-day need with zero current coverage:
first day in a repo, before touching an unfamiliar subsystem, onboarding a
teammate, or understanding how one feature actually flows.

## Design decisions (resolved during brainstorming)

1. **Deliverable is a brief, with an optional written doc.** The skill always
   produces an in-chat orientation brief; it then *offers* to persist it. The
   doc is the only thing ever written to disk, and only on an explicit user
   pick. This mirrors `review-pr`'s "report, then act on confirmation" shape and
   keeps the default run zero-write.
2. **Three runtime scopes:** whole repository (default), a path/glob
   (one subsystem in depth), or a feature/flow trace (one execution path end to
   end). The scope is chosen from the invocation argument.
3. **Read-only sub-agents.** Explorers only read and report; they never edit.
   The orchestrator writes nothing except the optional doc in the final phase.
   This is the same analysis/action separation `review-pr`, `batch-merge-prs`,
   and `simplify-sweep` use.
4. **Two fan-out shapes, by scope.** Map scopes (whole-repo, path) fan out
   **three lens explorers** in parallel. The flow-trace scope instead fans out
   **per-segment tracers** along the path the flow touches (entry → business →
   data → external) and stitches them into one ordered walkthrough. This is the
   one genuinely new fan-out shape versus the repo's existing skills.
5. **Cross-cutting concerns fold into the Layering lens** rather than getting a
   fourth explorer. Config, auth model, error handling, and logging are part of
   what a newcomer must find; the Layering & entry-points explorer already maps
   the shared infrastructure, so it carries them. Keeps the fan-out lean (three
   agents) without losing onboarding-critical content.
6. **Every claim carries a `file:line` reference.** The brief is only useful if
   it's verifiable and clickable; explorers must cite locations, not assert.
7. **Doc writes never clobber silently.** If the chosen write target already
   exists, the skill shows what would change (a new `ARCHITECTURE.md`, or an
   append to the `AGENTS.md` project-specific section) and asks before writing.
8. **Name:** `describe-codebase`. Verb-noun, matches the repo's framing
   (`batch-merge-prs`, `simplify-sweep`); says plainly what it does and does not
   collide with any built-in command.

## Architecture

A single orchestrator (the skill) drives the run. It dispatches read-only
explorer sub-agents that **only analyze** — they never edit. The only write
happens in the final phase, in the orchestrator, and only on user confirmation.

### Phase 0 — Orient (once, by the orchestrator)

- Read the project's guidance (`AGENTS.md`, `README`, `CLAUDE.md`,
  `CONTRIBUTING`, architecture notes). Capture what's already documented so the
  brief reflects and points at it rather than re-deriving it.
- Resolve the **scope argument**:
  - none → whole repository
  - a path or glob → just that subtree/match
  - a feature/flow name, endpoint, or entry point → flow-trace scope
- Gather a top-level directory/file listing of the resolved target to bundle
  into each explorer, so the explorers don't each re-enumerate the tree.
- No main-branch detection and no `gh` are required — this works on any
  checkout, including a fresh clone with no history context.

### Phase 1 — Fan out (shape depends on scope)

Dispatch all sub-agents **in parallel** (the
`superpowers:dispatching-parallel-agents` pattern). Each sub-agent's prompt has
three parts: the **shared context** from Phase 0, **its lens/segment prompt**
(read the matching file from `lenses/` and include it verbatim), and the
**output contract**: *read-only; do not modify any file; read what you need;
return findings in this exact schema with `file:line` references.*

**Map scopes (whole-repo, path) — three lens explorers:**

| Explorer | Emoji | File | Maps |
|----------|-------|------|------|
| Layering & entry points | 🧭 | `lenses/layering.md` | How the app boots; the request/data flow; which layer may call which; **plus cross-cutting infra: the config object, auth model, error handling, logging.** |
| Data & persistence | 🗃️ | `lenses/data.md` | Schema, migrations, the data-access layer, and where data-structure ownership lives. |
| Conventions & build | 📐 | `lenses/conventions.md` | Naming idioms; how a new component gets wired in (router/DI/registry/dispatch table); the lint/format/test/build commands. |

**Flow-trace scope — per-segment tracers:**

Given the entry point, dispatch tracers along the path the flow touches —
entry/handler, business logic, data access, and any external calls — each
reporting its segment with `file:line` hops (`lenses/flow-trace.md` is the
shared instruction for how to trace a segment). The orchestrator stitches the
segments into one ordered, numbered walkthrough in Phase 2.

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole brief on one lens or segment.

### Phase 2 — Consolidate & present the brief

Merge the explorers' findings into one skimmable orientation brief, scaled to
the scope, shown in the conversation.

For a **map scope**:

```
## <repo/subsystem> — orientation

**Layering**     entry → business → data; who-calls-who
**Shared infra** config: …  auth: …  errors: …  logging: …
**Data**         schema owner: …  migrations: …  access layer: …
**Conventions**  naming idioms; how to wire a new component
**Commands**     lint: …  format: …  test: …  build: …
**Start here**   3–5 files a newcomer should read first, in order
```

For a **flow trace**: an ordered, numbered walkthrough of the path, each hop a
`file:line` reference, from entry to the data/external boundary and back.

Every line that makes a structural claim carries a `file:line` reference so the
reader can verify and click through. Keep it skimmable — an orientation, not an
essay.

### Phase 3 — Offer to persist

Ask the user whether to write the brief to disk:

- **(a)** a new `ARCHITECTURE.md` at the repo root,
- **(b)** appended to the `AGENTS.md` project-specific section, or
- **(c)** chat only — write nothing (the default).

Only write on an explicit pick. If the chosen target already exists, show what
would change (the new file's content, or the append) and confirm before writing
— never overwrite a hand-written doc silently. The skill writes **no code**
under any path.

## Finding schema

Each explorer emits findings as records with these fields:

```
lens:      layering | data | conventions | flow-<segment>
topic:     short label (e.g. "config object", "auth guard", "test layout")
location:  path:line     — required; the claim's evidence
detail:    one or two lines explaining what's there and why it matters
```

The orchestrator composes these into the brief sections; it does not surface the
raw records.

## File structure

Mirrors the existing skills (`review-pr`, `batch-merge-prs`):

```
skills/describe-codebase/
  SKILL.md
  lenses/
    layering.md
    data.md
    conventions.md
    flow-trace.md
```

Plus plugin wiring so the skill installs with the marketplace, the same way
`review-pr` and `batch-merge-prs` are registered. The README's skills section
and the plugin description gain a `describe-codebase` entry.

## Error handling

- **Empty or unrecognized target** (no source files in scope): report there's
  nothing to map and stop.
- **An explorer fails or returns nothing:** note it, continue with the others;
  the brief renders from whatever returned.
- **Flow-trace target not found:** report what was searched (the symbol/route/
  file patterns tried) and ask the user to disambiguate rather than guessing.
- **Commands not discoverable** in Phase 1's conventions lens: render the brief
  with the commands marked "not found" rather than fabricating them.
- **Doc-write target already exists:** show the diff/append preview and confirm;
  never overwrite silently.
