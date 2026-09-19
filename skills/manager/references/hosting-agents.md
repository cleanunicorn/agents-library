# Hosting the managers and their teams

This file tells both roles how to start, address, and shut down what they
direct, on whatever the host offers: the **super manager** hosting one manager
per work item, and a **manager** hosting its team — the roster it picked from
`agent-types.md`. The roles, the isolation between them, and the records they
return are the same on every rung. Only the transport changes.

## Two levels

| Level | Who creates it | What it is | Who closes it |
|-------|----------------|------------|---------------|
| Manager workspace | the super manager, one per work item | a new workspace labelled after the work item, rooted at the repository | the super manager, by recorded id |
| Team sub-space | that manager | a new tab inside the manager's own workspace, labelled `<slug>-team`, rooted at the worktree | that manager, by recorded id |

The chain of command follows the same levels: the super manager prompts and
reads managers only; a manager prompts and reads its own team only; team
members own no enclosing space. Nobody but the super manager addresses the
user. The two levels may sit on different rungs — live managers whose teams
are native subagents, say — and each level records its own.

## The rule that does not change

Rule 8 of `SKILL.md` holds on every rung, at both levels: nothing is started
in the super manager's workspace or beside a manager's own pane, and each
level closes only the ids it created and recorded — or inherited, recorded,
from the dead agent it replaces — never by label, never from a listing. A
host with no workspaces records `workspace: n/a` and what isolates the agents
instead.

## Pick the highest rung available, and record which

| Rung | Host | Super manager → managers | Manager → team |
|------|------|--------------------------|----------------|
| 1 | Live agents of different kinds in a terminal multiplexer such as Herdr | A new workspace per work item — 1a below | A new tab in the manager's workspace — 1b below |
| 2 | Other agent CLIs run headless | Background processes, one per manager, writing to its run directory | Background processes from the worktree; nothing attaches to a terminal |
| 3 | Native subagents of one kind (the host's Agent/Task tool) | Each manager is a subagent, if the nesting limit allows — see Rung 3 | Subagents own no panes, so the rule holds with no extra step — say so in the ledger |
| 4 | No delegation | The super manager plays each manager itself, in sequence (`manager: self`) | The manager runs each pass in sequence and reports the loss of independence |

Falling a rung is a recorded degradation, not a failure.

### Rung 1 — a terminal multiplexer (Herdr as the example)

Optional. Use it when the user asks for it or the session is already running
inside it; for Herdr that is `test "${HERDR_ENV:-}" = 1`. If the host has a
Herdr skill, load it and let it overrule this summary — the installed binary
is the authority on syntax (`herdr <group> --help`). Note that Herdr's own
default is a sibling pane beside the caller; this skill's topology rule is the
explicit request that overrides it.

#### 1a — the super manager hosts a manager

1. **Create the manager's workspace**, labelled after the work item, rooted
   at the repository — the worktree does not exist until the manager's
   Phase 0 — without stealing focus:
   `herdr workspace create --label "<work-item-slug>" --cwd <repository> --no-focus`.
   Read the ids from the JSON response — `.result.workspace.workspace_id` and
   `.result.root_pane.pane_id` — and write the workspace id into the ledger.
   Never predict an id.
2. **Start the manager in that root pane:**
   `herdr agent start <slug>-manager --kind <kind> --pane <root pane id>`,
   then `herdr agent prompt <slug>-manager "<launch prompt>"`. Prompt every
   manager before waiting on any.
3. **Watch by rotating** `herdr agent wait <manager> --until blocked --until
   idle --until done --timeout <ms>` over the managers, and read each run
   directory. A manager reported `blocked` is waiting on an approval or a
   question: read it with `herdr agent read <manager>` and relay it. Herdr
   rejects `agent prompt` to a `blocked` agent, so the user's answer to that
   dialog is delivered with `herdr agent send-keys <manager> <keys>`.
4. **At done, close only what you created:**
   `herdr workspace close <recorded workspace id>`. `super-manager.md` S4
   says when. Never close a manager's tab yourself.

#### 1b — a manager hosts its team

1. **Create the team sub-space** as a tab in your own workspace, rooted at
   the worktree: `herdr tab create --workspace <your workspace id> --cwd
   <worktree> --label "<slug>-team" --no-focus`. Read the ids from the
   response — `.result.tab.tab_id` and `.result.root_pane.pane_id` — and
   write the tab id into your ledger. Never `workspace create`: the workspace
   level belongs to the super manager.
2. **Make a pane per team member inside that tab.** The first member takes
   the tab's root pane; further panes come from
   `herdr pane split --pane <a pane in the team tab> --direction
   right|down --cwd <worktree> --no-focus` (`--direction` is required), which
   returns the new id as `.result.pane.pane_id`. Never `--current`, and never
   your own `$HERDR_PANE_ID`.
3. **Start and drive each member through the agent commands:**
   `herdr agent start <role-name> --kind <kind> --pane <pane id>`, then
   `herdr agent prompt <role-name> "<brief>"`, then `herdr agent wait
   <role-name>`, then `herdr agent read <role-name>`. **Agents of one type
   run in parallel only if all are prompted before any is waited on:**
   `prompt --wait` blocks until that member settles, so using it on planner A
   first finishes A before B has started. Start them all, prompt them all
   without `--wait`, then wait on each and read each — and record
   `parallel: true` only when that is what happened. `prompt --wait` is fine
   for an agent that works alone: the coordinator, the final reviewer, a sole
   planner or reviewer. Names are unique among
   live agents, so prefix them with the work item (`limits-planner-a`). A
   member reported `blocked` is waiting on an approval or a question: read
   it. Its question travels up the chain — member → you → your question
   record → the super manager → the user — and the answer comes back down the
   same way, delivered to a `blocked` member with `herdr agent send-keys`.
   Never answer it for the user.
4. **Long deliverables go to a file** in the run directory, not to scrollback.
   Tell each member the path to write, then read the file.
5. **A pane that did start beside you is moved out:**
   `herdr pane move <pane> --new-tab --workspace <your workspace id>
   --no-focus` (`--workspace` is accepted only with `--new-tab`). Only the
   super manager uses `--new-workspace`. The pane gets a new id after a move —
   `.result.move_result.pane.pane_id`; continue with that or the agent name.
6. **At done, close only what you created:**
   `herdr tab close <recorded tab id>`. Phase 8 says when. Never
   `workspace close`.

### Rung 2 — headless CLIs

Different kinds without a multiplexer: for example `claude -p`, `codex exec`,
`opencode run`. Check each tool's `--help` before use; do not assume flags.
Run each as a background process — a manager from the repository, a team
member from the worktree — with its output going to a file in the run
directory. A headless run has no later turn, so continuity — the
coordinator's across phases, a manager's across a question — comes from that
tool's resume mechanism, or from handing the next run what it needs: the
merged plan, the Progress list, and `git log` for a coordinator; the launch
prompt with `answers_so_far` filled in for a manager.

### Rung 3 — native subagents

Start same-type agents in a single message so they run concurrently. One kind
is all this rung has, so vary the model between them and record that they are
not different kinds. Continue the coordinator through the
host's resume mechanism (sending a further message to the same subagent). If
the host has none, the manager plays coordinator and says so in the hand-back.

Two levels need nesting. Count the layers below the super manager: the
manager, its team member, and the fan-out inside that member's sibling skill.
A host that allows that depth runs each manager as a subagent; check the
host's limit rather than assuming it. A host that allows less applies the
**collapse rule** of `super-manager.md` S1.

## The question relay, per rung

| Rung | The signal that a manager has a question | Where the super manager reads it | How it forwards the answer |
|------|------------------------------------------|----------------------------------|----------------------------|
| 1 | `agent wait` returns `blocked` or `idle`, and `status.md` reads `blocked` | `<run_dir>/questions.md`; the pane, for an approval prompt | `herdr agent prompt <manager> "<id>: <answer>"` — an approval prompt as 1a step 3 says |
| 2 | the process ended with a `pending` record in `questions.md` | the same file | resume that run, or restart it with `answers_so_far` filled in |
| 3 | the subagent returned a `blocked` team block | its return text and `questions.md` | a further message to the same subagent, else a new one with `answers_so_far` |

## When an agent dies

- **The coordinator:** a new one gets the merged plan, Progress, and
  `git log`; ticked boxes are trusted only after the gate passes. The manager
  reports the continuity exception.
- **A manager:** once the super manager has confirmed the death, it starts a
  replacement in the same workspace with the same run directory, and a launch
  prompt whose `answers_so_far` is rebuilt from the inherited `questions.md`
  — every answered or assumed id, verbatim. Ownership transfers with the ledger: every team sub-space id the
  dead manager recorded is the replacement's to reuse and to close, by exact
  id. It re-runs the gate before trusting Progress, reuses the recorded
  sub-space or closes it before opening another, and at Phase 8 closes every
  recorded id.

## Giving an agent a skill it does not have

The planners use `plan-feature`, the reviewers `review-pr`, the coordinator
`simplify-sweep`, and every manager this skill itself. An agent started as
another kind may not have this plugin installed. In order:

1. The agent invokes the skill by name. A manager's launch prompt still
   opens with `role: manager`, so the skill's router gives it the right role.
2. Else whoever started it gives the **absolute path of the skill's
   directory** — the siblings sit beside this skill's directory — and the
   agent reads `SKILL.md` and the sub-prompt files there.
3. Else, when a sandbox blocks that read, the **whole bundle is pasted
   verbatim** into the prompt: `SKILL.md` plus every file it tells the
   orchestrator to read or run — `lenses/*.md` for plan-feature,
   `domains/*.md` and `scripts/diff-target.sh` for review-pr, `domains/*.md`
   for simplify-sweep, every file in `references/` for this skill. `SKILL.md`
   alone is not enough: each of them hands those files on verbatim.
4. Else that kind cannot fill the role. Use another kind and record the
   degradation.

Never hand over a rewritten summary of a skill: a copy drifts, and the agent
then follows the copy.

## Independence, in practice

Rule 2 of `SKILL.md` says who may see what. In practice: give each planner
and each reviewer its own file in the run directory and no path to anyone
else's, and give reviewers the acceptance criteria and the commit —
never the coordinator's implementation report. A manager sees no other
manager's run directory.
