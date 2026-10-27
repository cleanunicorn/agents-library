---
name: simplify-sweep
description: >-
  Survey the repository, a path, or the branch diff for behavior-preserving
  simplifications — duplication, dead code, deep nesting, unclear names, stale
  docs — and optionally apply them behind the lint and test gate. Use to
  simplify, declutter, tidy, or reduce complexity. Never fixes bugs. Not for
  a full diff review (review-pr), explaining code (describe-codebase), or
  planning an unbuilt feature (plan-feature).
---

# simplify-sweep

You are the **orchestrator** of a simplification survey of code and docs, over
a target the user chooses: the whole repository, a path or glob, or the current
branch diff. Orient on the project, build and shard a scan surface, fan out
sub-agents across four lenses, consolidate, and help the user act on the
findings behind a lint/test gate.

Two properties frame everything below:

- **Every change is behavior-preserving.** This skill simplifies; it never fixes
  bugs or changes what the code does. A change that alters behavior is out of
  scope — note it and move on.
- **You never push or touch the remote.** All work is local: edits on the
  current branch, gated on lint and tests.

## Phase 0 — Orient

Gather this context **once** and bundle it into every sub-agent's prompt.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and architecture notes. Capture the layering, conventions,
   code-style bars, commit format, and confidence-indicator rules verbatim — the
   clarity/idiom and docs lenses are judged against exactly these.
2. **Detect the main branch** as `<main>`: `git symbolic-ref
   refs/remotes/origin/HEAD`, else whichever of `main`/`master` exists — never
   hard-code `main`.
3. **Resolve the target.** From the user's request:
   - nothing specified → the whole repository
   - a path or glob → just that subtree / matching files
   - "diff" / "my changes" / `--diff` → the current branch diff
     (`git diff <main>...HEAD`) plus staged and unstaged changes
     (`git diff --cached`, then `git diff`) and untracked files (`git status`)
   If it's ambiguous which they meant, ask before scanning.
4. **Find the commands that matter.** Detect how the project lints, formats,
   tests, and builds — docs first, then config. You need these for the Phase 6
   gate.

## Phase 1 — Build & shard the scan surface

1. **Enumerate** the files in the resolved target.
2. **Filter** out generated code, vendored dependencies, lockfiles, minified
   bundles, binaries, and the usual non-source directories (`node_modules`,
   `dist`, `build`, `vendor`, etc.). Respect `.gitignore`.
3. **Shard** the surviving files by directory/module into size-balanced shards,
   so one sub-agent sees a module's *intra-module* duplication.
4. **Cap** the fan-out at **~24** sub-agents (`4 lenses × shards`). If the
   surface is larger, cap it and **report what was left out** — never truncate
   silently. A `--diff` target is usually one shard.

If the target is empty after filtering, say there's nothing to scan and stop.

## Phase 2 — Fan out the survey

Dispatch one sub-agent per `(lens, shard)` pair concurrently, batching to the
host's concurrency limit.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only analysis, or inherit the session
model. Retry at the session tier only when required fields or assigned coverage
are missing.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance, conventions, and
   code-style bars.
2. **The lens's domain prompt** — read the matching file from `domains/` and
   include it verbatim — plus **this agent's shard file list**.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; read the files in your shard as you
   need; return findings in this exact schema, or an empty list. Every proposal
   must be behavior-preserving: never raise a behavior change, a public API,
   serialized field, or exported symbol an external contract depends on, and make
   each `fix` concrete and exact about preserving behavior. Calibrate to the
   project's own conventions and idioms, not personal preference.*

The four lenses and their files:

| Lens | Emoji | File | Looks for |
|------|-------|------|-----------|
| Redundancy & dead code | 🌲 | `domains/redundancy-deadcode.md` | Duplicated logic extractable to a helper; unused/unreachable code; redundant boolean logic. |
| Complexity & structure | 🔧 | `domains/complexity-structure.md` | Deep nesting → early returns; long mixed-responsibility functions; needless indirection / over-abstraction. |
| Clarity & idiom | ✨ | `domains/clarity-idiom.md` | Vague names; verbose constructs with a simpler idiom; over-broad/redundant types. |
| Docs simplification | 📝 | `domains/docs.md` | Duplicate docs; docs drifted from code; over-long prose; comments made redundant by clear code. |

If a sub-agent fails or returns nothing, note it and continue — never block the
survey on one shard or lens.

**Deletion is a finding, not a failure.** A whole capability that is machinery
for something nobody uses that way — a generalised model whose callers take one
path, an abstraction with a single implementation, a format nothing reads back —
is often the sweep's highest-value finding. Raise it as `kind:
removal-candidate`, with the line count it takes with it as `measured`. Removing
behaviour is not this skill's to *apply*: only `kind: simplification` records
enter implementation.

## Phase 3 — Consolidate

Merge all findings into one list:

- **Deduplicate** across lenses and shards: the same location with the same fix
  collapses into one entry, keeping the higher severity.
- **Cross-shard merge pass:** merge redundancy findings for the same pattern
  flagged in different shards. Intra-module duplication is caught reliably,
  cross-module duplication is best-effort; say so when it matters.
- **Rank** by severity (🔴 → 🟡 → 🟢), then by lens.
- **Assign stable IDs** of the form `<lens>-<n>` (e.g. `redundancy-1`, `docs-2`).

## Phase 4 — Present

Render a grouped, ID'd list to the user, one finding per line:

```
[redundancy-1] 🟡 redundancy · src/auth.ts:40 — token-decode block duplicated in
               session.ts:88 — extract a decodeToken() helper — small
               measured: 2 copies, 24 lines each; ~24 lines removable
```

Then summarize: findings per severity, which lenses were quiet, the **net lines
the accepted findings would remove**, and the **surface stats** from Phase 1 —
files scanned, shard count, anything skipped or capped. Keep it skimmable.

List any **removal candidates** (whole capabilities that look unused or
over-built) in their own short block below the findings, each with what it costs
to keep and what it would take with it.

## Phase 5 — Decide

If the request already chose a path ("report only", "apply the significant ones", "fix these IDs"), take it without asking; the request is the authorization. Otherwise ask the user to choose one:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop** — see *Autonomous loop rules*. On a whole-repo target
  each round gates every fix and re-surveys, so it can run long; say so before
  starting.
- **(c) Stop** — report only; change nothing.

## Phase 6 — Implement (paths a and b)

For each accepted finding, in order:

1. **Apply the edit** to the working tree.
2. **Fix every instance, not just the one found.** Search the whole
   repository for the same problem — its *shape*, not the literal text. Apply
   the same simplification wherever it is mechanical and safe, in the same
   commit, and record the search and its count (`N found · N fixed · N left`)
   in the commit body and in the round report. Two limits hold: the Phase 1
   exclusions apply to the sweep as well — never edit generated code, vendored
   dependencies, lockfiles, minified bundles, or binaries, which the scan
   surface filtered out for good reason; and instances outside the resolved
   target are reported with their count and edited only on the user's say-so —
   in the autonomous loop they are reported, never auto-applied. An instance
   needing judgement is listed for the user instead of forced. A finding fixed
   at one site while identical ones remain is not fixed.
3. **Run the gate** — the project's lint and test commands from Phase 0.
4. **Hold the gate hard.** If lint or tests go red, fix it or revert that one
   finding. Mark a revert `attempted, reverted — needs manual work`, then
   continue with the remaining findings. Never commit red.
5. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`, e.g. `refactor(auth): …`,
   `docs(readme): …`), scoped to the finding's lens.

Docs-only findings still run the gate (docs build/lint if the project has one).
If you couldn't find the lint/test commands in Phase 0, ask the user whether to
proceed without the gate — never silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:        <lens>-<n>            e.g. redundancy-1
kind:      simplification | removal-candidate
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
lens:      redundancy | complexity | clarity | docs
location:  path:line
problem:   one-line description of what is more complex than it needs to be
measured:  the size of the thing, in numbers (`4 near-identical copies, 31 lines
           each`; `nesting 5 deep`; `~180 lines removable`) — else `not measured`
fix:       proposed simplification, concrete enough to act on (behavior-preserving)
effort:    small | medium | large
```

## Autonomous loop rules (path b)

| Path | Apply | Stop when | Cap |
| --- | --- | --- | --- |
| b — significant | 🔴 and 🟡 | no 🔴/🟡 findings remain | 3 rounds |

Apply each finding through Phase 6, re-run Phases 1–3 on the updated target,
and repeat. 🟢 findings are reported, not auto-applied. Report each round's
fixes, gate, and remainder, then the total commits and the 🟢 findings left for
the user. The cap is per invocation: a later invocation re-surveys from the
updated target and continues where this one stopped — say so in the stop
summary.
