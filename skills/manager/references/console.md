# Running the console

## Run directory

One per session, outside every repository so nothing lands in a PR: the one
the user names, else the host's scratch directory, else
`${TMPDIR:-/tmp}/manager-<YYYYMMDD-HHMM>`. Each work item gets
`<run_dir>/<slug>/`:

| File | Written by |
|------|------------|
| `board.md`, `<slug>/brief-<role>-<label>.md` (the exact text sent) | you |
| `<slug>/<role>-<label>.md` — `setup`, `plan-a`, `merged-plan`, `implementation`, `review-a`, `validation`, `recheck-a` | that worker |
| `<slug>/gate-<role>-<short-sha>.log`, `<slug>/ci-coordinator-<short-sha>.log` | the worker that ran it |
| `watcher.sqlite3`, `watcher.log` — Herdr transport only: worker registry, prompt events (ids and hashes, never prompt text), watcher heartbeat | `scripts/watch-workers.py` (`references/herdr.md` § Watch for prompts) |

**A gate log** starts with `command: <exact command>` and `head: <full SHA>`,
then the raw output, then `exit: <code>`. **A CI log** has the same shape:
`command:` is the `gh pr checks` call, `head:` the PR head it watched.

## Results

Workers write everything to their records; you read only the **result
block** each one ends its final reply with — nothing else from it. A native
subagent's final message is the block; a Herdr worker saves it beside its
record as `<role>-<label>.result` and replies with that path:

```
result:   <role>-<label> · done | blocked: <why> | failed: <why>
record:   <run_dir>/<slug>/<role>-<label>.md
head:     <full SHA> | n/a
gate:     <log path> · exit <code> · N passed, N failed | n/a
summary:  at most five lines of counts and ids, never content
asks:     questions or proposed splits for the user, verbatim | none
```

Each brief says what its role's `summary` holds.

**Checking it costs a few lines, not a file.** Accept a gate claim only when
`sed -n '1,2p;$p' <log>` shows `head:` equal to `git rev-parse <branch>` and
`exit: 0` — or, at a red baseline, a `summary` with no failure the baseline
log lacked. Accept a CI claim only when that log's `head:` equals the gate
log's and `gh pr view <pr> --json headRefOid`. A result block missing, over
length, or contradicted by these checks goes back to the worker once; it is
not a reason to open the record.

**Pass records by path.** The coordinator gets the plan and review paths; a
reviewer gets the validation record's path. Open a record yourself only to
relay a worker's question that quotes it, and then only the lines it names.

## Output budget

The manager and every worker follow this paragraph; each brief carries it
word for word, and a helper's brief gets it too:

**Output budget.** Every tool result stays in your context until the session
ends, so keep each one small. Send output that can grow — a gate, a CI wait,
a build, a log, a full diff — to a file (`> <log> 2>&1`) and read back only
what you need: `tail -n 40 <log>`, `grep -n -m 20 '<pattern>' <log>`. Pipe
any other command that can print more than a screen through `head`, `tail`
or `grep`. Read a large file by line range — the host's read tool with an
offset and limit, or `sed -n '<a>,<b>p'` — never `cat` it whole; `grep -n`
first to find the range. A slice that cut too much is re-read narrower or
further on, not in full.

Your own reads (SKILL.md § Where the line sits) are already small; keep them
so — `git diff --stat | tail -n 1` for a count, `git log --oneline -5`, the
`sed` and `gh --json` checks in § Results — and never open a log or record to
look around.

## The loop

Each turn, in this order:

0. **Still the console** (SKILL.md rule 10). Read the board header. When a
   context summary has replaced SKILL.md or this file, re-read both from the
   header's `skill` path before anything else. Start every worker on the
   header's `transport`.
1. **The user's message**, whatever it says and whether or not it names the
   manager. A new change → Phase 0, or the queue when three are active. A
   question your own reads (`SKILL.md` § Where the line sits) cannot answer,
   a skill the user invokes now (`/review-pr`, `/describe-codebase`, …), or
   "start an agent to …" → a helper (§ Helpers), or Phase 0 when it asks for
   a change. An answer → the worker that asked. "Status" → the board. A
   change to a running item → its coordinator, logged on the board. "Do it
   yourself" → say the console delegates, and delegate it.
2. **Worker events.** A worker that finished: read its result block, check
   it as § Results says, start the next phase. A worker that blocked:
   classify and answer its prompt per § Approvals; it keeps its phase. On
   Herdr, drain the watcher's events first, whether or not it woke you
   (`references/herdr.md` § Watch for prompts).
3. **The board**, then a short reply: what moved, what waits on the user.

Keep the console responsive: wait in the background with wake-up where the
host allows (`herdr agent wait <name>`, a background subagent) and return to
the user; otherwise wait with a timeout and check next turn. A timeout is not
a failure; check the worker before re-prompting.

## Helpers

A request that changes nothing — a question, an investigation, a read-only
skill such as `review-pr` in report mode or `describe-codebase` — is its own
board item with **one helper** and no other team. It launches like a planner:
the read-only grant (`references/herdr.md` § Pre-grants per kind, the
planner, reviewer column) on the recorded transport, a tab labelled
`<slug>-helper-a` in Herdr, and the planner's worktree check as a native
subagent. Its brief is the request verbatim, the skill's absolute path when
one is named, its record path `<run_dir>/<slug>/helper-a.md`, write access
only to the run directory, the § Output budget paragraph, and the result
block. Its `summary` holds the answer in at most five lines; relay those and
the record path. A helper never edits, and a request that turns out to need a
change becomes a work item.

## Approvals

For implementation items, the manager invocation authorizes committing and
pushing the item's branch, creating or updating its PR, waiting for CI, and
marking it ready after all gates pass. Continue through final delivery without
asking whether to push or publish. Keep Phases 0–4 local: no early draft PR
or intermediate pushes. Publish once at Phase 5 after local gates pass;
CI-only fixes follow the coordinator's batched recovery rule. A user-requested
stopping point wins.

A worker waiting on a permission prompt is stalled work, and almost none of
those prompts need the user. SKILL.md rule 7 makes them yours:

- **Pre-grant at launch** each worker's access, so prompts rarely appear —
  `references/herdr.md` per agent kind, *Native subagents* below.
- **Answer every worker approval** that still appears yourself, with the
  broadest persistent option the host offers — "Allow always", "don't ask
  again", session-wide — but never one that writes the user's global host
  settings, or a settings file outside the item's worktree: claude's "don't
  ask again" saves to `.claude/settings.local.json` under the session's
  directory, which for a coordinator is the user's checkout. Where only such
  an option persists, take the session or once option. Routine is whatever the
  role's job needs: files and folders (worktree, run directory, the repository
  and its `.git`, other paths the job reads), shell commands, git commits and
  pushes of the item's branch, `gh` for the item's PR (including ready status
  after Phase 5's gates pass), the gate — for a
  planner or reviewer, only one that writes nowhere but the run directory —
  installs, and network fetches.
- **Log each answer** in the board's **approvals answered** list.
- **Redact any secret** a prompt shows — a token, key or password — before
  it goes anywhere: the board, a relay to the user, a brief.
- **Relay to the user only** these five cases, tagged `[<slug>]`, verbatim
  with the host's options, and deliver exactly the option the user names —
  once, session or always — never the broadest-persistent default:
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
still a rule 6 breach. Nor does approving widen a role — host permission is
not role permission, so a planner's or reviewer's prompt to write outside the
run directory is rejected and logged. A host that denies an out-of-role
action itself (claude `dontAsk`) leaves no prompt to log. Unattended, an
escalation case is answered with reject — that action only — labelled
`assumed` and listed; the worker continues. Neither a routine prompt nor a
rejected one is a failed member (SKILL.md rule 8).

**Check afterwards** what launch rules cannot promise, since they match a
command as written: any existing remote branch head remains an ancestor of
the local head (`git merge-base --is-ancestor`). Before Phase 5, no new PR
exists and the remote branch is absent or unchanged from intake. For an existing PR, verify it remains
open and draft. In Phase 5, verify the published head matches the tested
local head, and the PR is open and ready only after authorization
(`gh pr view <pr> --json state,isDraft,headRefOid`). The main branch's remote
head must remain the one recorded at intake. A mismatch is case 1, relayed
at once.

## The board

`<run_dir>/board.md`, rewritten after every event and shown on request.
It opens with the **console header**, written on the first turn and kept on
every rewrite, so a context summary cannot lose the mode or the transport:

```
console: manager · skill <absolute path to SKILL.md> · transport herdr <workspace id> | native · run_dir <absolute path> · since <HH:MM>
  · watcher <instance> · heartbeat <age>s · pending <N>
```

The second line is the Herdr watcher's health, refreshed from its `status`
on every rewrite (`references/herdr.md` § Watch for prompts); native runs
have no watcher and omit it.

Then the items:

```
| item | phase | members (name=kind: state) | PR / branch | waiting on | last event |
|------|-------|----------------------------|-------------|------------|------------|
| list-limit | 4 review | coord=claude: idle · rev-a=codex: working | #12 draft | rev-a | 14:02 review started at 3f1c2ab |
| count-cmd  | 1 plan   | coord=claude: idle · plan-a=codex: done · plan-b=opencode: working | — | plan-b | 13:58 plan A saved |
| export     | queued   | — | — | a free slot | 13:55 three items active |
```

Below the table, every secret a prompt showed redacted: open questions to
the user, each tagged `[<slug>]` — escalated approvals among them — then the
**approvals answered** list, one row per approval you answered, appended and
kept on every rewrite so the user can audit them later. Its `asked` cell is
your own one-line summary of the action and target, with pipes and newlines
stripped, never the prompt's text pasted in:

```
approvals answered
| time  | item       | worker=kind        | asked (action · target)                     | option       |
|-------|------------|--------------------|---------------------------------------------|--------------|
| 14:05 | list-limit | coord=codex        | git push origin feat/list-limit             | for session  |
| 14:07 | count-cmd  | plan-b=opencode    | read external dir <run_dir>/count-cmd/*     | Allow always |
| 14:09 | count-cmd  | plan-b=opencode    | edit src/count.py                           | rejected — read-only role |
```

Then **overlaps** — two items whose diffs (`git diff --stat`) touch the same
file. Flag it, don't serialize: both PRs stay independent, and the hand-back
names the file so the user merges in order.

## Concurrency

Each item owns a worktree, branch, PR and workers, with one writer per
worktree, and a blocked item never stops another. A coordinator's grant covers
the whole repository, so an edit to a sibling's worktree would not prompt:
give a claude coordinator the other active worktrees as deny rules
(`references/herdr.md` § Pre-grants per kind). An item started later, and a
host without path rules, rely on the coordinator brief alone. The cap of
three active items is the user's to change.

## Native subagents

Same roles, briefs, budget and rules. No watcher runs: a subagent's prompt
reaches you only as the host shows it, so claim no continuous monitoring.

- **Start same-role workers in one message**, in the background where the
  host allows. A subagent's final message lands in your context, so its brief
  ends with the result block and nothing after it (§ Results).
- **Continue a worker** — the coordinator across Phases 0 to 5, a reviewer
  from review to re-check — by resuming or messaging it. Where the host
  cannot, start a fresh agent in that role with its record paths (setup,
  merged plan, its findings) and `git log`; that is the same member, not a
  new one or a second review round. A replaced coordinator's ticked boxes
  count only after a fresh gate log.
- **Pre-grant through the manager's own session.** Native workers inherit
  its permissions; the spawn call has none of its own. At intake, check the
  session was started broad but guarded — for Claude Code `--permission-mode
  auto --add-dir <run_dir> --add-dir <repo> --settings <claude ask>`; for
  other hosts the coordinator row of `references/herdr.md` § Pre-grants per
  kind, without its deny rules, since every coordinator shares this session.
  If not, tell the user the one relaunch line once; never edit their global
  settings to get it. Unattended, note it once on the board as `assumed` and
  continue with the session's permissions.
- **Subagents cannot ask the user.** Relay their `asks` under rule 7 and
  resume them with the answer. A host that shows their prompts to the user
  directly is noted once on the board.
- **Read-only roles stay read-only** by their briefs alone, since a session
  grant cannot narrow them. Before each starts, record the worktree's `git
  rev-parse HEAD`, branch and `git stash list | wc -l`; when it returns,
  compare them and require an empty `git status --porcelain` — a clean status
  alone misses a commit, a stash or a branch switch. A difference is a role
  breach, reported to the user.

## Error handling

- **No gate command, or a placeholder:** ask the user; unattended, the item
  is `blocked`. No worker edits without a gate.
- **Gate red at the baseline:** the coordinator adds no failure; nobody
  claims green.
- **The main branch moved, or the worktree exists:** the coordinator fetches
  and rebases as the project allows, then re-checks the citations the change
  touches.
- **A reviewer's gate must write into the repository:** the reviewer reports
  it and does not run it. The coordinator runs that gate at the same head,
  and the re-check record's `gate:` reads `not run — <reason> →
  <coordinator's log>`.

## Ending the session

The console ends only when the user ends it in words — "end the manager",
"leave the console", "stop managing". A later request, a skill invocation,
or "just do it yourself" does not end it (SKILL.md rule 10). Then report
every item still open with its hand-back block (`in progress` or `blocked`),
close the workers you started, stop this run's watcher on Herdr (`<watcher>
stop --run-dir <run_dir>`; it never stops another run's), and leave every
worktree and branch in place.
