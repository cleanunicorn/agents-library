---
name: batch-merge-prs
description: >-
  Merge a named list of GitHub pull requests onto one new local branch,
  skipping any already in main, then run the project's tests and review the
  merged branch. Use to batch, combine, or bulk-merge specific PRs into one
  branch. Requires `gh`; never pushes or closes PRs. Not for reviewing one
  PR (review-pr) or triaging issues (triage-issues).
---

# batch-merge-prs

Merge the user's PR list locally, test under the project's rules, review,
and report. These boundaries apply throughout:

- **The user's list is the selection.** Never add or drop a PR based on your
  quality judgement; tests and review assess quality after merging.
- **No GitHub writes:** never push, merge, close, or comment on remote PRs.
  Leave the local branch for the user.
- **Scripts own deterministic steps.** Run the scripts below and retain their
  ledgers rather than improvising classification, merges, or attribution.
  A `FATAL` stops that step: relay the error without destructive cleanup.
- **Herdr first:** when the host lists a `herdr` skill and
  `test "${HERDR_ENV:-}" = 1 && command -v herdr` passes, follow
  `references/herdr.md` for all agents and test commands, answering
  routine worker approvals per its § Approvals. Otherwise use native
  subagents and your shell; the same contracts hold.

Script paths below are relative to this skill; run from the target repository.

## Phase 0 — Orient

1. Take PR numbers or GitHub PR URLs from the request. Without a list, run
   `gh pr list --state open --json number,title,author,isDraft`, show them,
   and ask which to merge. Wait for the answer; never select for them.
2. Read `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING`, and `README` for branch,
   merge, and test rules, including suites safe to run unattended.
3. Identify the GitHub remote (usually `origin`) and classify:

   ```
   bash <skill>/scripts/check-prs.sh <remote> <pr-or-url>...
   ```

   Retain `MAIN <main>` and each PR's ledger: `IN_MAIN` with
   `merged-on-github <sha>`, `head-reachable <sha>`, or `patch-equivalent
   <sha>` evidence; `TODO <n> <head> <state>`; or `SKIPPED` with its reason
   (fetch failure, other repository, unparseable). Merge `TODO`s in user
   order, including `DRAFT` or `CLOSED` PRs, whose state belongs in the report.

No `TODO`s → report the ledger and stop.

## Phase 1 — Merge onto a local branch

Use the requested name, else `auto` for `batch/<YYYYMMDD-HHMM>`. Tell the
user if a named branch already exists: the script uses it as-is.

```
bash <skill>/scripts/merge-prs.sh <remote> <main> <target>|auto <n>...
```

The script requires a clean tree; if dirty, ask the user to commit or stash.
It creates a new branch from freshly fetched `<remote>/<main>` and merges
`--no-ff`, keeping each PR separately revertable. Retain `TARGET`,
`MERGED <n> <merge-sha>`, and `SKIPPED <n> <reason>`.

Conflicts are aborted and recorded as `SKIPPED <n> conflicts <files>`;
never resolve them yourself. Continue with the rest: independent PRs can
still land, and tests expose a dependency on a skipped PR.

Nothing merged → report and stop.

## Phase 2 — Test

Follow `references/test-gate.md`: discover commands from project guidance,
CI, then manifests; run authorized suites sequentially, log results, and
attribute failures to merge commits. Report unauthorized suites as skipped.

## Phase 3 — Review

Start one read-only reviewer using **review-pr**, report-only (Phase 4 path
*d*), against `<remote>/<main>`. Supply that base explicitly if local
`<main>` is behind: review-pr's `diff-target.sh` otherwise includes upstream
work in the batch diff. Its domain fan-out remains review-pr's responsibility.

Review and tip tests may run together because neither writes. Wait for the
reviewer before failure attribution, which checks out other commits. Report
a failed reviewer; never replace its verified findings with your own review.

## Phase 4 — Report

Return one ledger:

- **Branch:** `TARGET`, base `<remote>/<main>` and SHA, local and unpushed.
- **Merged:** each PR's number, title, and merge commit.
- **Skipped:** already-in-main evidence, or fetch/conflict reason and files.
- **Tests:** command, source, exit status, passed/failed counts; skipped suites
  and reasons; each failure's culprit PR, `pre-existing`, or `none`.
- **Review:** ranked verified findings and review-pr's filtered-out tally.
- **Approvals:** `<run-dir>/approvals.md` and its count of answered,
  relayed, and rejected prompts.
- **Next steps:** the user may inspect, fix or drop a culprit, push, or open
  a combined PR. Nothing on GitHub was changed.
