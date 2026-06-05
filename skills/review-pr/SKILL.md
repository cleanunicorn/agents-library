---
name: review-pr
description: >-
  Review the work-in-progress on the current branch before it is finalized —
  the reviewer you start in a fresh agent after implementing a change. Orients
  on the project (AGENTS.md, README, conventions), computes the local branch
  diff, fans out specialized review sub-agents across nine quality domains
  (correctness, architecture, dead code, docs, refactor, testing, UX polish,
  security, conventions), consolidates and ranks their findings, presents them
  for you to pick from, and then either applies a chosen subset or runs an
  autonomous improve-until-converged loop. Use this whenever the user wants to
  review a PR, review a branch, review their changes before merging, "check what
  I just built", clean up a diff, or asks for a pre-merge / pre-PR review — even
  if they don't say the word "skill". Works on the local diff before a GitHub PR
  exists; no `gh` or remote required.
---

# review-pr

You are the **orchestrator** of a multi-domain review of the current branch.
The user has implemented a change and wants a fresh, thorough review before it
is finalized. Your job is to orient on the project, fan out nine specialized
review sub-agents, consolidate what they find, and help the user act on it.

The review target is always the **local branch diff** — everything on the
current branch that isn't yet in the main branch, plus any uncommitted
working-tree changes. This works before a GitHub PR exists; you never need `gh`
or a remote.

## Why this shape

A single reviewer reading a diff top-to-bottom misses things, because "is this
correct?", "does this fit the architecture?", and "is this tested?" are
different mental modes that compete for attention. Nine focused sub-agents, each
holding exactly one lens and the same shared project context, find more and
find it more sharply. You then merge their findings into one ranked list so the
user sees signal, not nine separate reports.

The sub-agents **only analyze** — they never edit code. Implementation happens
later, under your control, behind a lint/test gate. Keeping review and
implementation separate is what makes the findings trustworthy and the applied
changes safe.

## Phase 0 — Orient (do this once, yourself)

Before dispatching anything, build an accurate map of the project and the
change. You gather this **once** and bundle it into every sub-agent's prompt, so
the nine agents don't each re-derive the same context.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and any architecture notes. These tell you the layering,
   conventions, commit style, and quality bars the change will be judged
   against. If the project declares its own rules (commit format, confidence
   indicators, code-style bars), capture them verbatim — the conventions domain
   checks the diff against exactly these.
2. **Detect the main branch.** Don't hard-code `main` — detect it (e.g.
   `git symbolic-ref refs/remotes/origin/HEAD`, or fall back to whichever of
   `main`/`master` exists). Call it `<main>`.
3. **Compute the diff.** `git diff <main>...HEAD` for committed work, plus
   `git diff` and `git status` for uncommitted working-tree changes. The review
   target is the union. Capture the changed-file list.
4. **Find the commands that matter.** Detect how the project lints, formats,
   tests, and builds — from the docs first, then config files (package.json
   scripts, Makefile, pyproject, etc.). You'll need these for the gate in
   Phase 4. If you can't find them, you'll ask the user later rather than
   silently skipping verification.

If the branch is even with `<main>` and the working tree is clean, there's
nothing to review — say so and stop.

## Phase 1 — Fan out the review

Dispatch all nine domain sub-agents **in parallel** — issue all the Agent/Task
calls in a single message so they run concurrently. (This is the
`superpowers:dispatching-parallel-agents` pattern.)

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** you gathered in Phase 0: the project guidance summary,
   the detected conventions, the changed-file list, and the diff (or, for a
   large diff, the changed-file list plus instructions to read what it needs).
2. **The domain prompt** — read the matching file from `domains/` and include it
   verbatim. That file is the sub-agent's entire instruction set for what to
   look for.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; return findings in this exact
   schema, or an empty list if you find nothing worth raising.*

The nine domains and their files:

| Domain | Emoji | File | Looks for |
|--------|-------|------|-----------|
| Correctness | 🐛 | `domains/correctness.md` | Logic bugs, edge-case crashes, races, wrong behavior. **The only bug-hunting domain.** |
| Architecture | 🏗️ | `domains/architecture.md` | Does the change fit the project's structure, and is it coherent in itself. |
| Dead code | 🌲 | `domains/deadcode.md` | Code the diff leaves unused/unreachable; removable without behavior change. |
| Docs | 📝 | `domains/docs.md` | Missing or stale documentation the project expects for the changed surface. |
| Refactor | 🔧 | `domains/refactor.md` | Simplification, readability, DRY — without changing behavior. |
| Testing | 🧪 | `domains/testing.md` | Coverage gaps: happy paths, failure paths, edge cases. |
| UX polish | 🎨 | `domains/ux-polish.md` | User-experience friction (frontend projects; no-op otherwise). |
| Security | 🛡️ | `domains/security.md` | Auth guards, error/info leakage, secrets, input validation. |
| Conventions | 📐 | `domains/conventions.md` | The diff vs the project's own declared rules (AGENTS.md/CLAUDE.md). |

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole review on one domain.

## Phase 2 — Consolidate & present

Merge all findings into one list:

- **Deduplicate across domains.** The same location with the same fix collapses
  into one entry; keep the higher severity. (Several domains will legitimately
  flag the same line for different reasons — surface that once.)
- **Rank** by severity (🔴 → 🟡 → 🟢), then by domain.
- **Assign stable IDs** of the form `<domain>-<n>` (e.g. `correctness-1`).

Present a grouped, ID'd list to the user. Each finding renders on one line:

```
[correctness-1] 🔴 correctness · src/auth.ts:42 — token expiry uses `<` not `<=`,
                off-by-one lets expired tokens through — change to `<=` — small
```

Then summarize: how many findings at each severity, and which domains were
quiet. Keep it skimmable — the user is choosing what to act on, not reading
nine essays.

## Phase 3 — Decide

Ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop** — apply all significant findings, re-review, repeat
  until convergence or the round cap (see loop rules).
- **(c) Stop** — report only; change nothing.

## Phase 4 — Implement (for paths a and b)

For each accepted finding, in order:

1. **Apply the edit** to the working tree.
2. **Run the gate** — the project's lint and test commands from Phase 0.
3. **Hold the gate hard.** If lint or tests go red, fix it or revert that one
   finding. Never commit red. A review that breaks the build is worse than no
   review.
4. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`), scoped to the finding's domain.
   One commit per finding keeps the history reviewable and lets any single fix
   be reverted cleanly.

If you couldn't find the lint/test commands in Phase 0, ask the user for them
or whether to proceed without the gate — don't silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:        <domain>-<n>            e.g. correctness-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
domain:    <one of the nine>
location:  path:line
problem:   one-line description of what's wrong or missing
fix:       proposed change, concrete enough to act on
effort:    small | medium | large
```

## Autonomous loop rules (path b)

1. Apply every **significant** finding — severity 🔴 or 🟡. 🟢 findings are
   reported but not auto-applied (they're judgment calls the user should opt
   into). Each fix follows the Phase 4 apply-and-gate steps.
2. Re-run the full review fan-out (Phases 1–2) on the now-updated diff.
3. Repeat. **Stop** when either:
   - a review round produces no 🔴/🟡 findings (convergence), **or**
   - three apply-then-re-review rounds have completed (cost bound),
   whichever comes first.
4. Each round reports: findings applied, the gate result, and what remains. On
   stop, summarize total commits made and any 🟢 findings left for the user.

The loop is **stateless across invocations**: hitting the 3-round cap is not
the end of the road. Because each run re-orients and re-reviews from the current
diff, the user can simply re-invoke this skill to run another set of rounds on
the updated branch — a fresh run naturally continues where the last one stopped.
Mention this in the stop summary so the user knows it's an option.

## Error handling

- **No diff** (branch even with main, clean tree): report nothing to review and
  stop.
- **Lint/test command not found:** warn and ask the user whether to proceed
  without the gate or supply the command. Never silently skip verification.
- **A sub-agent fails or returns nothing:** note it, continue with the others.
- **A fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it "attempted, reverted — needs manual work," and continue with the rest.
- **Two findings' edits conflict:** one-commit-per-finding already serializes
  them; apply sequentially and re-run the gate after each.
