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
| `<slug>/ci-coordinator-<short-sha>.log` | the coordinator, waiting on the PR's checks |

**A gate log** starts with `command: <exact command>` and `head: <full SHA>`,
then the raw output, then `exit: <code>`. Accept a gate claim only
when the log exists, `head` equals `git rev-parse <branch>`, and `exit: 0` —
or, at a red baseline, no test fails that the baseline log did not.
**A CI log** has the same shape: `command:` is the `gh pr checks` call,
`head:` the PR head it watched. Accept a CI claim only when that head equals
the gate log's and `gh pr view <pr> --json headRefOid`.

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

## Approvals

A worker waiting on a permission prompt is stalled work, and almost none of
those prompts need the user. SKILL.md rule 7 makes them yours:

- **Pre-grant at launch** each worker's access, so prompts rarely appear —
  the transport says how (`references/herdr.md` per agent kind, *Native
  subagents* below).
- **Answer every worker approval** that still appears yourself, with the
  broadest persistent option the host offers — "Allow always", "don't ask
  again", session-wide — but never one that writes the user's global host
  settings, or a settings file outside the item's worktree: claude's "don't
  ask again" saves to `.claude/settings.local.json` under the session's
  directory, which for a coordinator is the user's checkout. Where only such
  an option persists, take the session or once option. Routine is whatever the role's job needs: files and folders
  (worktree, run directory, the repository and its `.git`, other paths the
  job reads), shell commands, git commits and pushes of the item's branch,
  `gh` for the item's draft PR, the gate, installs, and network fetches.
- **Log each answer** in the board's **auto-approved** list.
- **Redact any secret** a prompt shows — a token, key or password — before
  it goes anywhere: the board, a relay to the user, a brief.
- **Relay to the user only** these five cases, tagged `[<slug>]`:
  1. an action SKILL.md forbids or reserves — merging, force-push, a commit
     to the main branch, marking ready outside Phase 5;
  2. irreversible destruction outside the item's worktree and run directory
     — deleting other paths, dropping data, deleting branches or worktrees
     this run did not create;
  3. anything touching secrets or credentials, or the user's global host
     settings;
  4. the project's ask-first list — a public contract, stored data;
  5. a prompt you cannot classify confidently.

A host prompt never authorizes what SKILL.md forbids: "Allow" on a merge is
still a rule 6 breach. Approving a prompt never widens a role either —
host permission is not role permission, so a planner's or reviewer's prompt
to write outside the run directory is rejected and logged, not approved.
A host that denies an out-of-role action itself — claude `dontAsk` — has
already rejected it; there is no prompt to log.
Unattended, an escalation case is answered with reject — that action only —
labelled `assumed` and listed; the worker continues. Neither a routine
prompt nor a rejected one is a failed member (SKILL.md rule 8).

**Check afterwards** what launch rules cannot promise, since they match a
command as written: at each coordinator event, the PR is still an open
draft (`gh pr view <pr> --json state,isDraft`), the remote branch head is an
ancestor of the local one (`git merge-base --is-ancestor`), and the main
branch's remote head is the one recorded at intake. A mismatch is case 1,
relayed at once.

## The board

`<run_dir>/board.md`, rewritten after every event and shown on request:

```
| item | phase | members (name=kind: state) | PR / branch | waiting on | last event |
|------|-------|----------------------------|-------------|------------|------------|
| list-limit | 4 review | coord=claude: idle · rev-a=codex: working | #12 draft | rev-a | 14:02 review started at 3f1c2ab |
| count-cmd  | 1 plan   | coord=claude: idle · plan-a=codex: done · plan-b=opencode: working | — | plan-b | 13:58 plan A saved |
| export     | queued   | — | — | a free slot | 13:55 three items active |
```

Below the table, every secret a prompt showed redacted: open questions to
the user, each tagged `[<slug>]` — escalated approvals among them — then the
**auto-approved** list, one row per approval you answered, appended and kept
on every rewrite so the user can audit them later:

```
auto-approved
| time  | item       | worker=kind        | asked (action · target)                     | option       |
| 14:05 | list-limit | coord=codex        | git push origin feat/list-limit             | for session  |
| 14:07 | count-cmd  | plan-b=opencode    | read external dir <run_dir>/count-cmd/*     | Allow always |
| 14:09 | count-cmd  | plan-b=opencode    | edit src/count.py                           | rejected — read-only role |
```

Then **overlaps** — two items whose merged plans or diffs (`git diff --stat`) touch
the same file. An overlap is flagged, not serialized: both PRs stay
independent, and the hand-back names the file so the user merges in order.

## Concurrency

Isolation makes concurrent items safe: each owns a worktree, branch, PR and
workers, with one writer per worktree. A coordinator's grant covers the
whole repository, so an edit to a sibling's worktree would not prompt: give
a claude coordinator the active items' other worktrees as deny rules
(`references/herdr.md` § Pre-grants per kind). An item started later, and a
host without path rules, rely on the coordinator brief alone. Three active items (at most fifteen
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
- **Pre-grant through the manager's own session.** Native workers inherit
  its permissions, and the spawn call has no permission fields of its own.
  At intake, check the session was started with a broad, guarded mode and
  the item's directories and the escalation ask rules — for Claude Code
  `--permission-mode auto --add-dir <run_dir> --add-dir <repo> --settings
  <claude ask>`; for other hosts the coordinator row of `references/herdr.md`
  § Pre-grants per kind, which defines `<claude ask>` — here without its
  deny rules, since every item's coordinator shares this session. If it was not, tell the
  user the one relaunch line once; never edit their global settings to get
  it.
- **Subagents cannot ask the user.** Return their questions to the user
  under SKILL.md rule 7 and resume them with the answer. Their permission
  prompts follow § Approvals when they reach you; a host that shows them to
  the user directly is noted once on the board rather than claimed as
  auto-approved.
- **Read-only roles stay read-only** by their briefs; a host-level grant
  for the whole session cannot narrow a planner or reviewer. Before each
  starts, record the worktree's `git rev-parse HEAD`, branch and `git stash
  list | wc -l`; when it returns, compare them and require an empty `git
  status --porcelain` — a clean status alone misses a commit, a stash or a
  branch switch. A difference is a role breach, reported to the user. Writes
  outside the worktree escape this check; there only the brief holds.

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
