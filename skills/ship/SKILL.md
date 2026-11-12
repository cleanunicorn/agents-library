---
name: ship
description: >-
  Deliver finished work as the user specifies; by default push the branch,
  open a draft pull request that summarizes the changes and links the issue,
  follow CI until green, and mark it ready only when nothing is left open.
  Never merges unless asked. Use when the work is built, verified and
  reviewed. Not for reviewing it (review).
---

# ship

Deliver the branch the way the user asked. The default applies only to what they left unsaid.

## 1. Choose the delivery

| The user says | Do |
|---|---|
| nothing, or "open a PR" | the whole default: steps 2–6 |
| "just push", "no PR" | step 2 only, then report the branch |
| "leave it local" | push nothing and call no `gh`; report the branch and its commits |
| "keep it a draft" | steps 2–4 and 6; never mark it ready |
| "merge it" | the whole default, then merge once it is ready and green |

## 2. Check, then push

- On the main branch: stop. Never push to it, and never change it.
- Uncommitted changes: stop and ask. Don't commit work you haven't seen.
- Read the project's guidance (README, CONTRIBUTING, AGENTS.md, CLAUDE.md) for its PR title format and any release steps.
- `git push -u origin <branch>`.

## 3. Open a draft PR

- Find the issue from the branch name, the commits, or the conversation. None: say so and leave the link out.
- `gh pr create --draft --body-file <file>`, titled in the project's format, or as a Conventional Commit if it has none. The body:

  ```
  ## Summary
  What changed and why, in a few lines.
  ## Changes
  - one line per meaningful change
  ## Testing
  - `<test command>` → N passed at <short SHA>
  - each acceptance criterion: pass | fail
  Closes #n
  ```

  Copy the acceptance results from the verify report on the issue. If there is none, say so in the body.

## 4. Follow CI until green

- `gh pr checks <pr> --watch`. A failing check: read its log, fix the cause on this branch, run the tests locally, commit, push, and watch again.
- Stop after three fix attempts, or as soon as the failure lies outside this branch (a flaky runner, a broken main, a missing secret or permission). Report it; don't retry blindly.
- No CI configured: run the project's tests locally and use their result instead.

## 5. Mark ready

`gh pr ready` only when all of these hold:

- CI is green (or the local tests, with no CI) at the pushed head.
- The verify report has no failing acceptance criterion.
- Review left no unresolved critical or important finding.

Otherwise leave the PR a draft and name each blocker. The user saying "ship it" does not waive a known gap; report the gap and let them decide.

## 6. Report

- The PR URL, and whether it is a draft or ready.
- The CI result, and what you fixed to get there.
- Anything still open: failing checks, unmet criteria, unresolved findings.

Merge only when the user asked: `gh pr merge` after step 5 passes, using the project's merge method. Never force-push and never delete the branch unless told to.
