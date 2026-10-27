# Running the console

## Run directory

One per session, outside every repository: the one the user names, else the
host scratch directory, else `${TMPDIR:-/tmp}/manager-<YYYYMMDD-HHMM>`.
`board.md` and the briefs you send live there, with `<slug>/` per item for
workers' logs. Herdr adds `watcher.sqlite3` and `watcher.log`
(`references/herdr.md` § Watch for prompts).

## Results

A coordinator ends with a short free-form status. Read that and the issue and
PR, never records, logs or scrollback. Check claims with one-line commands:
`git rev-parse <branch>`, `gh pr view <pr> --json headRefOid,isDraft`,
`sed -n '1,2p;$p' <gate log>`. A gate claim holds only when `head:` equals the
branch head and `exit: 0`; a CI claim only when its head equals the PR head.
A status that is missing or contradicted by these goes back once.

## Output budget

The manager and every worker follow this paragraph. The coordinator brief
carries it word for word; a helper's brief gets it too:

**Output budget.** Every tool result stays in your context until the session
ends, so keep each one small. Send output that can grow — a gate, a CI wait,
a build, a log, a full diff — to a file (`> <log> 2>&1`) and read back only
what you need: `tail -n 40 <log>`, `grep -n -m 20 '<pattern>' <log>`. Pipe
any other command that can print more than a screen through `head`, `tail`
or `grep`. Read a large file by line range — the host's read tool with an
offset and limit, or `sed -n '<a>,<b>p'` — never `cat` it whole; `grep -n`
first to find the range. A slice that cut too much is re-read narrower or
further on, not in full.

Your own reads (SKILL.md § Where the line sits) stay small: `git diff --stat
| tail -n 1`, `git log --oneline -5`, the checks in § Results.

## The loop

Each turn, in this order:

0. **Still the console** (SKILL.md rule 10). Read the board header. When a
   context summary has replaced SKILL.md or this file, re-read both from the
   header's `skill` path before anything else. Start every worker on the
   header's `transport`.
1. **The user's message**, whatever it says and whether or not it names the
   manager. A new change → intake, or the queue at the active-item limit. A
   question your own reads cannot answer, a skill the user invokes now
   (`/review-pr`, `/describe-codebase`, …), or "start an agent to …" → a
   helper (§ Helpers), or intake when it asks for a change. An answer → the
   worker that asked. "Status" → the board. A change to a running item → its
   coordinator, logged on the board. "Do it yourself" → say the console
   delegates, and delegate it.
2. **Worker events.** A coordinator that finished: read its status, check it
   per § Results, act. A worker that blocked: classify and answer its prompt
   per § Approvals. On Herdr, drain the watcher's events first, whether or not it woke you
   (`references/herdr.md` § Watch for prompts).
3. **The board**, then a short reply: what moved, what waits on the user.

Stay responsive: wait in the background with wake-up where the host allows
(`herdr agent wait <name>`, a background subagent) and return to the user.
A timeout is not a failure; check the worker before re-prompting.

## Helpers

A request that changes nothing — a question, an investigation, a read-only
skill such as `review-pr` in report mode or `describe-codebase` — is its own
board item with **one helper** and no other team. It launches with the
read-only grant (`references/herdr.md` § Pre-grants per kind, the planner,
reviewer column) on the recorded transport, in a tab labelled
`<slug>-helper-a` in Herdr. Its brief is the request verbatim, the skill's
absolute path when one is named, write access only to the run directory, the
§ Output budget paragraph, and a short answer as its status. Relay that
answer. A helper never edits; a request that needs a change becomes a work
item.

## Approvals

For implementation items, the manager invocation authorizes committing and
pushing the item's branch, creating or updating its PR, waiting for CI, and
marking it ready after all gates pass. Continue through final delivery
without asking. Work stays local until the coordinator's single push. A
user-requested stopping point wins.

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
  once the manager authorizes it), the gate — for a planner or reviewer, only
  one that writes nowhere but the run directory — installs, and network
  fetches.
- **Log each answer** in the board's **approvals answered** list.
- **Redact any secret** a prompt shows — a token, key or password — before
  it goes anywhere: the board, a relay to the user, a brief.
- **Relay to the user only** these cases, tagged `[<slug>]`, verbatim
  with the host's options, and deliver exactly the option the user names —
  once, session or always — never the broadest-persistent default:
  1. an action SKILL.md forbids or reserves — merging, force-push, a commit
     to the main branch, marking ready outside the manager's go-ahead;
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
the local head (`git merge-base --is-ancestor`); no PR exists and the remote
branch is absent before the coordinator's push; the published head matches the
tested head, and the PR is ready only after authorization (`gh pr view <pr>
--json state,isDraft,headRefOid`); the main branch's remote head is the one
recorded at intake. A mismatch is case 1, relayed at once.

## The board

`<run_dir>/board.md`, rewritten after every event and shown on request.
It opens with the **console header**, written on the first turn and kept on
every rewrite, so a context summary cannot lose the mode or the transport:

```
console: manager · skill <absolute path to SKILL.md> · transport herdr <workspace id> | native · run_dir <absolute path> · since <HH:MM>
  · watcher <instance> · heartbeat <age>s · pending <N>
```

The second line is the Herdr watcher's health, refreshed from its `status`
on every rewrite; native runs omit it. Then the items:

```
| item | phase | members (name=kind: state) | PR / branch | waiting on | last event |
|------|-------|----------------------------|-------------|------------|------------|
| list-limit | review | coord=claude: working · rev-a=codex: working | #12 draft | rev-a | 14:02 review started at 3f1c2ab |
| export     | queued | — | — | a free slot | 13:55 at the active-item limit |
```

Below the table, every secret a prompt showed redacted: open questions to
the user, each tagged `[<slug>]` — escalated approvals among them — then the
**approvals answered** list, one row per approval you answered, kept on every
rewrite so the user can audit them. Its `asked` cell is your own one-line
summary of the action and target, with pipes and newlines stripped, never the
prompt's text pasted in:

```
approvals answered
| time  | item       | worker=kind        | asked (action · target)                     | option       |
|-------|------------|--------------------|---------------------------------------------|--------------|
| 14:05 | list-limit | coord=codex        | git push origin feat/list-limit             | for session  |
| 14:09 | count-cmd  | rev-a=opencode     | edit src/count.py                           | rejected — read-only role |
```

Then **overlaps** — two items whose diffs (`git diff --stat`) touch the same
file. Flag it, don't serialize; the hand-back names the file so the user
merges in order.

## Concurrency

Each item owns a worktree, branch, PR and coordinator; one writer per
worktree; a blocked item never stops another. Both grants cover the whole
repository, so give writers the other active worktrees as deny rules, in the
form their kind's pre-grant takes (`references/herdr.md` § Pre-grants per
kind). An item started later, and a host without path rules, rely on the coordinator brief alone. The limit on
active items is the user's to set; the rest queue.

## Native subagents

Same roles and rules. No watcher runs: a subagent's prompt reaches you only as
the host shows it, so claim no continuous monitoring.

- **Continue a worker** by resuming or messaging it; where the host cannot,
  start a fresh agent in that role with the issue and `git log`. A replaced
  coordinator's ticked boxes count only after a fresh gate log.
- **Pre-grant through your own session.** Native workers inherit its
  permissions. At intake, check it was started broad but guarded — for Claude
  Code `--permission-mode auto --add-dir <run_dir> --add-dir <repo> --settings
  <claude ask>`; for other hosts the coordinator row of `references/herdr.md`
  § Pre-grants per kind, without its deny rules. If not, tell the user the one
  relaunch line once; never edit their global settings. Unattended, note it
  once on the board as `assumed` and continue with the session's permissions.
- **Subagents cannot ask the user.** Relay their `asks` under rule 7 and
  resume them with the answer.
- **Read-only roles stay read-only** by their briefs alone. Before each
  starts, record the worktree's `git rev-parse HEAD`, branch and `git stash
  list | wc -l`; when it returns, compare them and require an empty `git
  status --porcelain`. A difference is a role breach, reported to the user.

## Error handling

- **No gate command, or a placeholder:** ask the user; unattended, the item is
  `blocked`. No worker edits without a gate.
- **A failed planner, or a review round with no report:** the item is
  `blocked` and the PR stays a draft (SKILL.md rule 8).
- **Gate red at the baseline:** nobody adds a failure; nobody claims green.
- **The main branch moved, or the worktree exists:** the coordinator fetches
  and rebases as the project allows, then re-checks what the change touches.
- **A reviewer's gate must write into the repository:** the reviewer reports
  it and does not run it. The coordinator runs that gate at the same head.

## The hand-back block

One per item, when its coordinator reports:

```
### <work-item-slug> — done | blocked | in progress — <outcome, or the blocker, in one line>
- Shipped: PR URL or branch · worktree path · N files changed, each by path
- Gate: `<exact command>` → <result with a number> · log by <role> at <sha>
- CI: N of N required checks passed at <sha>, failures by name | none — no CI checks | none — branch only
- Progress: N of M boxes ticked · the unticked ones, by name
- Team: roles used and why · transport
- Plan: criteria covered, plan changes
- Findings: N raised · N confirmed · N refuted · N uncertain · N fixed · each by id with verdict and evidence
- Follow-ups: open items, assumed answers, deferred findings, what was not verified
- Confidence: 🟢 High | 🟡 Medium | 🔴 Low
```

## Ending the session

The console ends only when the user ends it in words — "end the manager",
"leave the console", "stop managing". A later message does not end it
(SKILL.md rule 10). Then report every item still open with its hand-back
block (`in progress` or `blocked`), close the workers you started, stop this
run's watcher on Herdr (`<watcher> stop --run-dir <run_dir>`; it never stops
another run's), and leave every worktree and branch in place.
