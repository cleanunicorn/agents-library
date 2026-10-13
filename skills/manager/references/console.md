# Running the console

## Run directory

One per session, outside every repository so nothing lands in a PR: the one
the user names, else the host's scratch directory, else
`${TMPDIR:-/tmp}/manager-<YYYYMMDD-HHMM>`. Each work item gets
`<run_dir>/<slug>/`. Workers write there; you only read it, plus the board and
the briefs you compose.

| File | Written by |
|------|------------|
| `board.md` | you |
| `<slug>/brief-<role>-<label>.md` | you — the exact text sent |
| `<slug>/<role>-<label>.md` — `setup`, `plan-a`, `merged-plan`, `implementation`, `review-a`, `validation`, `recheck-a` | that worker |
| `<slug>/gate-<role>-<short-sha>.log` | the worker that ran the gate |

**A gate log** starts with `command: <exact command>` and `head: <full SHA>`,
then the raw output, then `exit: <code>`. Accept a gate claim only
when the log exists, `head` equals `git rev-parse <branch>`, and `exit: 0` —
or, at a red baseline, no test fails that the baseline log did not.

## The loop

Each turn, in this order:

1. **The user's message.** A new work item → Phase 0 for it, or the queue
   when three are active. An answer → deliver it to the worker that asked.
   "Status" → the board. A change to a running item → brief its coordinator
   and log the change on the board.
2. **Worker events.** For each worker that finished or blocked: read its
   record, check it against its gate in `SKILL.md`, start the next phase.
3. **The board**, then a short reply: what moved, what waits on the user.

**Keep the console responsive.** Use background waits with wake-up when
available (`herdr agent wait <name>` or a background subagent), returning
to the user immediately. Otherwise wait with a timeout, report and check
next turn. Timeouts are not failures; read the worker before re-prompting.

## The board

`<run_dir>/board.md`, rewritten after every event and shown on request:

```
| item | phase | members (name=kind: state) | PR / branch | waiting on | last event |
|------|-------|----------------------------|-------------|------------|------------|
| list-limit | 4 review | coord=claude: idle · rev-a=codex: working | #12 draft | rev-a | 14:02 review started at 3f1c2ab |
| count-cmd  | 1 plan   | coord=claude: idle · plan-a=codex: done · plan-b=opencode: working | — | plan-b | 13:58 plan A saved |
| export     | queued   | — | — | a free slot | 13:55 three items active |
```

Below the table: open questions to the user, each tagged `[<slug>]`, and
**overlaps** — two items whose merged plans or diffs (`git diff --stat`) touch
the same file. An overlap is flagged, not serialized: both PRs stay
independent, and the hand-back names the file so the user merges in order.

## Concurrency

Isolation makes concurrent items safe: each owns a worktree, branch, PR and
workers, with one writer per worktree. Three active items (at most fifteen
agents) keep the board readable and host capacity sane; the user may change
the cap. A blocked item never stops another.

## Native subagents

Native workers use the same roles, briefs, budget and rules.

- **Start same-role workers in one message** so they run in parallel, and in
  the background where the host allows, so the console stays free.
- **Continue a worker** — the coordinator across Phases 0 to 5, a reviewer
  from review to re-check — by resuming or messaging it where the host can.
  Where it cannot, start a fresh agent in the same role with that role's
  records so far (setup record, merged plan, Progress, `git log`; or its own
  findings and the commits since the frozen SHA). That is the same member
  continuing, not a new one: it does not count against the budget and is not
  a second review round.
- **Subagents cannot ask the user.** Return their questions to the
  user under SKILL.md rule 7 and resume them with the answer.

## Error handling

- **No gate command, or a placeholder:** ask the user for it; unattended, the
  item is `blocked`. No worker edits without a gate.
- **Gate red at the baseline:** the coordinator adds no failure; nobody
  claims green.
- **The main branch moved, or the worktree already exists:** the coordinator
  fetches and rebases as the project allows, then re-checks the citations the
  change touches.
- **The coordinator dies:** a new one gets the setup record, merged plan,
  Progress, and `git log`; ticked boxes count only after a fresh gate log.

## Ending the session

When the user ends it, report every item still open with its hand-back block
(`in progress` or `blocked`), close the workers you started, and leave every
worktree and branch in place.
