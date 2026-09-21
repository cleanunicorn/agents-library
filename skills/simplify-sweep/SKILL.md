---
name: simplify-sweep
description: >-
  Survey the repository, a path, or the branch diff for behavior-preserving
  simplifications — duplication, dead code, deep nesting, unclear names, stale
  docs — and optionally apply them behind the lint and test gate. Use to
  simplify, declutter, tidy, or reduce complexity across a project. Never fixes
  bugs. Not for a full diff review (review-pr) or explaining code
  (describe-codebase).
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

## Phase 0 — Orient

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

Dispatch one sub-agent per `(lens, shard)` pair concurrently, batching to the
host's concurrency limit.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only analysis, or inherit the session
model. Retry at the session tier only when required fields or assigned coverage
are missing.

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

**Deletion is a finding, not a failure.** The lenses above hunt for code that
can be written more simply. Sometimes what a shard shows is that a whole
capability is elaborate machinery for something nobody uses that way — a
generalised model where the callers only ever take one path, an abstraction with
a single implementation, a format nothing reads back. Raise it. A finding whose
`fix` is *"delete this and the four things that exist to serve it"* is often the
highest-value one in the sweep, and it is the one a sub-agent told to "simplify"
will otherwise talk itself out of. Its `measured` field is the line count it
takes with it. Removing behaviour is out of this skill's remit to *apply* —
report it, size it, and mark it `kind: removal-candidate`. Only
`kind: simplification` records enter implementation.

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
               measured: 2 copies, 24 lines each; ~24 lines removable
```

Then summarize: how many findings at each severity, which lenses were quiet, the
**net lines the accepted findings would remove**, and the **surface stats** from
Phase 1 — files scanned, shard count, and anything skipped or capped. Keep it
skimmable; the user is choosing what to act on, not reading four reports.

List any **removal candidates** (whole capabilities that look unused or
over-built) in their own short block below the findings, each with what it costs
to keep and what it would take with it.

## Phase 5 — Decide

If the original request already chose a path — "report only", "apply the significant ones", "fix these IDs" — take that path without asking; the request is the authorization. Otherwise ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply. A finding may have
  identical instances elsewhere; Phase 6 sweeps for them, reports the count,
  and asks before editing anything outside the target you chose.
- **(b) Autonomous loop** — apply all significant findings, re-scan, repeat until
  convergence or the round cap (see loop rules). On a whole-repo target this can
  run long: each round gates every fix and then re-surveys — say so before
  starting it so the user opts in knowingly.
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

Docs-only findings still run the gate (docs build/lint if the project has one);
behavior preservation is trivial for them. If you couldn't find the lint/test
commands in Phase 0, ask the user whether to proceed without the gate — don't
silently skip verification.

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
