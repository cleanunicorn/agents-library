---
name: triage-issues
description: >-
  Triage the project's open GitHub issues into a ranked action plan. Lists the
  untriaged open issues, fans out one assessment sub-agent per issue that reads
  the issue *and the actual codebase* and judges it across five lenses —
  validity (does the bug still exist in the code?), completeness, classification,
  duplicate detection (search-then-confirm), and a code-grounded effort estimate
  — then recommends an action with evidence. Consolidates the verdicts into
  duplicate clusters and one ranked decision table (easy wins, duplicates,
  needs-info, larger work), lets you pick which actions to take, and then — only
  after your confirmation — applies labels, posts needs-more-info comments,
  closes confirmed duplicates via `gh`, and fixes the easy wins you approve:
  one fix sub-agent per issue, each in its own git worktree, each opening its
  own reviewable pull request that references the issue. Use this whenever the
  user wants to triage issues, clean up or groom the issue tracker/backlog,
  find duplicate issues, find and fix easy wins or good first issues, label or
  categorize open issues, or figure out what's worth fixing first — even if
  they don't say the word "skill". Requires the `gh` CLI; never writes to
  GitHub without explicit per-action confirmation, and never commits to the
  default branch — every fix lands as its own PR.
---

# triage-issues

You are the **orchestrator** of a triage sweep over the project's open GitHub
issues. The user wants to know what's actually in their backlog — which issues
are duplicates of each other, which are easy wins they could knock out today,
which need more information before anyone can act, and which are real, larger
pieces of work — without reading every issue themselves.

Your job: list the issues, fan out one assessment sub-agent per issue,
consolidate their verdicts into duplicate clusters and one ranked decision
table, let the user pick the actions to take, then carry out **only the
approved actions** on GitHub — including, for the easy wins the user selects,
fanning out fix sub-agents that each open one pull request per issue — and
summarize what happened.

Two guardrails frame everything below:

- **You never decide what happens to an issue.** The sub-agents *recommend*;
  the user *confirms*. No label is applied, no comment posted, no issue closed
  until the user approves that action.
- **Every write to GitHub is shown before it happens.** Unlike a local merge,
  triage actions land on the remote where contributors see them. Before
  posting any comment, show the user its exact text. Before closing anything,
  name the issue and the reason. Labels and closures are reversible; a comment
  in a contributor's inbox is not — treat comment text with the most care.
  Fixes have their own form of this guardrail: every fix arrives as **its own
  pull request** on its own branch, never as a commit to the default branch —
  the PR review is where the user judges the code.

## Why this shape

An issue tracker read by title is a hall of mirrors — "app crashes on save"
and "data loss when exporting" can be the same bug — and issue text alone
can't tell you whether a bug is *still real* or how contained a fix would be:
only the code can. So each issue gets its own sub-agent, holding all five
lenses over that one issue, that reads the thread, searches for duplicates,
and **goes into the codebase**. That code-grounded read, run in parallel
across the backlog, is what separates a real triage from a labeling bot. You
then merge the verdicts, resolve duplicate claims into clusters (no single
agent can see the whole graph), and present one decision table, not a stack
of reports.

The assessment sub-agents **only assess** — they read issues and code, they
judge, they never label, comment, close, or edit anything. Action happens
later, under your control, with the user's explicit approval — and fixing is
its own later still: a separate fan-out of fix sub-agents (Phase 5), one per
approved easy win, each producing one PR. Keeping assessment, triage actions,
and fixes in separate stages is what makes the verdicts trustworthy and every
write step safe to reason about.

## Phase 0 — Orient (do this once, yourself)

Before dispatching anything, build the picture you'll bundle into every
sub-agent so the agents don't each re-derive it.

1. **Confirm `gh` works.** Run `gh auth status`. If `gh` is missing or not
   authenticated, stop and tell the user — this skill cannot list issues
   without it.
2. **Read the project's guidance.** Look for `AGENTS.md`, `README`,
   `CLAUDE.md`, `CONTRIBUTING`, and any issue templates under `.github/`.
   These tell you what a well-formed issue looks like here and what
   information reporters are expected to provide. Capture a short summary to
   pass along.
3. **Capture the repo slug.** Run `gh repo view --json nameWithOwner`. The
   sub-agents need it to scope their duplicate searches — an unscoped
   `gh search issues` searches all of GitHub.
4. **Learn the label vocabulary.** Run `gh label list --limit 200` (the
   default truncates at 30). Sub-agents must suggest labels **from this
   list** — a triage that invents labels the repo doesn't use creates work
   instead of removing it. Note which labels look like a triage convention
   (kind/priority/area/`triaged`); if none exists, you'll propose a minimal
   one at the end rather than mid-sweep.
5. **List the open issues.** Run
   `gh issue list --state open --limit 200 --json number,title,author,labels,assignees,createdAt,updatedAt`.
   Default scope is the **untriaged** open issues, decided by this rule: if a
   label named `triaged` (or similar) exists, issues without it; otherwise,
   if the repo uses kind/area labels, issues with no labels at all;
   otherwise, every open issue. State the scope you chose to the user before
   fanning out. The user can override it: all open issues, a label filter,
   or the most recent N.
6. **Sketch the codebase map.** Note the project's language, layout, and how
   to find things (the top-level directories and what lives in each). One
   paragraph is enough — it saves every sub-agent an orientation pass.

If there are no issues in scope, say so and stop — there's nothing to triage.

## Phase 1 — Fan out the triage

Dispatch **one sub-agent per issue, all in parallel** — issue every Agent/Task
call in a single message so they run concurrently (the
`superpowers:dispatching-parallel-agents` pattern). For a large scope (say >20
issues), tell the user the count and confirm before fanning out that wide;
offer to batch (newest first) instead.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance summary, the
   repo slug, the label vocabulary, the codebase map, and the **full**
   open-issue list (number + title + labels only). The list is the
   duplicate-search candidate pool, so it stays complete even when the sweep
   is batched — duplicates are usually of *older* issues, and a batch-only
   pool would miss them.
2. **The assessment lens** — read `references/issue-assessment.md` and include
   it verbatim. That file is the sub-agent's entire instruction set for how to
   judge an issue. Also give it the one issue's number and its row from the
   `gh issue list` JSON.
3. **The output contract** — the verdict schema below, with the instruction:
   *assessment only; do not label, comment, close, or edit anything, on GitHub
   or in the working tree; gather the issue's full thread yourself with `gh`;
   read the codebase read-only; return exactly one verdict in this schema.*

The sub-agent fetches its own issue's thread (`gh issue view <n> --comments`),
runs its own duplicate search (`gh search issues`), and reads the code itself,
so the orchestrator prompt stays small and the work parallelizes cleanly.

If a sub-agent fails, note that issue as "not assessed" and continue with the
rest — never block the whole sweep on one issue.

## Phase 2 — Consolidate & present

First, **resolve duplicate claims into clusters.** Each sub-agent saw only its
own issue plus what its search surfaced, so claims may be one-directional or
chained (#12 → #8, #8 → #3). Union the claims into clusters and pick one
**canonical** issue per cluster — usually the oldest, or the one with the
clearest reproduction or the most discussion (say which rule you used). If two
agents disagree about a pairing, keep both issues open in the table and flag
the conflict instead of guessing.

Then render one decision table, grouped by recommended action — flags first
(the user must see those personally), then easy wins, duplicate clusters,
needs-info, larger work, close-candidates, and finally any that failed to
assess:

```
[#61] 🚩 flag · possible security report · disclosed publicly 3 weeks ago
      — XSS claim in the comment renderer; needs your eyes, not a label
[#47] 🟢 easy-win · bug · fix in src/export.rs:112 · ~20 lines, 1 file
      — off-by-one in CSV row count; verified still present, test exists to extend
[#52] 👥 duplicate of #31 · bug · same null-deref stack trace
      — close with reference; #31 has the better reproduction
[#58] ❓ needs-info · bug? · cannot locate in code from report
      — no version or steps; comment asking for repro (draft below)
[#44] 🔨 larger · feature · touches auth + storage layers
      — real and worth doing; label and leave for planning
[#19] ❌ close · already-fixed in a1b2c3d (shipped v2.1)
      — behavior described was removed; close with the fixing commit linked
```

Append any non-empty `risks` note to its issue's line — that hesitation is
exactly what the user needs to see before approving an action on the issue.

Then summarize: how many easy wins, how many issues the duplicate clusters
would close, how many need information, and anything **worth special
attention** — a cluster suggesting a recurring failure, an issue that looks
like a security report, a contributor waiting on a reply for months.

Keep it skimmable. The user is making a pick from a table, not reading
reports.

## Phase 3 — Decide

Present the proposed actions **grouped by kind**, and let the user approve per
group or per issue. Every comment that would be posted — including closure
comments — is shown as its **exact text** here; that's the guardrail, since a
comment lands in contributors' inboxes and can't be unsent:

1. **Labels** — the full list of `issue → labels to add` pairs.
2. **Needs-info comments** — the exact draft text for each. Drafts must be
   specific ("what version, and does it happen with X disabled?"), never a
   boilerplate "please provide more info."
3. **Duplicate closures** — each `close #n as duplicate of #m` with its
   one-line justification and the exact closure comment.
4. **Other closures** — already-fixed (with the commit/release that fixed
   it), invalid, or obsolete, each with the exact closure comment.
5. **Fixes** — which easy wins to actually fix, each becoming **one pull
   request per issue** (Phase 5). Offer the 🟢 list as the default; the user
   can drop any or add a 🔨 one they consider worth attempting (warn that the
   verdict said it wasn't contained). A fix means: a branch, a commit, a
   pushed PR that references the issue — so approving here is approving
   those remote writes.

Flags get no automated action — they exist precisely so the user handles them
personally. List them first, before the five groups, and don't carry out any
Phase 4 action until the user has responded to the flag list (a simple
"seen" is enough — what matters is that no flag slips past unnoticed).

Offer the easy default ("apply all of the above?") and accept answers at any
granularity: a whole group ("all labels", "no closures"), a single issue
("skip #47"), or an edit ("reword the #58 comment to ..."). Restate the final
action list back if anything was dropped or changed, so what runs in Phases 4
and 5 is unambiguous. If the repo had no triage label convention, this is where you
propose a minimal one (e.g. a `triaged` label plus kind labels) — creating
labels is also a write and also needs approval. Nothing is written until they
answer.

## Phase 4 — Act (remote, only what was approved)

Carry out the approved actions, in this order (labels first so even
soon-to-be-closed issues end up categorized for posterity). Narrate as you
go — one short line per action (`Labeled #47`, `Closed #52 as duplicate of
#31`) so the user sees progress and catches failures as they happen, not
only in the Phase 6 ledger:

1. **Labels:** `gh issue edit <n> --add-label "<a>,<b>"`. Create a label first
   (`gh label create`) only if the user approved it in Phase 3. If a
   `gh label create` fails, skip applying that label (the edit would fail
   too) and record it for the ledger.
2. **Comments:** `gh issue comment <n> --body "<approved text>"` — exactly the
   approved text, no silent edits. If you must change a draft after approval,
   go back to the user first. Comment text can quote untrusted issue content —
   pass it shell-safely (write it to a temp file and use `--body-file`, or
   pipe it via `--body-file -`) so backticks or `$(...)` in it are never
   interpreted by the shell.
3. **Duplicate closures:** `gh issue close <n> --duplicate-of <m>` — GitHub
   records the duplicate relationship and links the cluster. Post the approved
   closure comment first if it says more than "duplicate of #<m>".
4. **Other closures:** post the approved closure comment, then close with the
   right reason — already-fixed gets `--reason completed`; invalid or
   obsolete gets `--reason "not planned"`.

If any command fails (permissions, rate limit, issue locked), record it and
continue with the rest — report failures honestly in Phase 6 rather than
retrying into a rate limit.

## Phase 5 — Fix the approved easy wins (one PR per issue)

Skip this phase entirely if the user approved no fixes. Otherwise, dispatch
**one fix sub-agent per approved issue, in parallel, each in its own git
worktree** — parallel fixes in a shared checkout would trample each other, so
isolation is not optional. Use the Agent tool's worktree isolation if
available; otherwise create a `git worktree` per fix yourself (the
`superpowers:using-git-worktrees` pattern) and clean it up after. If more
than ~5 fixes were approved, confirm before fanning out that wide — each fix
is a real implementation run, not a quick edit.

Each fix sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance summary, the
   repo slug, the codebase map, and the project's lint/test commands if you
   found any.
2. **The triage verdict** for its one issue — the assessment agent already
   located the code (`evidence`) and sketched the fix (`reason`); hand that
   head start over so the fixer doesn't re-derive it.
3. **The fix contract** — read `references/issue-fix.md` and include it
   verbatim. That file is the sub-agent's entire instruction set: reproduce
   first, fix minimally, gate on lint/tests, one branch and one PR per
   issue, and report honestly when a "win" turns out not to be easy.

The sub-agent does its own branching, committing, pushing, and
`gh pr create` from inside its worktree, and returns the PR URL (or an
honest "did not open a PR because..."). As each one finishes, relay the
result in one line (`#47 → PR #103`, `#52 → no PR: fix not contained`). A
fix sub-agent that fails or bails out costs nothing on GitHub — no branch
push, no PR — so failures here are reports, not messes to clean up.

Two boundaries hold no matter what:

- **The default branch is never committed to.** Every fix lives on its own
  branch and arrives as a PR — the PR review is where a human judges the
  code; this skill doesn't merge its own fixes.
- **One issue, one PR.** A fixer that discovers its issue can't be fixed in
  isolation reports back instead of growing the PR to swallow neighboring
  problems.

## Phase 6 — Summarize

Report the outcome as a clear ledger:

- **Labeled / commented / closed:** each action that succeeded, as
  `#<n> — <what was done>`.
- **PRs opened:** each fix as `#<n> → <PR URL>`, plus any fixes that bailed
  out and why.
- **Failed:** any action that errored, with the message. (Distinct from
  actions the user chose not to take.)
- **The remaining backlog:** what's left open and triaged — including easy
  wins the user chose not to fix this round.
- **Untriaged remainder:** anything skipped by scope or batching, so the user
  knows the sweep's boundary.

## Verdict schema

Each sub-agent returns exactly one verdict:

```
issue:          <number>
title:          <issue title>
recommendation: easy-win | larger | needs-info | duplicate | close | flag
                (🟢 | 🔨 | ❓ | 👥 | ❌ | 🚩)
kind:           bug | feature | enhancement | question | docs | task
duplicate_of:   #<n> (empty unless recommendation is duplicate)
validity:       confirmed-in-code | plausible | not-found | already-fixed | n/a
effort:         <rough size: lines/files/layers touched, or "unknown">
evidence:       file:line or commit reference backing validity/effort
                ("src/export.rs:112", "fixed in a1b2c3d"); for not-found, a
                brief note on what was searched — empty only for n/a
labels:         labels to add, from the repo's existing vocabulary (empty if
                none fit — fewer labels beats wrong labels)
comment_draft:  the specific question to ask (only for needs-info)
summary:        one line on what the issue reports or asks
reason:         one line on why this recommendation
risks:          short note on anything that gives pause (empty if none)
```

`recommendation` collapses the five lenses into one action; the authoritative
definitions of each value live in `references/issue-assessment.md`
("Collapsing to a recommendation") — don't restate them here.

## Error handling

- **`gh` missing/unauthenticated:** stop in Phase 0; this skill needs it.
- **Another Phase 0 command fails:** `gh issue list` failing is fatal — it is
  the work list; report the error and stop. If `gh repo view` or
  `gh label list` fails, say so and ask whether to continue (triage works
  without labels; duplicate search degrades to the issue list). Missing
  guidance files are not an error — note it and continue.
- **No issues in scope:** report nothing to triage and stop.
- **A sub-agent fails:** mark that issue "not assessed," continue with the
  others, and list it in Phase 2 so the user knows it was not judged.
- **A verdict is incomplete or inconsistent** — an `easy-win` without
  `evidence`, a `needs-info` without a `comment_draft`, a `duplicate` without
  `duplicate_of`: treat it as a failed assessment and mark the issue "not
  assessed" rather than acting on a verdict that didn't earn trust.
- **Search rate limit:** many parallel sub-agents running `gh search issues`
  can trip GitHub's search rate limit. The assessment file tells them to fall
  back to the issue list they were given and note it in `risks` — don't
  retry into the limit.
- **Conflicting duplicate claims:** don't pick a side — keep both issues open
  in the table, show the conflict, let the user decide.
- **A write action fails in Phase 4:** record it, continue with the remaining
  actions, report it in the Phase 6 ledger.
- **A fix sub-agent fails or bails out:** nothing was pushed, so there is
  nothing to undo — report it in the ledger with the reason, remove its
  worktree, and leave the issue open and triaged for a human.
- **A fix can't pass the project's tests:** the contract says no PR — the
  fixer reports what it tried and why it's stuck instead of pushing red.
- **The repo has no labels at all:** triage still works (the table is the
  value); propose a minimal label set in Phase 3 instead of inventing labels
  per issue.
