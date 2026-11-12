---
name: plan
description: >-
  Break a feature or issue into small, verifiable tasks with acceptance
  criteria and dependency order, sliced vertically, and write the plan into
  the issue being developed. Use before writing code. Not for defining
  the problem (define) or implementing it (build).
---

# plan

Break the work into small tasks that each end in something you can check, ordered so each one builds on finished work. Plan only: write no code.

## 1. Read

- The issue, its comments, and the `define` output if there is one. Its done-criteria are what the plan must reach.
- The code the work touches: the entry point, the layers a change passes through, the tests, and how they run. Name real files and functions in the plan.
- The problem is still loose (no clear done-criteria): say so and suggest `define` before going on.

## 2. Slice vertically

- Each task is one complete path through the layers it needs (say CLI → service → storage, plus its test), not one layer at a time.
- Small: one focused commit, reviewable on its own.
- Every done-criterion is covered by at least one task. Work outside the scope is not a task; list it under **Deferred**.

## 3. Write each task

```
### Task N: <short name>
Scope: what changes, in which files and functions.
Acceptance criteria:
- AC1: observable behavior → expected result
Verify: the exact command or test that shows each criterion passing.
Depends on: none | Task M
```

- Acceptance criteria are checkable from outside: a command, its input, the output you expect.
- Verification names a real command (`make test`, `python -m app list --done`), not "test it".

## 4. Order and track

- Order tasks by dependency. A task depends on another only if it cannot pass without it.
- Open the plan with a progress list that `build` ticks as it goes:

  ```
  ## Progress
  - [ ] Task 1: <name>
  - [ ] Task 2: <name> (depends on Task 1)
  ```

## 5. Record it

- Default: post the plan as an issue comment (`gh issue comment <n> --body-file <file>`).
- The user asked for the issue body: append it with `gh issue edit <n> --body-file <file>`, keeping the existing body.
- Told you are read-only, or a coordinator will post it: write no file and post nothing; return the plan as your answer.
- No issue: return the plan in the conversation and offer to file it.

## 6. Report

The issue URL, the number of tasks, and any risk or open question the plan depends on.
