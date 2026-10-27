---
name: triage-issues
description: >-
  Triage open GitHub issues into a ranked plan: duplicates, easy wins with
  code evidence, needs-info drafts, larger work. Applies labels, comments,
  closes duplicates, and fixes easy wins only after per-action approval. Use
  to groom the backlog, find duplicates, or fix good first issues. Requires
  `gh`. Not for pull requests (batch-merge-prs, review-pr) or filing new
  issues (file-issues).
---

# triage-issues

You are the **orchestrator** of a triage sweep over the project's open GitHub
issues. The user wants to know what's in the backlog — duplicates, easy wins,
issues that need more information, real larger work — without reading every
issue themselves.

Your job: list the issues, fan out one assessment sub-agent per issue,
consolidate the verdicts into duplicate clusters and one ranked decision
table, let the user pick actions, carry out **only the approved actions** on
GitHub (for selected easy wins, fix sub-agents that each open one pull
request), and summarize.

Two guardrails frame everything below:

- **You never decide what happens to an issue.** Sub-agents *recommend*; the
  user *confirms*. No label is applied, no comment posted, no issue closed
  until the user approves that action.
- **Every write to GitHub is shown before it happens.** Triage lands on the
  remote where contributors see it. Show a comment's exact text before
  posting it; name the issue and reason before closing. Labels and closures
  are reversible; a comment in a contributor's inbox is not — treat comment
  text with the most care.

## Phase 0 — Orient

Build the picture you'll bundle into every sub-agent so none re-derives it.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`,
   `CLAUDE.md`, `CONTRIBUTING`, and any issue templates under `.github/`.
   These say what a well-formed issue looks like here. Capture a short summary
   to pass along; missing guidance files are not an error — note it and continue.
2. **Run the listing script.** `bash scripts/list-issues.sh` verifies `gh` is
   installed and authenticated (a `FATAL` line and non-zero exit if not —
   stop and relay it), then prints three sections:
   - **repo** — the repo slug, which scopes sub-agents' duplicate searches.
   - **labels** — the vocabulary. Sub-agents suggest labels **from this list**
     only. Note which look like a triage convention
     (kind/priority/area/`triaged`); if none exists, you'll propose a minimal
     one in Phase 3 rather than mid-sweep.
   - **issues** — the open-issue JSON work list.
   A `(repo view failed)` or `(label list failed)` marker is non-fatal — say
   so and ask whether to continue (triage works without labels; duplicate
   search degrades to the issue list). A `FATAL` issue-list failure is fatal:
   it is the work list.
3. **Choose the scope.** Default scope is the **untriaged** open issues,
   decided by this rule: if a label named `triaged` (or similar) exists,
   issues without it; otherwise, if the repo uses kind/area labels, issues
   with no labels at all; otherwise, every open issue. State the scope you
   chose to the user before fanning out. The user can override it: all open
   issues, a label filter, or the most recent N.
4. **Sketch the codebase map.** One paragraph: language, layout, and what
   lives in each top-level directory.

If there are no issues in scope, say so and stop — there's nothing to triage.

## Phase 1 — Fan out the triage

Dispatch one sub-agent per issue concurrently, batching to the host's limits.
For a large scope (over 20 issues), tell the user the count and confirm before
fanning out that wide; offer to batch (newest first) instead.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only assessments, or inherit the
session model. Retry at the session tier only when required verdict fields or
assigned coverage are missing.

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
   or in the working tree; fetch the thread, search for duplicates, and read
   the code yourself; return exactly one verdict in this schema.*

If a sub-agent fails, note that issue as "not assessed" and continue with the
rest — never block the whole sweep on one issue.

## Phase 2 — Consolidate & present

Treat an incomplete or inconsistent verdict — an `easy-win` without `evidence`,
a `needs-info` without a `comment_draft`, a `duplicate` without
`duplicate_of` — as a failed assessment: mark the issue "not assessed" rather
than acting on a verdict that didn't earn trust.

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
attention** — a cluster suggesting a recurring failure, a possible security
report, a contributor waiting months. Keep it skimmable: the user is picking
from a table, not reading reports.

## Phase 3 — Decide

Present the proposed actions **grouped by kind**, for approval per group or
per issue. Every comment that would be posted, closure comments included, is
shown here as its **exact text**:

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
   verdict said it wasn't contained). A fix is a branch, a commit, and a
   pushed PR — approving it approves those remote writes.

Flags get no automated action; the user handles them personally. List them
before the five groups, and carry out no Phase 4 action until the user has
responded to the flag list (a simple "seen" is enough).

Offer the easy default ("apply all of the above?") and accept answers at any
granularity: a group ("no closures"), an issue ("skip #47"), or an edit
("reword the #58 comment to ..."). Restate the final action list if anything
changed, so what runs in Phases 4 and 5 is unambiguous. If the repo had no
triage label convention, propose a minimal one here (e.g. a `triaged` label
plus kind labels); creating labels is a write and needs approval. Nothing is
written until they answer.

## Phase 4 — Act (remote, only what was approved)

Carry out the approved actions in this order (labels first so even
soon-to-be-closed issues end up categorized). Narrate one short line per
action (`Labeled #47`, `Closed #52 as duplicate of #31`):

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
   obsolete gets `--reason "not planned"`. If the closure comment fails to
   post, don't close — a closure stripped of its approved explanation reads
   as a silent dismissal; record the failure and leave the issue open.

If any command fails (permissions, rate limit, issue locked), record it,
continue, and report it in Phase 6 rather than retrying into a rate limit.

## Phase 5 — Fix the approved easy wins (one PR per issue)

Skip this phase entirely if the user approved no fixes. Otherwise, dispatch
**one fix sub-agent per approved issue, in parallel, each in its own git
worktree** — a shared checkout would let parallel fixes trample each other, so
isolation is not optional. Use the host's worktree isolation if available;
otherwise create a `git worktree` per fix and clean it up after. If more
than 5 fixes were approved, confirm before fanning out that wide.

Fix sub-agents are the exception to the Phase 1 cheaper-model default: they
write code and open PRs, so run them on the **session model** unless the user
says otherwise.

Each fix sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: guidance summary, repo slug, codebase
   map, and the project's lint/test commands if you found any.
2. **The triage verdict** for its one issue — `evidence` and `reason` are the
   fixer's head start.
3. **The fix contract** — read `references/issue-fix.md` and include it
   verbatim. That file is the sub-agent's entire instruction set.

The sub-agent branches, commits, pushes, and runs `gh pr create` from inside
its worktree, and returns the PR URL (or an honest "did not open a PR
because..."). As each finishes, relay one line (`#47 → PR #103`,
`#52 → no PR: fix not contained`) and remove its worktree. A failed or
bailed-out fixer leaves nothing on GitHub, so the issue stays open and
triaged for a human.

Two boundaries hold no matter what: the **default branch is never committed
to** (every fix arrives as a PR; this skill doesn't merge its own fixes), and
it is **one issue, one PR** — the same bug at other call sites *is* the
issue, so the fixer fixes every instance in that one PR (see the contract).

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

`recommendation` collapses the five lenses into one action; the definitions
of each value live in `references/issue-assessment.md` ("Collapsing to a
recommendation").
