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

You are the **orchestrator** of a batch merge. The user names the pull
requests; you merge every one that main doesn't already contain onto a new
local branch, run the tests that branch needs under the project's own rules,
review the result, and report what landed, what was skipped, what failed, and
which PR broke it.

Three guardrails frame everything below:

- **The user's list is the selection.** Merge every listed PR that isn't
  already in main. Never add a PR, and never drop one on your own judgement of
  its quality — the tests and the review are where quality shows up.
- **You never touch the remote.** All merging is local. You do not push, and
  you do not merge, close, or comment on PRs on GitHub. The branch is left for
  the user.
- **Scripts own the deterministic steps.** Classifying PRs, merging, finding
  test commands, running them, and attributing failures each have a script in
  `scripts/`; run it and relay its ledger lines instead of improvising.

**Herdr.** When the host lists a `herdr` skill and `test "${HERDR_ENV:-}" = 1
&& command -v herdr` passes, every agent this skill starts and every test
command it runs goes through Herdr — follow `references/herdr.md`. Otherwise
start agents as native subagents and run tests in your own shell; every other
rule is the same.

## Phase 0 — Orient

1. **Get the list.** The PRs are numbers or GitHub PR URLs in the request. If
   none were given, run `bash scripts/list-prs.sh`, show the open PRs (number,
   title, author, draft), and ask which to merge. Do not pick for the user;
   stop here until they answer. A `FATAL` line from any script means `gh` is
   missing or unauthenticated, or the remote is unreachable — relay it and
   stop.
2. **Read the project's guidance** — `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING`,
   `README` — for the test commands, which suites are safe to run unattended,
   and any rule about branches or merges.
3. **Classify the list.** Note which remote points at GitHub (usually
   `origin`), then run:

   ```
   bash scripts/check-prs.sh <remote> <pr-or-url>...
   ```

   It prints `MAIN <main>`, then one line per PR: `IN_MAIN` with its evidence
   (`merged-on-github <sha>`, `head-reachable <sha>`, or `patch-equivalent
   <sha>`), `TODO <n> <head> <state>`, or `SKIPPED` (fetch failed, other
   repository, unparseable). The `TODO` PRs, in the order the user gave, are
   the merge list. Mention a `DRAFT` or `CLOSED` state in the report, but
   merge it — the user listed it.

If nothing is `TODO`, report the ledger and stop: there is nothing to merge.

## Phase 1 — Merge onto a new branch

The branch name is the user's if they gave one, otherwise `auto`, which the
script turns into `batch/<YYYYMMDD-HHMM>`. A named branch that already exists
is merged onto as-is; say so.

```
bash scripts/merge-prs.sh <remote> <main> <target>|auto <n>...
```

It refuses a dirty working tree (ask the user to commit or stash), creates the
branch from a freshly fetched `<remote>/<main>`, and merges each PR `--no-ff`
so each stays one revertable merge commit. Capture its ledger: `TARGET`,
`MERGED <n> <merge-sha>`, and `SKIPPED <n> <reason>`.

**Conflict policy:** a PR that conflicts is aborted, never half-resolved; its
conflicting files are recorded (`SKIPPED <n> conflicts <files>`) and the
remaining PRs still merge. The PRs are independent changes, so one conflict
is no reason to withhold the rest; a later PR that needed the skipped one
shows up in the Phase 2 tests. Never resolve a conflict yourself.

If nothing merged, report and stop.

## Phase 2 — Test the merged branch

Read `references/test-gate.md` and follow it. In short:
`scripts/test-commands.sh` lists the project's test sources in the order you
trust them — `AGENTS.md`/`CLAUDE.md` project section, `CONTRIBUTING`, CI
workflows, then build manifests — and flags lines that tie a suite to live or
shared resources. Run every suite the project expects for a change like this
batch through `scripts/run-gate.sh`; skip, and report as skipped, any suite
that needs an authorization the request didn't give. When a command fails,
`scripts/attribute-failure.sh` re-runs it at `<remote>/<main>` and at each
merge commit to name the PR that broke it.

## Phase 3 — Review the merged branch

Start one reviewer agent on the batch branch and have it run the
**review-pr** skill, report-only (its Phase 4 path *d*), on the batch
branch's diff from `<remote>/<main>`. review-pr's `diff-target.sh` diffs
against the local `<main>`; if that is behind `<remote>/<main>`, tell the
reviewer to diff against `<remote>/<main>` so work already merged upstream
isn't reviewed as part of the batch. The reviewer only reads; review-pr's own
domain fan-out is its business.

Start it while the Phase 2 suites run on the branch tip — neither writes —
but run `attribute-failure.sh` only after the reviewer finishes, because it
checks out other commits. If the reviewer fails, say so; do not substitute
your own review for its verified findings.

## Phase 4 — Report

One ledger:

- **Branch:** the `TARGET` name, cut from `<remote>/<main>` at `<sha>`, local
  and unpushed.
- **Merged:** each `#<n> — <title>` with its merge commit.
- **Skipped — already in main:** each PR with the `check-prs.sh` evidence.
- **Skipped — conflicts or fetch:** each PR with its reason and conflicting
  files.
- **Tests:** a table — command, source, exit status, passed/failed counts —
  then every suite skipped and why, and for each failure the culprit
  `attribute-failure.sh` named (`#<n>`, `pre-existing`, or `none`).
- **Review:** review-pr's verified findings, ranked, with its filtered-out
  tally.
- **Next steps:** inspect the branch, drop or fix a culprit PR, push it, or
  open a combined PR — the user's call. Nothing on GitHub was changed.
