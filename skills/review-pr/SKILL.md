---
name: review-pr
description: >-
  Review the current branch's local diff across ten quality domains, verify
  each finding, and optionally apply fixes behind the lint and test gate.
  Use to review a PR, branch, or "check what I just built" before merging.
  Not for whole-repo cleanup (simplify-sweep), visual design (review-design),
  conversion flows (review-ux-psychology), explaining code
  (describe-codebase), or planning an unbuilt feature (plan-feature).
---

# review-pr

## Overview

Review everything on the current branch that is not yet in the main branch,
including staged, unstaged, and untracked work, so it works before a PR exists
and without `gh` or a remote. Report only findings that survive an independent
re-check, and optionally fix them.

## When to use

Use before merging, or to check work you just finished. Not for whole-repo
cleanup (simplify-sweep), visual design (review-design), conversion flows
(review-ux-psychology), explaining code (describe-codebase), or planning an
unbuilt feature (plan-feature). If the branch matches main and the tree is
clean, say there is nothing to review and stop.

## What good looks like

Read the project's guidance (`AGENTS.md`, `CLAUDE.md`, `README`,
`CONTRIBUTING`) first; judge the diff against the project's own layering and
rules, not generic taste. Review in parallel where the host supports
delegation, otherwise locally, then have a fresh, skeptical agent re-check each
finding against the real code (not just the diff hunk) before you report it.
Drop what it refutes but list the dropped ones with a one-line reason; mark
what stays uncertain as unverified. Merge duplicates across domains and rank by
severity.

A finding is worth a maintainer's time when it has a location, a concrete fix,
a measurement (a value against a threshold, a count, never an adjective), and,
for a defect, the gap: what should have caught it and why it did not.

Domains and what each looks for:

- **Correctness** (the only bug-hunting domain): logic errors, edge cases,
  error paths, races, resource leaks, broken contracts, data integrity.
- **Architecture**: fit with the project's layering and wiring; internal
  coherence of the change.
- **Dead code**: code the diff leaves unused or unreachable, confirmed by a
  project-wide search (mind dynamic dispatch and public exports).
- **Docs**: missing or stale docs, calibrated to what the project already keeps.
- **Refactor**: behavior-preserving simplification, duplication, nesting,
  naming, toward the project's own style.
- **Testing**: untested happy, failure, and edge paths; weak assertions.
- **UX polish**: loading, empty, error, confirmation, keyboard, and
  accessibility gaps (frontend only).
- **Visual design**: hierarchy, spacing, type, contrast, dark mode, using the
  project's tokens (frontend only).
- **Security**: auth guards, leaked internals, secrets, input validation,
  sensitive logging; hygiene, not vulnerability research.
- **Conventions**: the diff against rules the project wrote down (commit
  format, style bars, required artifacts), nothing it did not.

## Boundaries

- Reviewers are read-only; only the fix step edits files, and only when asked.
- Never push or touch the remote.
- If the request already chose a path ("report only", "fix everything", "fix
  these"), take it. Otherwise ask whether to fix selected findings, fix
  everything, or stop.
- Fix each finding in its own commit (Conventional Commits, scoped to the
  domain). Apply the fix to every instance of the same problem by searching the
  repo for its shape, and report `N found / N fixed / N left`; instances
  outside the diff are reported, not edited, without the user's say-so.
  Close the finding's gap (widen the test or check) in the same commit.
- Run the project's lint and test commands before each commit and never commit
  red: fix it or revert that finding and note it needs manual work. If you
  cannot find the commands, ask rather than skip the gate.
- Never auto-apply unverified findings.

## Scripts

`bash scripts/diff-target.sh [main|files|diff]` computes the target without
hard-coding the main branch name.

- no argument: `MAIN <name>` then the changed-file list (committed vs main,
  staged, unstaged, untracked).
- `main`: the main branch name. `files`: the sorted changed-file list.
- `diff`: patches in order main to HEAD, HEAD to index, index to worktree.
  Partially staged files can have two patches; keep both. Untracked files have
  no patch, so read them.
- Exit with `FATAL` on stderr means no main branch was detected: ask which
  branch to diff against.

## Output

A grouped list ranked by severity, each finding with location, problem,
measurement, gap, fix, and verified or unverified status; then counts per
severity, quiet domains, and the filtered-out tally. After fixing, report
commits, the gate result, and what was left.
