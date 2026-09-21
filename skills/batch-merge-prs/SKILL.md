---
name: batch-merge-prs
description: >-
  Triage open GitHub pull requests and batch-merge the trivial ones locally
  onto one branch. Use to sweep, bulk-merge, or clean up the PR queue, or collect the
  low-risk PRs onto one branch. Requires `gh`; never pushes or closes PRs.
  Not for reviewing one PR (review-pr) or triaging issues (triage-issues).
---

# batch-merge-prs

You are the **orchestrator** of a triage-and-batch-merge sweep over the
project's open pull requests. The user wants to find the trivial, low-risk PRs
sitting in the queue and collect the ones they choose onto a single branch they
name — without hand-reviewing each one and without touching the remote.

Your job: list the open PRs, fan out one review sub-agent per PR, consolidate
their include/skip verdicts into one ranked list, let the user pick, then
**locally** git-merge the chosen PRs into the target branch and summarize what
happened.

Two guardrails frame everything below:

- **You never decide what merges.** The sub-agents *recommend*; the user
  *confirms*. Nothing is merged until the user names the PRs to take.
- **You never touch the remote.** All merging is local. You do not push, and you
  do not merge or close PRs on GitHub. The user inspects the resulting branch and
  decides what to do with it.

## Phase 0 — Orient

Before dispatching anything, build the picture you'll bundle into every
sub-agent so the agents don't each re-derive it.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`. These tell you the conventions, commit style, and quality bars
   a PR should respect — the same bars the per-PR reviewer judges against. Capture
   a short summary to pass along.
2. **Run the listing script.** `bash scripts/list-prs.sh` verifies `gh` is
   installed and authenticated (a `FATAL` line and non-zero exit if not — stop
   and relay it; this skill cannot run without `gh`), then prints two sections:
   the detected main branch (call it `<main>`) and the open-PR JSON work list.
   Capture both. Note which remote points at GitHub (usually `origin`); you'll
   fetch PR heads from it. Skip drafts by default (mention you did); the user
   can ask to include them.
3. **Find the commands that matter (optional but useful).** Detect how the
   project lints/tests/builds, from the docs first then config. You'll offer to
   run these once on the final batched branch as a sanity check in Phase 5.

If there are no open PRs (or only drafts and the user didn't ask for those), say
so and stop — there's nothing to triage.

## Phase 1 — Fan out the triage

Dispatch one sub-agent per open PR concurrently, batching to the host's limits.
For a large queue (say >15 open PRs), tell the user the count and confirm before
fanning out that wide.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only assessments, or inherit the
session model. Retry at the session tier only when required verdict fields or
assigned coverage are missing.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance summary, the
   detected conventions, and `<main>`.
2. **The assessment lens** — read `references/pr-assessment.md` and include it
   verbatim. That file is the sub-agent's entire instruction set for how to judge
   a PR. Also give it the one PR's number and its row from the `gh pr list` JSON.
3. **The output contract** — the verdict schema below, with the instruction:
   *assessment only; do not merge, check out, or edit anything; gather the PR's
   diff and metadata yourself with `gh`; return exactly one verdict in this
   schema.*

The sub-agent fetches its own PR's diff (`gh pr diff <n>`) and details
(`gh pr view <n> --json ...`, including `mergeable`, `mergeStateStatus`, and CI
via `statusCheckRollup`) so the orchestrator prompt stays small and the work
parallelizes cleanly.

If a sub-agent fails, note that PR as "not assessed" and continue with the rest —
never block the whole sweep on one PR.

## Phase 2 — Consolidate & present

Collect the verdicts into one decision table, sorted **include candidates first**
(by ascending risk), then skips, then any that failed to assess. Render each PR
on a compact line:

```
[#142] ✅ include · trivial · docs · +6/-2, 1 file · clean, CI green
       — README typo fixes, no code paths touched
[#137] ⚠️ review · borderline · deps · +1/-1, 1 file · clean, CI green
       — bumps lodash minor; low risk but touches a runtime dep
[#131] ❌ skip · not-trivial · core · +210/-44, 9 files · CONFLICTS with base
       — refactors the auth flow; needs a real review, not a batch merge
```

Then summarize: how many PRs are include candidates, how many borderline, how
many to skip, and call out anything that conflicts with its base or has
**red/pending CI** — those are the ones most likely to bite during the merge.

Keep it skimmable. The user is making a pick from a table, not reading reviews.

## Phase 3 — Decide

If the user's original request already made these decisions — they pre-approved
a selection ("take everything trivial", "don't ask") and/or named a target
branch — treat that as the answer and proceed straight to Phase 4 without
re-asking. Otherwise ask the user two things:

1. **The target branch.** Default to an auto-generated name: pass `auto` to the
   merge script and it creates `batch/<YYYYMMDD-HHMM>` from the current date and
   time. If the user named a branch, use that instead — if it doesn't exist
   you'll create it off `<main>`; if it exists you'll merge onto it as-is (tell
   them which).
2. **Which PRs to take.** They name the PR numbers. Offer the include candidates
   as a default ("take all 4 ✅ ones?") but let them add borderline PRs or drop
   any. Nothing merges until they answer (or their original request already
   answered).

## Phase 4 — Merge (local, no push)

Run the merge script with the approved PRs, in the order the user gave (or
ascending PR number):

```
bash scripts/merge-prs.sh <remote> <main> <target>|auto <pr-number>...
```

The script owns the procedure (its header documents it): it refuses a dirty
working tree, merges each PR `--no-ff`, and aborts — never half-resolves — a
merge that conflicts or a PR that won't fetch, then continues. It prints a
`TARGET` line with the branch name and one `MERGED <n>` / `SKIPPED <n> <reason>`
line per PR — capture these; they are Phase 5's input. A non-zero exit means
setup failed (dirty tree, target checkout): relay the error — for a dirty tree,
ask the user to commit or stash first — instead of improvising.

Do not push, and do not run `gh pr merge`. The branch stays local.

## Phase 5 — Summarize

Report the outcome as a clear ledger:

- **Merged:** which PRs landed, each as `#<n> — <title>`.
- **Skipped during merge:** PRs that conflicted or failed to fetch, with the
  reason. (Distinct from PRs the user chose not to take.)
- **Sanity check (offer):** if you found lint/test commands in Phase 0, offer to
  run them on the batched branch and report the result. Don't run them
  unprompted — the user may want to inspect first.
- **Where things stand:** the name of the branch, that it's local and unpushed,
  and the natural next steps — inspect it, run the suite, push it, or open a
  combined PR. Make clear nothing on GitHub was changed.

## Verdict schema

Each sub-agent returns exactly one verdict:

```
pr:             <number>
title:          <pr title>
recommendation: include | review | skip      (✅ | ⚠️ | ❌)
triviality:     trivial | borderline | not-trivial
change_type:    docs | deps | config | test | refactor | core | mixed
size:           +<additions>/-<deletions>, <n> files
mergeable:      clean | conflicts | unknown   (vs the PR base)
ci:             green | red | pending | none
summary:        one line on what the PR does
reason:         one line on why include / review / skip
risks:          short note on anything that gives pause (empty if none)
```

`recommendation` is defined in `references/pr-assessment.md` ("Collapsing to a
recommendation").
