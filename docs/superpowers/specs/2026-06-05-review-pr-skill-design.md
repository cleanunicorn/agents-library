# Design: `review-pr` skill

**Date:** 2026-06-05
**Status:** Approved (pending user spec review)

## Purpose

A Claude Code skill that reviews the work-in-progress on the current branch
before it is finalized. The user's workflow is: collaborate with Claude,
implement a change, then start a fresh agent whose job is to review what was
built. This skill is that reviewer.

It orients itself in the project, fans out specialized review sub-agents across
nine quality domains, consolidates their findings, presents them to the user,
and then either implements a chosen subset or runs an autonomous
improve-until-converged loop.

## Scope

- **In:** orienting on the project, computing the branch diff, parallel
  domain review, finding consolidation/ranking, user selection, applying fixes
  as commits, an autonomous improvement loop, a hard lint/test gate.
- **Out:** opening or interacting with GitHub PRs (`gh`); reviewing arbitrary
  commits or remote PRs; multi-branch/multi-PR fan-out. The review target is
  always the local branch diff.

## Packaging

Self-contained skill committed to this repository:

```
skills/review-pr/
  SKILL.md              # orchestrator
  domains/
    correctness.md      # logic bugs, edge-case crashes, races, wrong behavior
    architecture.md     # fit with project structure + internal coherence
    deadcode.md         # dead code to remove, behavior-preserving
    docs.md             # missing/stale docs the project expects
    refactor.md         # simplify, readability, DRY
    testing.md          # happy + failure + edge-case coverage gaps
    ux-polish.md        # UX friction (frontend projects)
    security.md         # auth, leakage, secrets, input validation
    conventions.md      # diff vs AGENTS.md/CLAUDE.md declared rules
```

The `domains/*.md` files are **review-mode** prompts written fresh for this
skill. They are NOT loaded from the existing `agents/*.md` definitions — those
are implement-and-open-PR agents. The review prompts mirror the same domain
knowledge but in analysis-only form: each returns findings and never edits
code. (Domain knowledge is duplicated deliberately, to decouple review from the
implement agents.)

## Review target

Always the local branch diff: everything on the current branch not yet in the
main branch (`git diff <main>...HEAD`, plus uncommitted working-tree changes if
present). No GitHub remote or `gh` auth required; works before a PR exists.

The main branch name is detected (e.g. `main` or `master`) rather than
hard-coded.

## Domains (9 review sub-agents)

| Domain | Emoji | Looks for |
|--------|-------|-----------|
| Correctness | 🐛 | Logic errors, edge-case crashes, races, wrong behavior. **The only bug-hunting domain** — the rest are behavior-preserving. |
| Architecture | 🏗️ | Does the change fit the project's established structure, and is it coherent in itself. |
| Dead code | 🌲 | Code the diff leaves unreachable/unused; removable without behavior change. |
| Docs | 📝 | Missing or stale documentation the project expects for the changed surface. |
| Refactor | 🔧 | Simplification, readability, DRY — without changing behavior. |
| Testing | 🧪 | Coverage gaps: happy paths, failure paths, edge cases. |
| UX polish | 🎨 | User-experience friction (frontend projects only; no-op otherwise). |
| Security | 🛡️ | Auth guards, error/info leakage, hardcoded secrets/config, input validation. |
| Conventions | 📐 | The diff vs the project's own AGENTS.md/CLAUDE.md declared rules (commit style, confidence indicators, code-style bars). |

## Flow

### Phase 0 — Orient (orchestrator, once)

1. Read AGENTS.md, README, and CLAUDE.md if present.
2. Detect the main branch and compute the diff (`git diff <main>...HEAD` plus
   any uncommitted changes).
3. Detect the project's lint/format/test/build commands (from docs or config).
4. Capture conventions and the changed-file list.

This context is gathered **once** and bundled into the prompt of every
sub-agent, so the nine agents do not each re-derive project context.

### Phase 1 — Fan out review

Dispatch all 9 domain sub-agents **in parallel** (one Agent/Task call each,
issued in a single message), in analysis-only mode. Each receives the bundled
context + diff and returns findings in the fixed schema below. Sub-agents MUST
NOT modify files.

(Use the `superpowers:dispatching-parallel-agents` pattern for the fan-out.)

### Phase 2 — Consolidate & present

The orchestrator merges all findings, deduplicates across domains (same
location + same fix collapses, keeping the higher severity), ranks by severity
then domain, and presents a grouped, ID'd list to the user.

### Phase 3 — Decide

The user chooses one of:

- **(a) Implement selected** — user names finding IDs to apply.
- **(b) Autonomous loop** — implement all significant findings, re-review,
  repeat (see loop rules).
- **(c) Stop** — report only, change nothing.

### Phase 4 — Implement

For each accepted finding:

1. Apply the edit to the working tree.
2. Run the project lint + test commands.
3. **Hard gate:** if lint/tests are red, fix or revert that finding. Never
   commit red.
4. Commit on the current branch — **one commit per finding**, Conventional
   Commits style (`<type>(<scope>): <subject>`), scoped to the finding's
   domain.

## Finding schema

Each finding is emitted by a sub-agent as a structured record:

```
id:        <domain>-<n>            e.g. correctness-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
domain:    <one of the 9>
location:  path:line
problem:   one-line description of what's wrong/missing
fix:       proposed change, concrete enough to act on
effort:    small | medium | large
```

Presented to the user as:

```
[correctness-1] 🔴 correctness · src/auth.ts:42 — token expiry uses `<` not `<=`,
                off-by-one lets expired tokens through — change to `<=` — small
```

## Autonomous loop rules

1. Implement every **significant** finding (severity 🔴 or 🟡; 🟢 are reported
   but not auto-applied) following the Phase 4 implement-and-gate steps.
2. Re-run the full review fan-out (Phase 1–2).
3. Repeat. **Stop** when either:
   - a review round produces no 🔴/🟡 findings (convergence), **or**
   - 3 implement-then-re-review rounds have completed (cost bound),
   whichever comes first.
4. Each round reports: findings applied this round, lint/test result, and what
   remains. On stop, summarize total commits made and any 🟢 findings left for
   the user.

The loop is **stateless across invocations**: hitting the 3-round cap is not
terminal. The user can simply re-invoke the skill to run another set of rounds
on the now-updated branch — each invocation re-orients and re-reviews from the
current diff, so a fresh run naturally continues where the last one stopped. On
stop, the summary tells the user this is an option.

## Error handling

- **No diff** (branch even with main): report nothing to review and stop.
- **Lint/test command not found:** warn, ask the user whether to proceed
  without the gate or supply the command. Do not silently skip verification.
- **A sub-agent fails/returns nothing:** note it, continue with the others;
  never block the whole review on one domain.
- **Fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it as "attempted, reverted — needs manual work," continue.
- **Merge conflict between two findings' edits:** apply sequentially (one
  commit per finding already enforces this); re-run the gate after each.

## Testing the skill

- Dry-run on a branch with a known planted bug → correctness domain surfaces
  it; confirm no files are edited in review-only mode.
- Selected-implement path → only chosen IDs become commits; gate runs; log
  shows one commit per finding.
- Autonomous loop → converges or stops at 3 rounds; never commits with red
  lint/tests; 🟢 findings reported, not applied.
- No-diff and missing-test-command branches → correct graceful handling.

## Open questions

None outstanding. All design forks resolved with the user:
self-contained packaging, local-diff target, commits-on-current-branch apply,
all 9 domains, max-3-rounds+convergence loop, one-commit-per-finding.
