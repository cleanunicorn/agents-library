# describe-codebase Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `describe-codebase` orchestrator skill for the agents-library plugin — the read-to-explain counterpart to `review-pr` — that surveys a target (whole repo, path/glob, or a feature/flow) by fanning out read-only explorer sub-agents, consolidates their findings into one orientation brief, and optionally persists that brief to a doc on the user's confirmation.

**Architecture:** The skill is a set of markdown files following the existing `review-pr`/`simplify-sweep` shape: a `SKILL.md` orchestrator plus one `lenses/*.md` prompt per explorer. The orchestrator (the model running the skill) orients on the project, resolves the scope, fans out read-only explorer sub-agents via the Agent/Task tool, consolidates their findings into a brief, and writes nothing except an optional doc the user explicitly opts into. Sub-agents only read; the orchestrator does all consolidation and the single optional write.

**Tech Stack:** Markdown (Claude Code plugin skill format with YAML frontmatter), git for branching/commits. No application code, no `gh`, no remote. "Tests" for this deliverable are **structural verification commands** (file existence, frontmatter validity, internal-reference resolution) since the artifact is prose, not code.

---

## File Structure

All paths relative to the repo root.

- Create: `skills/describe-codebase/SKILL.md` — the orchestrator. Frontmatter (name + trigger-rich description) and the Phase 0–3 workflow.
- Create: `skills/describe-codebase/lenses/layering.md` — explorer 1 prompt (layering & entry points + cross-cutting infra).
- Create: `skills/describe-codebase/lenses/data.md` — explorer 2 prompt (data & persistence).
- Create: `skills/describe-codebase/lenses/conventions.md` — explorer 3 prompt (conventions & build).
- Create: `skills/describe-codebase/lenses/flow-trace.md` — per-segment tracer prompt (flow-trace scope).
- Modify: `README.md` — add a "Describe Codebase Skill" section and list `/describe-codebase` in the two install blurbs.

No `plugin.json` / `marketplace.json` change: skills auto-discover from `skills/` (confirmed by how `review-pr` and `simplify-sweep` ship).

**Build order:** lens files first (Task 1), so the SKILL.md references resolve when written (Task 2), then README (Task 3), then end-to-end verification (Task 4). Each task ends in its own commit on the `feat/describe-codebase-skill` branch (already created and holding the design spec).

---

## Task 1: The four lens files

**Files:**
- Create: `skills/describe-codebase/lenses/layering.md`
- Create: `skills/describe-codebase/lenses/data.md`
- Create: `skills/describe-codebase/lenses/conventions.md`
- Create: `skills/describe-codebase/lenses/flow-trace.md`

Each file is a self-contained sub-agent prompt in the same format as
`skills/review-pr/domains/*.md`, but **read-to-explain** rather than critique:
a titled intro, **What to map**, **What NOT to do**, and **Output** (the finding
schema, every claim carrying a `file:line` reference, read-only). The intro
frames the agent as an *explorer holding one lens over the target*, not a
reviewer judging a diff.

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p skills/describe-codebase/lenses
```

- [ ] **Step 2: Write `layering.md`**

Create `skills/describe-codebase/lenses/layering.md` with exactly:

```markdown
# Layering & entry points 🧭

You are the **layering & entry points** explorer for the target you were given
(the whole repository, or a single subsystem path). Your job is to *explain how
this code is shaped* so a newcomer can find their bearings — not to critique it.

Map two things. First, the **structural backbone**: where the program starts,
how a request or unit of work flows through it, and which layer is allowed to
call which (entry/presentation → business logic → data access). Second, the
**shared infrastructure a newcomer must find on day one**: the central config
object, the auth model, how errors are handled, and where logging lives.

Read the project guidance you were handed first, then read the actual entry
points and a couple of well-built modules to see the intended layering. Report
what the code *does*, with evidence — not what you'd prefer.

## What to map

- **Entry points** — where execution begins (CLI main, HTTP server bootstrap,
  worker/queue consumers, scheduled jobs). Name the file and the boot sequence.
- **The layers and their boundaries** — how entry/presentation, business logic,
  and data access are separated, and the direction calls are allowed to flow.
- **A representative flow** — pick one typical path (e.g. one request or command)
  and trace it across the layers in a sentence or two, with `file:line` hops.
- **Config** — the central configuration object/module and how code reads it
  (vs. reading the environment directly).
- **Auth** — where authentication/authorization is enforced (the guard, the
  middleware, the decorator) and what model it uses.
- **Error handling** — the project's convention for raising, wrapping, and
  surfacing errors; where the central handler lives if there is one.
- **Logging** — the logging entry point and how cross-cutting concerns are wired.

## What NOT to do

- Do not critique, rank, or propose changes — this is orientation, not review.
- Do not modify any file.
- Do not map data schema/migrations (the data explorer owns that) or naming/
  build commands (the conventions explorer owns those) beyond what you need to
  explain the flow.
- Do not assert structure you can't point at — if you can't find the auth model
  or a central config, say "not found" rather than guessing.

## Output

Return findings in the orchestrator's schema. Each finding's `topic` is a short
label (e.g. "entry point", "config object", "auth guard", "error handling"),
`location` is the `path:line` evidence (required), and `detail` is one or two
lines on what's there and why a newcomer cares. Read-only — never edit files.
If the target genuinely has no discernible layering (e.g. a flat script),
return what you can and say so.
```

- [ ] **Step 3: Write `data.md`**

Create `skills/describe-codebase/lenses/data.md` with exactly:

```markdown
# Data & persistence 🗃️

You are the **data & persistence** explorer for the target you were given (the
whole repository, or a single subsystem path). Your job is to *explain how this
code stores and accesses data* so a newcomer understands the data layer — not to
critique it.

Map where the project's data structures are defined, how they are persisted and
migrated, and how runtime code reaches them. Read the schema/model definitions
and the data-access code first; report what's there, with evidence.

## What to map

- **The data model** — where entities/tables/documents/types are defined (the
  schema files, ORM models, type definitions). Name the files and the main
  entities.
- **Persistence** — what stores the data (relational DB, document store,
  key-value, files, external service) and how the project talks to it.
- **Migrations / schema ownership** — where the structure is owned and evolved
  (migration directory, schema files) versus runtime code that must NOT create
  structure. Name where migrations live and how they're run if discoverable.
- **The data-access layer** — the repositories/DAOs/query modules runtime code
  goes through to read and write, and the boundary between "business logic" and
  "touches the store".
- **Key relationships** — the handful of relationships a newcomer needs to grasp
  the domain (e.g. "an Order has many LineItems"), each pointing at the defining
  file.

## What NOT to do

- Do not critique, rank, or propose changes — this is orientation, not review.
- Do not modify any file.
- Do not map entry points/auth/config (the layering explorer owns those) or
  naming/build commands (the conventions explorer owns those).
- Do not assert a store or schema you can't point at — if the project has no
  persistence layer (e.g. a pure library), say so plainly.

## Output

Return findings in the orchestrator's schema. Each finding's `topic` is a short
label (e.g. "schema owner", "migrations", "data-access layer", "core entity"),
`location` is the `path:line` evidence (required), and `detail` is one or two
lines on what's there and why a newcomer cares. Read-only — never edit files.
If the target has no data layer, return that conclusion with what evidence you
have.
```

- [ ] **Step 4: Write `conventions.md`**

Create `skills/describe-codebase/lenses/conventions.md` with exactly:

```markdown
# Conventions & build 📐

You are the **conventions & build** explorer for the target you were given (the
whole repository, or a single subsystem path). Your job is to *explain how to
work in this codebase the way its authors do* — the unwritten conventions and
the commands that matter — not to critique anything.

Infer conventions by reading a couple of well-built modules, not from your own
preference. The most valuable output is the answer to "if I add a new component
here, how do I make it look like it belongs?" and "how do I lint, test, and
build?".

## What to map

- **Naming idioms** — how files, modules, types, and functions are named (case
  style, suffixes like `*Service`/`*Repository`, test file naming). Give a
  concrete example with a `file:line`.
- **How a new component gets wired in** — the registration mechanism the project
  uses (router table, module index/barrel, DI container, dispatch map, plugin
  registry). Point at an existing registration so a newcomer can copy it.
- **Code-style conventions** — the patterns the codebase clearly follows (early
  returns, error-handling shape, import ordering) as evidenced in real files.
- **Project-declared rules** — if `AGENTS.md`/`CLAUDE.md`/`CONTRIBUTING` declare
  rules (commit format, confidence indicators, style bars), capture them and
  point at the source.
- **The commands that matter** — how to lint, format, test, and build. Find them
  from the docs first, then config (`package.json` scripts, `Makefile`,
  `pyproject.toml`, `justfile`, CI config). Report the actual command strings.

## What NOT to do

- Do not critique, rank, or propose changes — this is orientation, not review.
- Do not modify any file.
- Do not map layering/auth/config (the layering explorer) or schema/migrations
  (the data explorer) beyond naming examples.
- Do not invent commands. If you cannot find the lint/format/test/build command,
  report it as "not found" rather than guessing a likely one.

## Output

Return findings in the orchestrator's schema. Each finding's `topic` is a short
label (e.g. "naming idiom", "component wiring", "test command", "commit
format"), `location` is the `path:line` evidence (required; for a command, the
config file and line it's declared in), and `detail` is one or two lines a
newcomer can act on. Read-only — never edit files.
```

- [ ] **Step 5: Write `flow-trace.md`**

Create `skills/describe-codebase/lenses/flow-trace.md` with exactly:

```markdown
# Flow trace 🔗

You are a **flow tracer** for one segment of a single execution path the user
asked about (a feature, an endpoint, or an entry point). The orchestrator has
told you which segment to cover — the entry/handler, the business logic, the
data access, or an external call. Your job is to *follow the flow through your
segment and report the ordered hops* so the segments can be stitched into one
end-to-end walkthrough.

Start from the location the orchestrator gave you (the entry point, or where the
previous segment handed off). Follow the actual calls — read the functions they
land in — until your segment hands off to the next (a call into the next layer,
a store read/write, or an external request). Report each hop as a numbered step
with a `file:line` reference and a one-line description of what happens there.

## What to map

- **The ordered hops** through your segment: each function/method the flow enters,
  in call order, with `file:line` and what it does.
- **The hand-off** — where your segment passes control on (the call into the next
  layer, the query executed, the external request made). Name it so the next
  segment's tracer (or the orchestrator) can continue from there.
- **Branch points that matter** — if the flow forks on a meaningful condition
  (auth fails, cache hit, validation error), note the branch and where each goes.
- **Data shape changes** — if the payload is transformed/validated/serialized in
  your segment, say so in one line.

## What NOT to do

- Do not critique the flow or propose changes — this is a trace, not a review.
- Do not modify any file.
- Do not trace beyond your assigned segment; stop at the hand-off and name it.
- Do not invent hops. If the trail goes cold (dynamic dispatch, a call you can't
  resolve), report the last solid hop and say where it became unclear.

## Output

Return findings in the orchestrator's schema, one finding per hop. `topic` is the
hop's order and role (e.g. "1. handler", "2. validation", "3. service call"),
`location` is the `path:line` (required), and `detail` is one line on what happens
at that hop. Read-only — never edit files. If you cannot locate the starting
point at all, return that and describe what you searched.
```

- [ ] **Step 6: Verify all four files exist and are non-empty**

Run:
```bash
ls -1 skills/describe-codebase/lenses/ && wc -l skills/describe-codebase/lenses/*.md
```
Expected: four files listed (`conventions.md`, `data.md`, `flow-trace.md`,
`layering.md`), each with a non-trivial line count (>30 lines).

- [ ] **Step 7: Commit**

```bash
git add skills/describe-codebase/lenses/
git commit -m "feat(skills): add describe-codebase explorer lens prompts"
```

---

## Task 2: The SKILL.md orchestrator

**Files:**
- Create: `skills/describe-codebase/SKILL.md`

This is the orchestrator the model runs. It has trigger-rich frontmatter (so it
fires on "explain this codebase", "how does this work", "onboard me", "map the
architecture", "trace this flow") and the Phase 0–3 workflow from the spec.

- [ ] **Step 1: Write `SKILL.md`**

Create `skills/describe-codebase/SKILL.md` with exactly:

````markdown
---
name: describe-codebase
description: >-
  Explain how a codebase is shaped — the read-to-explain counterpart to
  review-pr. Orients on the project, then fans out read-only explorer sub-agents
  to map it across three lenses (layering & entry points incl. config/auth/error
  handling, data & persistence, conventions & build), consolidates their findings
  into one skimmable orientation brief with file:line references, and optionally
  writes that brief to a doc. Supports three scopes: whole repository (default),
  a path/glob for one subsystem, or a feature/flow trace that follows a single
  execution path end to end. Use this whenever the user wants to understand an
  unfamiliar codebase, "explain how this works", get oriented, onboard onto a
  repo or subsystem, map the architecture, write an ARCHITECTURE.md, or trace how
  a feature/endpoint flows — even if they don't say the word "skill". Read-only
  by default; never modifies code and writes a doc only on explicit confirmation.
  No `gh` or remote required.
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

A single agent reading a whole codebase top-to-bottom blurs together questions
that need different attention: "where does execution start and flow?", "how is
data stored?", and "what are the conventions and commands?" are different mental
modes. Focused explorers, each holding one lens over the same target, map more
and map it more sharply. You then merge their findings into one brief so the user
sees an orientation, not three separate reports.

The explorers **only read** — they never edit. The only thing you ever write is
an optional doc the user explicitly opts into (Phase 3). Keeping the survey
read-only is what makes it safe to point at any repo, including one you've never
seen.

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
````

- [ ] **Step 2: Verify the frontmatter parses and references resolve**

Run:
```bash
head -20 skills/describe-codebase/SKILL.md && echo "--- referenced lens files ---" && for f in layering data conventions flow-trace; do test -f "skills/describe-codebase/lenses/$f.md" && echo "OK $f.md" || echo "MISSING $f.md"; done
```
Expected: the YAML frontmatter (`---`, `name: describe-codebase`, a
`description:` block, `---`) prints, and all four lens files report `OK`.

- [ ] **Step 3: Verify name uniqueness against existing skills**

Run:
```bash
grep -rl "^name: describe-codebase" skills/
```
Expected: exactly one path — `skills/describe-codebase/SKILL.md`. (No collision
with `review-pr`, `batch-merge-prs`, or `simplify-sweep`.)

- [ ] **Step 4: Commit**

```bash
git add skills/describe-codebase/SKILL.md
git commit -m "feat(skills): add describe-codebase orchestrator skill"
```

---

## Task 3: Wire into the README

**Files:**
- Modify: `README.md`

Add a "Describe Codebase Skill" section (mirroring the existing "The PR Review
Skill" / "The Batch PR Merge Skill" sections) and list `/describe-codebase` in
the install description.

- [ ] **Step 1: Add the skill section**

In `README.md`, after the "The Batch PR Merge Skill" section (which ends at the
line before "## The Agents"), insert this new section:

```markdown
## The Describe Codebase Skill

[`describe-codebase`](skills/describe-codebase/SKILL.md) is the read-to-explain
counterpart to `review-pr`: it explains how a codebase is shaped so you can get
your bearings. It orients on the project, fans out read-only explorer sub-agents
across three lenses (layering & entry points — including config, auth, and error
handling — data & persistence, and conventions & build), and consolidates their
findings into one skimmable orientation brief where every claim carries a
`file:line` reference. It supports three scopes: the whole repository (default),
a path/glob for a single subsystem, or a feature/flow trace that follows one
execution path end to end. The brief is shown in the conversation; you can
optionally persist it to a new `ARCHITECTURE.md` or append it to `AGENTS.md`. It
never modifies code and writes a doc only on your explicit confirmation. No `gh`
or remote required.

```

- [ ] **Step 2: Update the install blurb**

In `README.md`, find the line in the "Install (Claude Code plugin)" section that
reads:

```
This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr` and `/batch-merge-prs` skills plus all seven agents as subagents.
```

Replace it with:

```
This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr`, `/batch-merge-prs`, and `/describe-codebase` skills plus all seven
agents as subagents.
```

Then find the sentence just below the second install block:

```
Then start a new session. The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr` and
`/batch-merge-prs`.
```

Replace it with:

```
Then start a new session. The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr`,
`/batch-merge-prs`, and `/describe-codebase`.
```

- [ ] **Step 3: Verify the edits landed**

Run:
```bash
grep -n "describe-codebase" README.md
```
Expected: at least three matches — the section heading/link, and the two install
blurbs.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): document the describe-codebase skill"
```

---

## Task 4: End-to-end structural verification

**Files:** none (verification only)

Confirm the skill is internally consistent and discoverable before opening a PR.
These are the "tests" for a prose deliverable.

- [ ] **Step 1: Verify the full file tree**

Run:
```bash
find skills/describe-codebase -type f | sort
```
Expected exactly:
```
skills/describe-codebase/SKILL.md
skills/describe-codebase/lenses/conventions.md
skills/describe-codebase/lenses/data.md
skills/describe-codebase/lenses/flow-trace.md
skills/describe-codebase/lenses/layering.md
```

- [ ] **Step 2: Verify every lens referenced in SKILL.md exists**

Run:
```bash
grep -oE 'lenses/[a-z-]+\.md' skills/describe-codebase/SKILL.md | sort -u | while read ref; do test -f "skills/describe-codebase/$ref" && echo "OK $ref" || echo "MISSING $ref"; done
```
Expected: every referenced path reports `OK` (no `MISSING`).

- [ ] **Step 3: Verify frontmatter is well-formed**

Run:
```bash
awk 'NR==1{if($0!="---"){print "BAD: no opening ---"; exit 1}} NR>1 && $0=="---"{print "OK: frontmatter closes at line " NR; exit 0}' skills/describe-codebase/SKILL.md
```
Expected: `OK: frontmatter closes at line N` (frontmatter opens on line 1 and
closes with a second `---`).

- [ ] **Step 4: Confirm no stray edits and a clean tree**

Run:
```bash
git status --short && git log --oneline master..HEAD
```
Expected: clean working tree (no unstaged/untracked changes from this work), and
the branch shows four commits — the spec, the lens files, the orchestrator, and
the README.

- [ ] **Step 5: Final review and PR (optional)**

The skill is complete. If finalizing, run the `review-pr` skill on this branch
for a self-review, then open a PR against `master` with a Conventional Commits
title (`feat(skills): add describe-codebase skill`) and a body summarizing the
three scopes and the read-only/opt-in-write guarantees. End with a confidence
indicator (🟢 / 🟡 / 🔴) per the repo convention.

---

## Notes for the implementer

- **Read-only is the core invariant.** The explorers must never edit; the
  orchestrator writes nothing except the one optional doc in Phase 3. If any
  step tempts you to "just fix" something the explorers noticed, don't — that's
  `review-pr`/`simplify-sweep`'s job, not this skill's.
- **`file:line` on every claim** is what makes the brief trustworthy. The lens
  prompts enforce it; keep it when editing.
- **Three lenses, not four.** Cross-cutting concerns (config, auth, error
  handling, logging) live inside the layering lens by design — don't split them
  into a fourth explorer.
- **Match the house voice.** The lens files and SKILL.md deliberately echo the
  tone and structure of `skills/review-pr/`. Read those before editing so new
  prose stays consistent.
```
