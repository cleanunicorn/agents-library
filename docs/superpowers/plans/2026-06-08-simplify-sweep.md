# simplify-sweep Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `simplify-sweep` orchestrator skill for the agents-library plugin that surveys a target (whole repo, path/glob, or branch diff) for behavior-preserving simplification opportunities across four lenses and optionally applies them behind a lint/test gate.

**Architecture:** The skill is a set of markdown files following the existing `review-pr` skill's shape: a `SKILL.md` orchestrator plus one `domains/*.md` prompt per lens. The orchestrator (the model running the skill) orients on the project, builds and shards a scan surface, fans out read-only `lens × shard` sub-agents via the Agent/Task tool, consolidates and ranks findings, then applies chosen fixes behind the project's lint/test gate. Sub-agents only analyze; the orchestrator does all editing.

**Tech Stack:** Markdown (Claude Code plugin skill format with YAML frontmatter), git for branching/commits. No application code, no `gh`, no remote. "Tests" for this deliverable are **structural verification commands** (file existence, frontmatter validity, internal-reference resolution) since the artifact is prose, not code.

---

## File Structure

All paths relative to the repo root.

- Create: `skills/simplify-sweep/SKILL.md` — the orchestrator. Frontmatter (name + trigger-rich description) and the Phase 0–6 workflow.
- Create: `skills/simplify-sweep/domains/redundancy-deadcode.md` — lens 1 prompt.
- Create: `skills/simplify-sweep/domains/complexity-structure.md` — lens 2 prompt.
- Create: `skills/simplify-sweep/domains/clarity-idiom.md` — lens 3 prompt.
- Create: `skills/simplify-sweep/domains/docs.md` — lens 4 prompt.
- Modify: `README.md` — add a "Simplify Sweep Skill" section and list `/simplify-sweep` in the install blurbs.

No `plugin.json` / `marketplace.json` change: skills auto-discover from `skills/`.

**Build order:** domain files first (Task 1), so the SKILL.md references resolve when written (Task 2), then README (Task 3), then end-to-end verification (Task 4). Each task ends in its own commit on the `feat/simplify-sweep-skill` branch (already created and holding the design spec).

---

## Task 1: The four lens domain files

**Files:**
- Create: `skills/simplify-sweep/domains/redundancy-deadcode.md`
- Create: `skills/simplify-sweep/domains/complexity-structure.md`
- Create: `skills/simplify-sweep/domains/clarity-idiom.md`
- Create: `skills/simplify-sweep/domains/docs.md`

Each file is a self-contained sub-agent prompt in the same format as `skills/review-pr/domains/*.md`: a titled intro, **What to look for**, **What NOT to raise**, and **Output** (severity guidance + "Analysis only — never edit files. Empty list if …"). The intro is adapted from "reviewer for this diff" to "lens for the files in your shard" and stresses behavior preservation.

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p skills/simplify-sweep/domains
```

- [ ] **Step 2: Write `redundancy-deadcode.md`**

Create `skills/simplify-sweep/domains/redundancy-deadcode.md` with exactly:

```markdown
# Redundancy & dead code 🌲

You are the **redundancy & dead code** lens for the files in your shard. You
find two related things: logic that repeats and could collapse into one
well-named helper (DRY), and code that is unused or unreachable and can be
removed. Both make the code bigger than the behavior it delivers. Everything you
propose must be **behavior-preserving** — you reduce duplication and remove dead
weight, you never change what the code does.

Work from the files in your shard. For dead code, confirm with a project-wide
search that nothing references a thing before flagging it — code can be reached
dynamically (reflection, string dispatch, plugin registries) in ways a local
read won't show.

## What to look for

- **Duplicated logic** — the same block appearing two or more times, extractable
  into a well-named helper. Describe the duplicated pattern concretely (what it
  does, where you saw it).
- **Copy-pasted variants** — near-identical functions differing only by a
  constant or type, collapsible with a parameter.
- **Magic numbers/strings** repeated across the code that should be one named
  constant.
- **Redundant boolean logic** (`if cond: return True else: return False` →
  `return cond`), needless temporaries, double negatives.
- **Unused imports, variables, parameters** — declared but never read.
- **Unreachable / orphaned code** — branches that can't run, a function or file
  nothing imports, commented-out blocks left "just in case", stale TODO/FIXME
  for work already done.

> **Cross-shard note:** you only see your shard. If a duplicated block likely
> exists elsewhere in the project, say so in `problem` and describe the pattern
> precisely so the orchestrator can merge it with matches from other shards. Do
> not claim project-wide uniqueness you can't verify from your shard.

## What NOT to raise

- Anything that changes behavior — that is out of scope for every lens here.
- Code that only *looks* unused but is a public export, a dynamically dispatched
  handler, or a type used by the type checker. When unsure whether something is
  truly dead, say so rather than recommending removal.
- Over-engineering in the name of DRY: do not introduce an abstraction the
  codebase doesn't use just to remove a two-line repeat. Simpler beats cleverer.
- Migration/history directories and example-config files (those repeat
  deliberately).

## Output

Return findings in the orchestrator's schema. `problem` names the duplication or
dead code and its evidence (e.g. "same decode block in auth.ts and session.ts",
"no callers found in shard"); `fix` is the concrete extraction or removal and
must preserve behavior exactly. Severity is usually 🟢 (cleanup); raise to 🟡
for duplication that will actively bite maintenance or dead code that looks live
and misleads. Analysis only — never edit files. Empty list if your shard is
already lean.
```

- [ ] **Step 3: Write `complexity-structure.md`**

Create `skills/simplify-sweep/domains/complexity-structure.md` with exactly:

```markdown
# Complexity & structure 🔧

You are the **complexity & structure** lens for the files in your shard. You
find code that is harder to follow than the behavior requires: deep nesting,
functions doing too much, and indirection that adds layers without adding value.
Every change you propose must be **behavior-preserving** — you make the same
behavior easier to read, you never change it.

Simplify *toward* the project's established style — how it layers modules, how it
handles errors, how its well-built functions are shaped. Match the surrounding
code, never a personal preference.

## What to look for

- **Deep nesting** (>3 levels) that early returns / guard clauses would flatten.
- **Long functions with mixed responsibilities** that would be clearer split
  into named steps — only when the split is mechanical and obvious.
- **Needless indirection** — a wrapper, layer, or pass-through that exists for no
  reason and can be inlined without losing a seam the code actually uses.
- **Over-abstraction** — a pattern, base class, or generic mechanism with a
  single concrete user, where the direct form is plainly simpler.
- **Convoluted control flow** — redundant conditions, flags that could be
  structure, loops doing work that belongs outside them (without changing what
  runs).

## What NOT to raise

- Anything that changes behavior — that's a bug fix, not a simplification.
- Splitting a function purely to hit a line count, or extracting a helper used
  once that only adds a hop to read.
- Introducing new patterns, abstractions, or dependencies the codebase doesn't
  already use. Removing needless abstraction is in scope; adding it is not.
- Pure duplication or dead code (the redundancy lens) and pure renaming (the
  clarity lens) — overlap is fine; the orchestrator dedupes.

## Output

Return findings in the orchestrator's schema. `problem` names the structural cost
(what makes it hard to follow); `fix` is the concrete restructuring (which
guard clause, what to inline, where to split) and must preserve behavior
exactly. Keep each suggestion localized and reviewable. Severity is usually 🟡 or
🟢 — reserve 🟡 for complexity that actively impedes maintenance. Analysis only —
never edit files. Empty list if your shard is already clear.
```

- [ ] **Step 4: Write `clarity-idiom.md`**

Create `skills/simplify-sweep/domains/clarity-idiom.md` with exactly:

```markdown
# Clarity & idiom ✨

You are the **clarity & idiom** lens for the files in your shard. You find code
that works but reads poorly: vague names, verbose constructs that a simpler
language idiom would express, and types broader or more tangled than they need
to be. Every change you propose must be **behavior-preserving** — you make the
code say what it means, you never change what it does.

Calibrate to the project's own conventions and the idioms its language and
codebase already use. A precise name or idiom that matches the surrounding code
is the goal — not your personal preference.

## What to look for

- **Vague names** (`data`, `handle`, `process`, `result`, bare `id`, `tmp`) that
  a precise name would clarify — for what they are, not how they're built.
- **Verbose constructs** with a clearer idiomatic form in this language (a manual
  loop that's a built-in map/filter, a multi-line build-up that's one
  comprehension/expression) — only when the idiom is one the codebase uses.
- **Over-broad or redundant types** — a vague type where a concrete one is
  clearly intended, a redundant annotation, a union wider than the values it
  ever holds.
- **Double negatives, awkward conditionals, and needless ceremony** that a
  direct phrasing would make obvious.

## What NOT to raise

- Anything that changes behavior.
- Renaming public API endpoints, serialized field names, exported symbols, or
  anything an external contract depends on. Internal names only.
- Rewriting in an idiom the codebase doesn't use, or trading a clear explicit
  form for a clever one that's harder to read. Clarity is the goal, brevity is
  only the means.
- Structural splitting (the complexity lens) or documentation (the docs lens).

## Output

Return findings in the orchestrator's schema. `problem` names what's unclear and
the cost to the reader; `fix` is the concrete rename or idiomatic rewrite and
must preserve behavior exactly. Severity is usually 🟢 — raise to 🟡 only when
the unclarity is genuinely misleading (a name that implies the wrong thing).
Analysis only — never edit files. Empty list if your shard already reads
clearly.
```

- [ ] **Step 5: Write `docs.md`**

Create `skills/simplify-sweep/domains/docs.md` with exactly:

```markdown
# Docs simplification 📝

You are the **docs simplification** lens for the files in your shard. You find
documentation that has grown heavier or less true than it needs to be: the same
thing explained in two places, docs that have drifted from the code they
describe, over-long prose that could be tightened, and comments made redundant by
self-documenting code. Your job is to make the docs leaner and more accurate
without losing information a reader needs.

First check how this project documents things and match its style and density. A
terse codebase doesn't suddenly need essays, and a well-documented one shouldn't
lose its contracts. Calibrate to what's already here.

## What to look for

- **Duplicate documentation** — the same fact, setup step, or explanation
  maintained in two or more places that will drift apart; consolidate to one
  source of truth and point at it.
- **Drifted docs** — a comment, README line, or doc block that no longer matches
  the code it describes (renamed symbol, changed behavior, removed flag).
- **Over-long prose** — a paragraph or comment that says in ten lines what two
  would, with no loss of meaning.
- **Redundant comments** — a comment restating exactly what self-documenting code
  already says (`i += 1  # increment i`), or a stale TODO already done.

## What NOT to raise

- Removing documentation a reader genuinely needs (the *why* behind non-obvious
  code, a public contract, a config value's meaning). Tightening is in scope;
  stripping is not.
- Demands for new docs the project doesn't otherwise keep — don't impose a
  documentation culture the codebase hasn't adopted. (Missing docs are a
  different concern; this lens *simplifies* existing docs.)
- Code changes (the complexity/clarity lenses) — though noting "this comment is
  redundant because the code is clear" is fine.

## Output

Return findings in the orchestrator's schema. `problem` names the redundancy,
drift, or bloat and where it is; `fix` says what to consolidate, correct, or cut
and roughly to what. Severity: 🟡 when a doc is now wrong/misleading (drift), 🟢
for consolidation and tightening. Analysis only — never edit files. Empty list if
the docs in your shard are already lean and accurate.
```

- [ ] **Step 6: Verify all four files exist and are well-formed**

Run:
```bash
ls skills/simplify-sweep/domains/ && \
for f in redundancy-deadcode complexity-structure clarity-idiom docs; do \
  echo "== $f =="; \
  head -1 "skills/simplify-sweep/domains/$f.md"; \
  grep -c "## What to look for\|## What NOT to raise\|## Output" "skills/simplify-sweep/domains/$f.md"; \
done
```
Expected: all four files listed; each `head -1` prints a `# Title emoji` line; each grep count is `3` (all three required sections present).

- [ ] **Step 7: Commit**

```bash
git add skills/simplify-sweep/domains/
git commit -m "feat(simplify-sweep): add the four lens domain prompts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: The SKILL.md orchestrator

**Files:**
- Create: `skills/simplify-sweep/SKILL.md`

This is the orchestrator that drives the whole run. It mirrors `skills/review-pr/SKILL.md`'s structure, adapted to a sharded survey of an arbitrary target. The frontmatter description is trigger-rich (lists the phrasings that should activate it) in the same style as the existing skills.

- [ ] **Step 1: Write `SKILL.md`**

Create `skills/simplify-sweep/SKILL.md` with exactly:

````markdown
---
name: simplify-sweep
description: >-
  Survey a target — the whole repository, a path/glob, or the current branch diff
  — for behavior-preserving simplification opportunities, then optionally apply
  them. Orients on the project (AGENTS.md, README, conventions), builds and shards
  a scan surface, fans out parallel sub-agents across four simplification lenses
  (redundancy & dead code, complexity & structure, clarity & idiom, docs),
  consolidates and ranks their findings, presents them for you to pick from, and
  then either applies a chosen subset or runs an autonomous improve-until-converged
  loop — every applied fix gated on the project's lint and tests and
  behavior-preserving by construction. Use this whenever the user wants to simplify
  the codebase, find code or docs that can be simplified, reduce complexity,
  declutter or tidy a repo, find duplication / dead code / over-engineering, or
  survey the whole project (not just a diff) for cleanup opportunities — even if
  they don't say the word "skill". Works on the local branch; no `gh` or remote
  required.
---

# simplify-sweep

You are the **orchestrator** of a simplification survey. The user wants to find
code and docs that can be made simpler — across a target they choose: the whole
repository, a path or glob, or the current branch diff. Your job is to orient on
the project, build and shard a scan surface, fan out specialized sub-agents
across four simplification lenses, consolidate what they find, and help the user
act on it behind a lint/test gate.

Two properties frame everything below:

- **Every change is behavior-preserving.** This skill simplifies; it never fixes
  bugs or changes what the code does. A change that alters behavior is out of
  scope — note it and move on.
- **You never push or touch the remote.** All work is local: edits on the current
  branch, gated on lint and tests. No `gh`, no remote required.

## Why this shape

A single reader skimming a whole codebase for "things to simplify" misses most of
it, because "is this duplicated?", "is this too nested?", "is this name clear?",
and "is this doc stale?" are different mental modes that compete for attention.
Focused sub-agents, each holding exactly one lens over a bounded shard of files,
find more and find it more sharply. You then merge their findings into one ranked
list so the user sees signal, not a pile of reports.

The sub-agents **only analyze** — they never edit. Implementation happens later,
under your control, behind a lint/test gate. Keeping analysis separate from
action is what makes the findings trustworthy and the applied changes safe.

## Phase 0 — Orient (do this once, yourself)

Build an accurate map of the project, gathered once and bundled into every
sub-agent so they don't each re-derive it.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and architecture notes. Capture the layering, conventions,
   code-style bars, commit format, and confidence-indicator rules verbatim — the
   clarity/idiom and docs lenses are judged against exactly these.
2. **Detect the main branch.** Don't hard-code `main` — detect it
   (`git symbolic-ref refs/remotes/origin/HEAD`, or fall back to whichever of
   `main`/`master` exists). Call it `<main>`.
3. **Resolve the target.** From the user's request:
   - nothing specified → the whole repository
   - a path or glob → just that subtree / matching files
   - "diff" / "my changes" / `--diff` → the current branch diff
     (`git diff <main>...HEAD`) plus working-tree changes (`git diff`,
     `git status`)
   If it's ambiguous which they meant, ask before scanning.
4. **Find the commands that matter.** Detect how the project lints, formats,
   tests, and builds — docs first, then config (package.json scripts, Makefile,
   pyproject, etc.). You need these for the Phase 6 gate. If you can't find them,
   you'll ask the user later rather than silently skipping verification.

## Phase 1 — Build & shard the scan surface

This is what lets the survey scale to a whole repository instead of a small diff.

1. **Enumerate** the files in the resolved target.
2. **Filter** out what shouldn't be scanned: generated code, vendored
   dependencies, lockfiles, minified bundles, and binaries. Respect `.gitignore`
   and skip the usual non-source directories (`node_modules`, `dist`, `build`,
   `vendor`, etc.).
3. **Shard** the surviving files: group by directory/module into size-balanced
   shards so related code stays together. Grouping by module is what makes
   *intra-module* duplication detectable by a single sub-agent.
4. **Cap** the fan-out: choose the shard count so the total sub-agent count
   (`4 lenses × shards`) stays at or under **~24**. If the surface is larger than
   that allows, cap it and **report what was left out** — never truncate
   silently. For a `--diff` target the surface is usually small (one shard).

If the target is empty after filtering, say there's nothing to scan and stop.

## Phase 2 — Fan out the survey

Dispatch one sub-agent per `(lens, shard)` pair, **all in parallel** — issue the
Agent/Task calls in a single message so they run concurrently (the
`superpowers:dispatching-parallel-agents` pattern). If the pair count is large,
dispatch in batches to respect the concurrency limit.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance summary, the
   detected conventions and code-style bars.
2. **The lens's domain prompt** — read the matching file from `domains/` and
   include it verbatim — plus **this agent's shard file list**.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; read the files in your shard as you
   need; return findings in this exact schema, or an empty list if you find
   nothing worth raising.*

The four lenses and their files:

| Lens | Emoji | File | Looks for |
|------|-------|------|-----------|
| Redundancy & dead code | 🌲 | `domains/redundancy-deadcode.md` | Duplicated logic extractable to a helper; unused/unreachable code; redundant boolean logic. |
| Complexity & structure | 🔧 | `domains/complexity-structure.md` | Deep nesting → early returns; long mixed-responsibility functions; needless indirection / over-abstraction. |
| Clarity & idiom | ✨ | `domains/clarity-idiom.md` | Vague names; verbose constructs with a simpler idiom; over-broad/redundant types. |
| Docs simplification | 📝 | `domains/docs.md` | Duplicate docs; docs drifted from code; over-long prose; comments made redundant by clear code. |

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole survey on one shard or lens.

## Phase 3 — Consolidate

Merge all findings into one list:

- **Deduplicate** across lenses and shards: the same location with the same fix
  collapses into one entry, keeping the higher severity.
- **Cross-shard merge pass:** scan the redundancy findings for the same pattern
  flagged in different shards and merge them into one entry. This is best-effort
  recovery of duplication that spans shard boundaries — intra-module duplication
  is caught reliably, cross-module duplication is best-effort, and you should say
  so when it matters.
- **Rank** by severity (🔴 → 🟡 → 🟢), then by lens.
- **Assign stable IDs** of the form `<lens>-<n>` (e.g. `redundancy-1`, `docs-2`).

## Phase 4 — Present

Render a grouped, ID'd list to the user, one finding per line:

```
[redundancy-1] 🟡 redundancy · src/auth.ts:40 — token-decode block duplicated in
               session.ts:88 — extract a decodeToken() helper — small
```

Then summarize: how many findings at each severity, which lenses were quiet, and
the **surface stats** from Phase 1 — files scanned, shard count, and anything
skipped or capped. Keep it skimmable; the user is choosing what to act on, not
reading four reports.

## Phase 5 — Decide

Ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop** — apply all significant findings, re-scan, repeat until
  convergence or the round cap (see loop rules).
- **(c) Report only** — change nothing.

## Phase 6 — Implement (paths a and b)

For each accepted finding, in order:

1. **Apply the edit** to the working tree.
2. **Run the gate** — the project's lint and test commands from Phase 0.
3. **Hold the gate hard.** If lint or tests go red, fix it or revert that one
   finding. Never commit red. A simplification that breaks the build is worse
   than no simplification.
4. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`, e.g. `refactor(auth): …`,
   `docs(readme): …`), scoped to the finding's lens.

Docs-only findings still run the gate (docs build/lint if the project has one);
behavior preservation is trivial for them. If you couldn't find the lint/test
commands in Phase 0, ask the user whether to proceed without the gate — don't
silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:        <lens>-<n>            e.g. redundancy-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
lens:      redundancy | complexity | clarity | docs
location:  path:line
problem:   one-line description of what is more complex than it needs to be
fix:       proposed simplification, concrete enough to act on (behavior-preserving)
effort:    small | medium | large
```

## Autonomous loop rules (path b)

1. Apply every **significant** finding — severity 🔴 or 🟡. 🟢 findings are
   reported but not auto-applied (judgment calls the user should opt into). Each
   fix follows the Phase 6 apply-and-gate steps.
2. Re-run the full survey (Phases 1–2) on the now-updated target.
3. Repeat. **Stop** when either a survey round produces no 🔴/🟡 findings
   (convergence) or three apply-then-re-scan rounds have completed (cost bound),
   whichever comes first.
4. Each round reports: findings applied, the gate result, and what remains. On
   stop, summarize total commits and any 🟢 findings left for the user.

The loop is **stateless across invocations**: hitting the 3-round cap is not the
end of the road. Because each run re-orients and re-surveys from the current
state, the user can re-invoke this skill to run another set of rounds — a fresh
run naturally continues where the last one stopped. Mention this in the stop
summary.

## Error handling

- **Empty target** (no files after filtering): report nothing to scan and stop.
- **Lint/test command not found:** warn and ask whether to proceed without the
  gate or supply the command. Never silently skip verification.
- **A sub-agent fails or returns nothing:** note it, continue with the others.
- **A fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it "attempted, reverted — needs manual work," and continue with the rest.
- **Surface exceeds the agent cap:** cap it and disclose what was left out, so a
  partial survey never reads as a complete one.
- **Two findings' edits conflict:** one-commit-per-finding serializes them; apply
  sequentially and re-run the gate after each.
````

- [ ] **Step 2: Verify the frontmatter is valid and the name matches the directory**

Run:
```bash
head -1 skills/simplify-sweep/SKILL.md && \
grep -m1 '^name:' skills/simplify-sweep/SKILL.md && \
grep -q '^name: simplify-sweep$' skills/simplify-sweep/SKILL.md && echo "NAME OK"
```
Expected: first line is `---`; the `name:` line reads `name: simplify-sweep`; prints `NAME OK`.

- [ ] **Step 3: Verify every referenced domain file exists**

Run:
```bash
for f in $(grep -o 'domains/[a-z-]*\.md' skills/simplify-sweep/SKILL.md | sort -u); do \
  test -f "skills/simplify-sweep/$f" && echo "OK  $f" || echo "MISSING  $f"; \
done
```
Expected: four `OK` lines (`domains/clarity-idiom.md`, `domains/complexity-structure.md`, `domains/docs.md`, `domains/redundancy-deadcode.md`), no `MISSING`.

- [ ] **Step 4: Verify all seven workflow phases are present**

Run:
```bash
grep -c '^## Phase ' skills/simplify-sweep/SKILL.md
```
Expected: `7` (Phases 0 through 6).

- [ ] **Step 5: Commit**

```bash
git add skills/simplify-sweep/SKILL.md
git commit -m "feat(simplify-sweep): add the orchestrator SKILL.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: README section and install blurbs

**Files:**
- Modify: `README.md` — add a "Simplify Sweep Skill" section after the "The Batch PR Merge Skill" section; add `/simplify-sweep` to the two install blurbs that list the skills.

- [ ] **Step 1: Add `/simplify-sweep` to the plugin-install blurb**

In `README.md`, find:
```
This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr` and `/batch-merge-prs` skills plus all seven agents as subagents.
```
Replace with:
```
This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr`, `/batch-merge-prs`, and `/simplify-sweep` skills plus all seven
agents as subagents.
```

- [ ] **Step 2: Add `/simplify-sweep` to the "start a new session" blurb**

In `README.md`, find:
```
The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr` and
`/batch-merge-prs`.
```
Replace with:
```
The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr`,
`/batch-merge-prs`, and `/simplify-sweep`.
```

- [ ] **Step 3: Add the "Simplify Sweep Skill" section**

In `README.md`, find the start of the next section after the batch-merge description:
```
## The Agents
```
Insert this block immediately *before* that `## The Agents` line:
```
## The Simplify Sweep Skill

[`simplify-sweep`](skills/simplify-sweep/SKILL.md) surveys a target you choose —
the whole repository, a path/glob, or the current branch diff — for
**behavior-preserving** simplification opportunities. It orients on the project,
builds and shards a scan surface (so a whole-repo scan stays tractable), and fans
out parallel sub-agents across four lenses (redundancy & dead code, complexity &
structure, clarity & idiom, and docs simplification). It consolidates and ranks
their findings into one list, presents them for you to pick from, and then either
applies a chosen subset or runs an autonomous improve-until-converged loop —
every applied fix gated on the project's lint and tests and behavior-preserving
by construction. It's the whole-codebase counterpart to `review-pr`'s
diff-scoped review. No `gh` or remote required.

```

- [ ] **Step 4: Verify the edits landed**

Run:
```bash
grep -c '/simplify-sweep' README.md && \
grep -q '## The Simplify Sweep Skill' README.md && echo "SECTION OK" && \
grep -q '## The Agents' README.md && echo "AGENTS HEADING INTACT"
```
Expected: the count is `3` (two blurbs + the section link), `SECTION OK`, and `AGENTS HEADING INTACT`.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(readme): document the simplify-sweep skill

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: End-to-end structural verification

**Files:** none created or modified — this task only verifies the assembled skill.

- [ ] **Step 1: Confirm the full file layout**

Run:
```bash
find skills/simplify-sweep -type f | sort
```
Expected exactly:
```
skills/simplify-sweep/SKILL.md
skills/simplify-sweep/domains/clarity-idiom.md
skills/simplify-sweep/domains/complexity-structure.md
skills/simplify-sweep/domains/docs.md
skills/simplify-sweep/domains/redundancy-deadcode.md
```

- [ ] **Step 2: Confirm the new skill matches the existing skills' frontmatter shape**

Run:
```bash
for s in review-pr batch-merge-prs simplify-sweep; do \
  echo "== $s =="; \
  head -1 "skills/$s/SKILL.md"; \
  grep -m1 '^name:' "skills/$s/SKILL.md"; \
  grep -m1 'description:' "skills/$s/SKILL.md"; \
done
```
Expected: all three start with `---`, have a `name:` matching their directory, and a folded `description: >-`. The new skill is structurally indistinguishable from the existing two.

- [ ] **Step 3: Confirm the lens table and the schema agree on the four lens keys**

Run:
```bash
grep -o 'domains/[a-z-]*\.md' skills/simplify-sweep/SKILL.md | sort -u && \
grep -A1 '^lens:' skills/simplify-sweep/SKILL.md
```
Expected: the four domain paths, and the schema `lens:` line listing `redundancy | complexity | clarity | docs` — one key per domain file, no orphans.

- [ ] **Step 4: Confirm the branch holds a clean, reviewable history**

Run:
```bash
git log --oneline master..HEAD
```
Expected: four commits — the design spec, the domain prompts, the SKILL.md, and the README — each scoped to one concern.

- [ ] **Step 5: Final confirmation**

No commit needed (verification only). The skill is complete: orchestrator + four lenses + docs, on `feat/simplify-sweep-skill`, ready for a `review-pr` pass or a PR.

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- Runtime target (whole repo / path / `--diff`) → SKILL.md Phase 0 step 3 (Task 2).
- Output mode (report + optional apply, mirror review-pr) → Phases 4–6 (Task 2).
- Four lenses → the four domain files (Task 1) + the Phase 2 table (Task 2).
- Behavior-preserving + lint/test gate → stated in every domain file (Task 1) and Phase 6 (Task 2).
- Sharded fan-out + agent cap + disclosure → Phase 1 (Task 2).
- Cross-shard duplication best-effort + documented → redundancy-deadcode.md "Cross-shard note" (Task 1) and Phase 3 merge pass (Task 2).
- Fresh self-contained domain files → Task 1.
- Name `simplify-sweep` → frontmatter (Task 2).
- Finding schema, loop rules, error handling → Task 2.
- Files & registration (no manifest edit) + README section → Task 3; auto-discovery confirmed in File Structure.
- Out-of-scope (no push/PR, no bug fixing, no agent dispatch) → encoded in SKILL.md intro and domain "What NOT to raise" sections.

**2. Placeholder scan** — no TBD/TODO; every file's full content is inline; every verification step has an exact command and expected output. Clear.

**3. Type/name consistency** — lens keys `redundancy | complexity | clarity | docs` are identical across the schema, the Phase 2 table, the domain filenames, and the ID examples (`redundancy-1`, `docs-2`). Emojis 🌲/🔧/✨/📝 match between each domain file's title and the SKILL.md table. The `feat/simplify-sweep-skill` branch and `master` base are consistent throughout.
