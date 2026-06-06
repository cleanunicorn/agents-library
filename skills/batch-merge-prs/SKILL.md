---
name: batch-merge-prs
description: >-
  Triage the project's open pull requests and batch the trivial ones onto a
  branch you name. Lists every open PR, fans out one review sub-agent per PR that
  reads the diff and judges it across four lenses — size/scope, change type,
  mergeability/CI, and an actual correctness read — then recommends include or
  skip with reasoning. Consolidates the verdicts into one ranked list, lets you
  pick which to take, and locally git-merges the chosen PRs into your target
  branch (no push, nothing closed on GitHub), reporting conflicts and a final
  summary. Use this whenever the user wants to sweep open PRs, batch or bulk
  merge pull requests, "clean up the PR queue", collect the easy/trivial/safe
  PRs, merge the low-risk ones together, or assemble several PRs onto one branch
  — even if they don't say the word "skill". Requires the `gh` CLI; works on the
  local repo, never pushes or closes PRs on its own.
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

## Why this shape

Skimming a PR list by title tells you almost nothing — "fix typo" can hide a
behavior change and "small refactor" can be genuinely trivial. The only way to
know if a PR is safe to batch is to read its diff. But reading a queue of PRs
yourself is slow and the lenses compete: "is this small?" and "is this correct?"
pull attention in different directions. One sub-agent per PR, each holding the
same four lenses over a single diff, gives every PR a real review in parallel.
You then merge their verdicts into one ranked list so the user sees a decision
table, not a stack of reports.

The sub-agents **only assess** — they read, they judge, they never merge or edit
anything. Merging happens later, under your control, locally. Keeping assessment
separate from action is what makes the verdicts trustworthy and the merge step
safe to reason about.

## Phase 0 — Orient (do this once, yourself)

Before dispatching anything, build the picture you'll bundle into every
sub-agent so the agents don't each re-derive it.

1. **Confirm `gh` works.** Run `gh auth status`. If `gh` is missing or not
   authenticated, stop and tell the user — this skill cannot list PRs without it.
2. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`. These tell you the conventions, commit style, and quality bars
   a PR should respect — the same bars the per-PR reviewer judges against. Capture
   a short summary to pass along.
3. **Detect the main branch and the GitHub remote.** Don't hard-code `main` —
   detect it (`git symbolic-ref refs/remotes/origin/HEAD`, or fall back to
   whichever of `main`/`master` exists). Call it `<main>`. Note which remote
   points at GitHub (usually `origin`); you'll fetch PR heads from it.
4. **List the open PRs.** Run
   `gh pr list --state open --json number,title,author,headRefName,baseRefName,isDraft,mergeable,labels,additions,deletions,changedFiles`.
   This is the work-list. Capture it. Skip drafts by default (mention you did);
   the user can ask to include them.
5. **Find the commands that matter (optional but useful).** Detect how the
   project lints/tests/builds, from the docs first then config. You'll offer to
   run these once on the final batched branch as a sanity check in Phase 5.

If there are no open PRs (or only drafts and the user didn't ask for those), say
so and stop — there's nothing to triage.

## Phase 1 — Fan out the triage

Dispatch **one sub-agent per open PR, all in parallel** — issue every Agent/Task
call in a single message so they run concurrently (the
`superpowers:dispatching-parallel-agents` pattern). For a large queue (say >15
open PRs), tell the user the count and confirm before fanning out that wide.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance summary, the
   detected conventions, `<main>`, and the target branch name.
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
[#131] ❌ skip · not-trivial · core · +210/-44, 9 files · CONFLICTS with target
       — refactors the auth flow; needs a real review, not a batch merge
```

Then summarize: how many PRs are include candidates, how many borderline, how
many to skip, and call out anything that **conflicts with the target branch** or
has **red/pending CI** — those are the ones most likely to bite during the merge.

Keep it skimmable. The user is making a pick from a table, not reading reviews.

## Phase 3 — Decide

Ask the user two things:

1. **The target branch.** Where should the chosen PRs land? If they already named
   it, confirm it. If it doesn't exist yet, you'll create it off `<main>`; if it
   exists, you'll merge onto it as-is (tell them which).
2. **Which PRs to take.** They name the PR numbers. Offer the include candidates
   as a default ("take all 4 ✅ ones?") but let them add borderline PRs or drop
   any. Nothing merges until they answer.

## Phase 4 — Merge (local, no push)

Set up the branch once, then merge each chosen PR in the order the user gave (or
ascending PR number):

1. **Prepare the target branch.** If it doesn't exist, create it from an
   up-to-date `<main>` (`git fetch <remote>` first, then
   `git checkout -b <target> <remote>/<main>`). If it exists, check it out. Make
   sure the working tree is clean before you start — if it isn't, stop and tell
   the user rather than risk their uncommitted work.
2. **Fetch each PR's head.** Use the base-repo pull ref so it works for fork PRs
   too: `git fetch <remote> pull/<n>/head:__batch_pr_<n>`.
3. **Merge it.** `git merge --no-ff __batch_pr_<n> -m "Merge PR #<n>: <title>"`.
   The `--no-ff` keeps each PR as a distinct, revertable merge commit, so the
   batch stays auditable.
4. **Handle conflicts honestly.** If a merge conflicts, **abort it**
   (`git merge --abort`) — do not attempt to resolve it silently. Record the PR
   as "skipped — conflicts with the batch," and continue with the rest. A
   half-resolved merge the user didn't see is worse than a cleanly skipped PR.
5. **Clean up.** Delete the temporary `__batch_pr_<n>` branches when done.

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
mergeable:      clean | conflicts | unknown   (vs the target branch)
ci:             green | red | pending | none
summary:        one line on what the PR does
reason:         one line on why include / review / skip
risks:          short note on anything that gives pause (empty if none)
```

`recommendation` maps to triviality and risk: **include** = trivial and cleanly
mergeable with no correctness concerns; **review** = borderline or low-but-real
risk the user should eyeball before batching; **skip** = not trivial, conflicts,
red CI, or a correctness concern the agent actually found in the diff.

## Error handling

- **`gh` missing/unauthenticated:** stop in Phase 0; this skill needs it.
- **No open PRs:** report nothing to triage and stop.
- **A sub-agent fails:** mark that PR "not assessed," continue with the others,
  and list it in Phase 2 so the user knows it was not judged.
- **Dirty working tree at merge time:** stop before touching any branch; ask the
  user to stash or commit first. Never merge over uncommitted work.
- **A PR head won't fetch** (deleted branch, fork gone): skip it, note why,
  continue.
- **A merge conflicts:** abort that one merge, skip the PR, continue. Report it
  in the Phase 5 ledger.
