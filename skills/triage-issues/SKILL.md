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
  after your confirmation — applies labels, posts needs-more-info comments, and
  closes confirmed duplicates via `gh`. Use this whenever the user wants to
  triage issues, clean up or groom the issue tracker/backlog, find duplicate
  issues, find easy wins or good first issues, label or categorize open issues,
  or figure out what's worth fixing first — even if they don't say the word
  "skill". Requires the `gh` CLI; never writes to GitHub without explicit
  per-action confirmation.
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
approved actions** on GitHub and summarize what happened.

Two guardrails frame everything below:

- **You never decide what happens to an issue.** The sub-agents *recommend*;
  the user *confirms*. No label is applied, no comment posted, no issue closed
  until the user approves that action.
- **Every write to GitHub is shown before it happens.** Unlike a local merge,
  triage actions land on the remote where contributors see them. Before
  posting any comment, show the user its exact text. Before closing anything,
  name the issue and the reason. Labels and closures are reversible; a comment
  in a contributor's inbox is not — treat comment text with the most care.

## Why this shape

An issue tracker read by title is a hall of mirrors — "app crashes on save"
and "data loss when exporting" can be the same bug, and "add dark mode" filed
three times looks like three features. Worse, issue text alone can't tell you
whether a bug is *still real* or whether a fix would be easy: only the code
can. So each issue gets its own sub-agent that reads the issue, searches for
duplicates, and **goes into the codebase** to check whether the described
behavior still exists and how contained a fix would be. That code-grounded
read is what separates a real triage from a labeling bot.

The lenses compete — "is this a duplicate?" and "how hard is the fix?" pull
attention in different directions — so one sub-agent per issue, each holding
the same five lenses over a single issue, gives every issue a real assessment
in parallel. You then merge their verdicts, resolve duplicate claims into
clusters (no single agent can see the whole graph), and present one decision
table, not a stack of reports.

The sub-agents **only assess** — they read issues and code, they judge, they
never label, comment, close, or edit anything. Action happens later, under
your control, with the user's explicit approval. Keeping assessment separate
from action is what makes the verdicts trustworthy and the write step safe to
reason about.

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

Flags get no automated action — they exist precisely so the user handles them
personally; just make sure each one was seen.

Offer the easy default ("apply all of the above?") but let them drop or edit
any item. If the repo had no triage label convention, this is where you
propose a minimal one (e.g. a `triaged` label plus kind labels) — creating
labels is also a write and also needs approval. Nothing is written until they
answer.

## Phase 4 — Act (remote, only what was approved)

Carry out the approved actions, in this order (labels first so even
soon-to-be-closed issues end up categorized for posterity):

1. **Labels:** `gh issue edit <n> --add-label "<a>,<b>"`. Create a label first
   (`gh label create`) only if the user approved it in Phase 3.
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
continue with the rest — report failures honestly in Phase 5 rather than
retrying into a rate limit.

## Phase 5 — Summarize

Report the outcome as a clear ledger:

- **Labeled / commented / closed:** each action that succeeded, as
  `#<n> — <what was done>`.
- **Failed:** any action that errored, with the message. (Distinct from
  actions the user chose not to take.)
- **The remaining backlog:** what's left open and triaged — the easy wins
  ranked first, since "which of these do you want me to fix?" is the natural
  next conversation.
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
labels:         labels to add, from the repo's existing vocabulary
comment_draft:  the specific question to ask (only for needs-info)
summary:        one line on what the issue reports or asks
reason:         one line on why this recommendation
risks:          short note on anything that gives pause (empty if none)
```

`recommendation` collapses the lenses: **easy-win** = valid, well-understood,
and a contained fix the agent located in the code; **larger** = valid and
worth doing but not contained; **needs-info** = can't be assessed without more
from the reporter; **duplicate** = same underlying defect/request as an
earlier issue; **close** = already fixed, invalid, or describes behavior that
no longer exists; **flag** = something the user must see personally (possible
security report, angry long-waiting contributor, legal/licensing question).

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
- **Search rate limit:** many parallel sub-agents running `gh search issues`
  can trip GitHub's search rate limit. The assessment file tells them to fall
  back to the issue list they were given and note it in `risks` — don't
  retry into the limit.
- **Conflicting duplicate claims:** don't pick a side — keep both issues open
  in the table, show the conflict, let the user decide.
- **A write action fails in Phase 4:** record it, continue with the remaining
  actions, report it in the Phase 5 ledger.
- **The repo has no labels at all:** triage still works (the table is the
  value); propose a minimal label set in Phase 3 instead of inventing labels
  per issue.
