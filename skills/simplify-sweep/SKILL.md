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
  convergence or the round cap (see loop rules). On a whole-repo target this can
  run long: each round gates every fix and then re-surveys — say so before
  starting it so the user opts in knowingly.
- **(c) Stop** — report only; change nothing.

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
2. Re-run the full survey (Phases 1–3) on the now-updated target.
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
