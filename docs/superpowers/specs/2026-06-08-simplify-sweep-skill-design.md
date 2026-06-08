# simplify-sweep — design

**Status:** approved for planning
**Date:** 2026-06-08
**Repo:** agents-library (Claude Code plugin marketplace)

## Summary

`simplify-sweep` is a new orchestrator skill for the agents-library plugin. It
surveys a target — the whole repository, a path/glob, or the current branch diff
— for **behavior-preserving** simplification opportunities across four lenses,
consolidates them into one ranked list, and then either applies a chosen subset
or runs an autonomous improve-until-converged loop, every applied fix gated on
the project's lint and tests.

It is the whole-repository counterpart to `review-pr`: where `review-pr` reviews
a branch diff across nine quality domains, `simplify-sweep` surveys an
arbitrarily large target across four simplification-specific lenses, using a
sharded fan-out so a repo-wide scan stays tractable.

## Why this skill

The library already reviews a diff (`review-pr`) and batch-merges PRs
(`batch-merge-prs`), and it has single-purpose agents that each make one change
per run (`refactor`, `deadwood`, `docbot`). What is missing is a skill that
**surveys an entire codebase** for simplification opportunities and ranks them.
`review-pr` cannot do this — it is diff-scoped by design. The single-purpose
agents act one change at a time and do not survey. `simplify-sweep` fills that
gap.

## Design decisions (resolved during brainstorming)

1. **Scan target is chosen at runtime** — whole repo (default), a path/glob, or
   `--diff` (the current branch diff plus working-tree changes).
2. **Output mode mirrors `review-pr`** — produce a ranked report, let the user
   pick finding IDs (or an autonomous loop), and apply each behind a hard
   lint/test gate, one commit per fix. A report-only path also exists.
3. **Four simplification lenses**, each a parallel sub-agent domain:
   - redundancy & dead code (code)
   - complexity & structure (code)
   - clarity & idiom (code)
   - docs simplification (docs)
4. **All code changes are behavior-preserving** (the `refactor` agent's rule).
   The apply phase holds a hard lint/test gate; red is never committed.
5. **Fan-out is sharded** (`lens × shard`) so a whole-repo target scales. This
   is the one genuinely new problem versus `review-pr`, whose diff target is
   naturally bounded.
6. **Cross-shard duplication is best-effort, by design and accepted.** Sharding
   by module catches intra-module duplication reliably; duplication spanning two
   shards can be missed. A cross-shard merge pass in consolidation catches some
   of it. This limitation is documented in the skill rather than hidden.
7. **Fresh, simplification-tuned domain files.** They deliberately overlap with
   `review-pr`'s `refactor.md`/`deadcode.md`/`docs.md`, but are written fresh and
   self-contained because skills should not reach across each other and because
   the lenses are re-cut (e.g. "redundancy & dead code" merges what `review-pr`
   splits into two domains).
8. **Name:** `simplify-sweep`. Bare `simplify` collides with the built-in
   `/simplify`; `-sweep` matches the repo's verb-noun, repo-survey framing.

## Architecture

A single orchestrator (the skill) drives the whole run. It dispatches read-only
sub-agents that **only analyze** — they never edit. All editing happens later,
in the orchestrator, behind the lint/test gate. Keeping analysis separate from
action is what makes the findings trustworthy and the applied changes safe. This
is the same separation `review-pr` and `batch-merge-prs` use.

### Phase 0 — Orient (once, by the orchestrator)

- Read the project's guidance (`AGENTS.md`, `README`, `CLAUDE.md`,
  `CONTRIBUTING`, architecture notes). Capture conventions, code-style bars,
  commit format, and confidence-indicator rules verbatim — the clarity/idiom and
  docs lenses are judged against exactly these.
- Detect the main branch (`git symbolic-ref refs/remotes/origin/HEAD`, falling
  back to whichever of `main`/`master` exists). Call it `<main>`.
- Resolve the **target argument**:
  - none → whole repository
  - a path or glob → just that subtree/match
  - `--diff` → the current branch diff (`git diff <main>...HEAD`) plus
    `git diff`/`git status` working-tree changes (reuse `review-pr`'s
    computation)
- Find the lint/format/test/build commands (docs first, then config files) for
  the Phase 6 gate. If not found, ask the user later rather than silently
  skipping verification.

### Phase 1 — Build & shard the scan surface (new vs. `review-pr`)

- **Enumerate** the files in the resolved target.
- **Filter** out generated/vendored/lockfiles/minified/binary files; respect
  `.gitignore` and skip the usual non-source dirs (`node_modules`, `dist`,
  `build`, `vendor`, etc.).
- **Shard** the surviving files: group by directory/module into size-balanced
  shards so related code stays together (this is what makes intra-module
  duplication detectable).
- **Cap** shard count so total sub-agents (`4 lenses × shards`) stays under a
  ceiling (~24). If the surface is larger than the cap allows, cap it and
  **report what was left out** — files scanned, shard count, and anything
  skipped or capped. No silent truncation.
- For a `--diff` target the surface is the changed files only — usually a single
  shard.

### Phase 2 — Fan out `lens × shard` in parallel

Dispatch one sub-agent per `(lens, shard)` pair, all in parallel (the
`superpowers:dispatching-parallel-agents` pattern), batched to respect the
concurrency cap. Each sub-agent's prompt has three parts:

1. **Shared context** from Phase 0 — project guidance summary, detected
   conventions/code-style bars.
2. **The lens's domain prompt** — read the matching file from `domains/` and
   include it verbatim — plus this agent's **shard file list**.
3. **The output contract** — the finding schema below, with: *analysis only; do
   not modify any files; read the files in your shard as needed; return findings
   in this exact schema, or an empty list if you find nothing.*

The four lenses and their files:

| Lens | Emoji | File | Looks for |
|------|-------|------|-----------|
| Redundancy & dead code | 🌲 | `domains/redundancy-deadcode.md` | Duplicated logic extractable to a helper; unused/unreachable code the simplification leaves behind; redundant boolean logic. |
| Complexity & structure | 🔧 | `domains/complexity-structure.md` | Deep nesting → early returns; long mixed-responsibility functions; needless indirection / over-abstraction that can be inlined. |
| Clarity & idiom | ✨ | `domains/clarity-idiom.md` | Vague names; verbose constructs with a simpler language idiom; over-broad/redundant types. Behavior-preserving only. |
| Docs simplification | 📝 | `domains/docs.md` | The same thing documented in 2+ places; docs drifted from the code; over-long prose; docs made redundant by self-documenting code. |

If a sub-agent fails or returns nothing, note it and continue with the others.

### Phase 3 — Consolidate

- **Dedup** across both lenses and shards: same location + same fix collapses to
  one entry, keeping the higher severity.
- **Cross-shard merge pass:** scan the redundancy findings for the same pattern
  flagged in different shards and merge them — this is the best-effort recovery
  of cross-shard duplication noted in decision 6.
- **Rank** by severity (🔴 → 🟡 → 🟢), then by lens.
- **Assign stable IDs** of the form `<lens>-<n>` (e.g. `redundancy-1`,
  `docs-2`).

### Phase 4 — Present

Render a grouped, ID'd list, one finding per line (same render as `review-pr`):

```
[redundancy-1] 🟡 redundancy · src/auth.ts:40 — same token-decode block
               duplicated in session.ts:88 — extract a decodeToken() helper — small
```

Then summarize: counts per severity, which lenses were quiet, and the **surface
stats** from Phase 1 (files scanned, shards, anything skipped/capped). Keep it
skimmable.

### Phase 5 — Decide

Ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop** — apply all significant findings, re-scan, repeat
  until convergence or the round cap.
- **(c) Report only** — change nothing.

### Phase 6 — Implement (paths a and b)

For each accepted finding, in order:

1. **Apply the edit** to the working tree.
2. **Run the gate** — the project's lint and test commands from Phase 0.
3. **Hold the gate hard.** If lint or tests go red, fix it or revert that one
   finding. Never commit red.
4. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`), scoped to the finding's lens.

Docs-only findings still run the gate (e.g. docs build/lint if present);
behavior preservation is trivial for them. If lint/test commands were not found
in Phase 0, ask the user whether to proceed without the gate — never silently
skip verification.

## Finding schema

```
id:        <lens>-<n>            e.g. redundancy-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
lens:      redundancy | complexity | clarity | docs
location:  path:line
problem:   one-line description of what is more complex than it needs to be
fix:       proposed simplification, concrete enough to act on
effort:    small | medium | large
```

## Autonomous loop rules (path b)

1. Apply every **significant** finding — severity 🔴 or 🟡. 🟢 findings are
   reported but not auto-applied. Each fix follows the Phase 6 apply-and-gate
   steps.
2. Re-run the full scan fan-out (Phases 1–2) on the now-updated target.
3. Repeat. **Stop** when either a scan round produces no 🔴/🟡 findings
   (convergence) or three apply-then-re-scan rounds have completed (cost bound).
4. Each round reports findings applied, the gate result, and what remains. The
   loop is **stateless across invocations** — re-invoking the skill continues
   where the last run stopped; mention this in the stop summary.

## Error handling

- **Empty surface** (no files in target after filtering): report nothing to scan
  and stop.
- **Lint/test command not found:** warn and ask whether to proceed without the
  gate. Never silently skip verification.
- **A sub-agent fails or returns nothing:** note it, continue with the others.
- **A fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it "attempted, reverted — needs manual work," continue with the rest.
- **Surface exceeds the agent cap:** cap and disclose what was left out.

## Files & registration

```
skills/simplify-sweep/SKILL.md
skills/simplify-sweep/domains/redundancy-deadcode.md
skills/simplify-sweep/domains/complexity-structure.md
skills/simplify-sweep/domains/clarity-idiom.md
skills/simplify-sweep/domains/docs.md
```

Skills auto-discover from `skills/`, so no `plugin.json`/`marketplace.json` edit
is required. The `README.md` gains a "Simplify Sweep Skill" section in the same
style as the existing two skill sections.

## Out of scope (YAGNI)

- Pushing, opening PRs, or any remote interaction (the skill works on the local
  branch, like `review-pr`).
- Bug fixing or any behavior change — that is explicitly excluded; this skill
  only simplifies behavior-preservingly.
- Dispatching the single-purpose agents (a separate skill idea; not this one).
- Exhaustive cross-shard duplication detection (best-effort only, by decision).
