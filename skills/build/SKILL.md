---
name: build
description: >-
  Implement planned tasks one at a time, test first: write the failing test,
  make it pass with the minimum code, run the full suite, commit with a
  Conventional Commit. Use to implement a plan or fix a bug. Not for
  planning (plan) or checking the result (verify).
---

# build

Implement one task at a time, test first, and leave a green suite and one commit behind each task.

## 1. Before the first task

- Find the plan: the issue's plan comment or body, a `PLAN.md`, or the conversation. A bug report with no plan is one task: reproduce, then fix.
- Read the project's guidance for its test command, commit format, and branch convention.
- On the main branch: create a feature branch first. Never commit to main.
- Run the full suite once. Note anything already failing so you don't confuse it with your own breakage.

## 2. Per task: red, green, commit

1. **Read** the task's acceptance criteria and the code it touches.
2. **Red.** Write a test for the behavior the criteria describe and run it. Confirm it fails for the right reason: the missing behavior, not a typo or import error. For a bug, the test reproduces it.
3. **Green.** Write the minimum code that makes it pass. No extra features, options, or refactors the task didn't ask for.
4. **Suite.** Run the targeted tests while iterating, then the full suite. Everything that passed before must still pass.
5. **Tidy.** With the suite green, clean up names or duplication you just introduced, then run it again.
6. **Commit** the test and code together as one Conventional Commit: `feat(scope): …` for new behavior, `fix(scope): …` for a bug, `refactor:` and `test:` where they fit.
7. **Track.** The plan has a `## Progress` list: tick the task's box.

## 3. Rules

- Never delete, skip, or weaken an existing test to get green. If a test is wrong, say so and fix it in its own commit with the reason.
- Stay inside the task. A bug or cleanup you notice elsewhere goes in the report, not in this commit.
- Blocked, or the acceptance criteria turn out wrong or contradictory: stop, update the plan with what you found, and report. Don't widen the scope to get around it.
- Don't push or open a PR; that is `ship`.

## 4. Report

- Each task done, with its commit.
- The final suite result with counts, such as `make test → 14 passed`.
- Anything skipped, blocked, or noticed but left alone.
