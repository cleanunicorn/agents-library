---
name: verify
description: >-
  Check finished work against its acceptance criteria: exercise each acceptance criterion
  end to end, record pass or fail, confirm every task was done, and list the
  gaps. Use after build and before review. Not for fixing gaps (build) or
  reading the diff for quality (review).
---

# verify

Prove the work does what the plan promised, by running it. Green tests are evidence, not proof: every acceptance criterion gets exercised the way a user would.

## 1. Collect

- The plan: its tasks, each task's acceptance criteria, and the `## Progress` list.
- The branch: `git log <main>..HEAD` and the diff, to see which tasks have commits.
- The project's test command, and how to run the app itself (CLI, server, script).

## 2. Run the suite

Run the full test suite once and record the command and its counts (`make test → 23 passed, 0 failed`). A red suite is a gap, but keep going: the criteria still need checking.

## 3. Exercise every criterion

For each acceptance criterion, in order:

1. Run the real thing: the CLI with real arguments, the endpoint with a real request, the function from a shell. Use the criterion's own verification command when the plan gives one.
2. Compare the actual output with the expected result.
3. Record **pass**, **fail**, or **not verified** (it could not be run, and why).

A criterion only passes on observed behavior. "The test covers it" or "the code looks right" is not verified. A flag that is accepted but has no effect fails.

## 4. Check the tasks

For every task, and especially every ticked box: find the commit or diff that implements it. A ticked task with no matching change is a gap. So is an unticked task whose work is done; note it so the box can be fixed.

## 5. Report

Post the report on the issue (`gh issue comment <n> --body-file <file>`), and give the same summary in the conversation:

```
## Verify report at <short SHA>
Suite: `<command>` → N passed, N failed

| AC | What was run | Expected | Actual | Result |
|---|---|---|---|---|
| AC1 | `python -m app sample.txt --limit 2` | 2 lines | 2 lines | pass |
| AC2 | … | … | … | fail |

Tasks: Task 1 ✓ <sha> · Task 2 ✓ <sha> · Task 3 ticked, no commit found

## Gaps
- each failing criterion, task without a commit, or red test, in one line
```

Write `Gaps: none` only when every criterion passed, every task has its change, and the suite is green.

## Rules

- Change nothing: no code, tests, commits, or ticked boxes. Fixing gaps is `build`'s job; reading the diff for quality is `review`'s.
- Don't stop at the first failure. Check everything, so the report lists every gap at once.
