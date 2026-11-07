---
name: plan
description: >-
  Break a feature or issue into small, verifiable tasks with acceptance
  criteria and dependency order, sliced vertically, and write the plan into
  the issue being developed. Use before writing code. Not for defining
  the problem (define) or implementing it (build).
---

# plan

Turn one request into a plan another agent can build task by task without
asking you anything. You read and write the plan; you never change code.

## Phase 0 — Orient

1. **Find the issue and read the Define output** in it (problem, scope in
   and out, done-criteria): `gh issue view <n> --comments`. The plan serves
   those done-criteria and stays inside that scope. No definition and the
   request is loose → ask for `define` first. No issue at all → write the
   plan to `PLAN.md` in the worktree root instead of inventing an issue
   number.
2. **Read project guidance** (`AGENTS.md`, `CLAUDE.md`, `README`,
   `CONTRIBUTING`): layering, conventions, the lint/test commands.
3. **Read the code the change touches** — enough to cite real files, not
   guesses.

## Phase 1 — Map the dependency graph

List the components the change touches and which depends on which (a schema
before the code that reads it; a helper before its callers). Note the
external contracts involved (public API, stored data) — changing one is a
decision for the user, so flag it in the plan instead of assuming.

## Phase 2 — Slice vertically

Each task is **one complete path** through the layers — entry point to
storage, including its test — that works and can be verified alone. Never
slice by layer ("all the models, then all the handlers"). Order tasks so
each depends only on earlier ones; a task that cannot be verified alone is
sliced wrong.

## Phase 3 — Write each task

Every task has:

- **Scope:** what this task covers, in one sentence.
- **Acceptance criteria:** observable behaviors, each checkable.
- **Verification:** the exact test or command that proves each criterion
  (name the test file and case, or the command and expected output). A
  criterion with no verification is rewritten until it has one.
- **Depends on:** earlier task numbers, or `none`.

## Phase 4 — Record it

Open the plan with a `## Progress` section: one checkbox per task in
dependency order (`- [ ] 1. <scope> — depends on: none`), then deferred
follow-ups apart. Under it, the task details, then open questions.

**Read-only caller.** When the invoking brief says you may not write (a
read-only planner role), write nothing: return the plan as your final
output, in the same format, for the caller to post.

Otherwise add the task list to the issue: a comment with `gh issue comment <n>
--body-file -`, or the issue body when the user asks for that. Report the
issue URL and the task count. Stop there; building starts when the user asks
for it.
