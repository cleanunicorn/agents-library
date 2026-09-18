# Hosting the team

This file tells the **manager** how to start, address, and shut down the
team — two planners, one coordinator, two reviewers, one final reviewer — on
whatever the host offers. The roles, the isolation between them, and the
records they return are the same on every rung. Only the transport changes.

## The rule that does not change: the manager's workspace stays clear

The human runs one manager to watch several teams. Whatever the host is:

- The whole team for one work item lives in **one new dedicated workspace**,
  labelled after the work item.
- Nothing is split, tabbed, or started in the manager's own pane or
  workspace, and creating the team's workspace does not take the human's
  focus.
- The manager prompts, waits on, and reads from the team. It hosts nobody.
- The manager records the id of the workspace it created — or `workspace:
  n/a` plus what isolates the team, on a host that has no workspaces. When the
  work item is `done` it closes **that id and nothing else** — never by
  matching a label, never by picking from a listing, never a workspace it did
  not create.
- A run that ends blocked leaves its workspace open, and the hand-back names
  the id and label so the human can look inside.

## Pick the highest rung available, and record which

| Rung | Host | How the rule above is met |
|------|------|---------------------------|
| 1 | Live agents of different kinds in a terminal multiplexer such as Herdr | A new workspace per work item — see below |
| 2 | Other agent CLIs run headless from the worktree | Background processes that write to the run directory; nothing attaches to the manager's terminal |
| 3 | Native subagents of one kind (the host's Agent/Task tool) | Subagents own no panes, so the rule holds with no extra step — say so in the ledger |
| 4 | No delegation | The manager runs each pass in sequence and reports the loss of independence |

Falling a rung is a recorded degradation, not a failure. If a team workspace
cannot be created, fall to the next rung — never to the manager's own
workspace.

### Rung 1 — a terminal multiplexer (Herdr as the example)

Optional. Use it when the user asks for it or the session is already running
inside it; for Herdr that is `test "${HERDR_ENV:-}" = 1`. If the host has a
Herdr skill, load it and let it overrule this summary — the installed binary
is the authority on syntax (`herdr <group> --help`). Note that Herdr's own
default is a sibling pane beside the caller; this skill's topology rule is the
explicit request that overrides it.

1. **Create the team workspace**, labelled after the work item, rooted at the
   worktree, without stealing focus:
   `herdr workspace create --label "<work-item-slug>" --cwd <worktree> --no-focus`.
   Read the ids from the JSON response — `.result.workspace.workspace_id` and
   `.result.root_pane.pane_id` — and write the workspace id into the ledger.
   Never predict an id.
2. **Make a pane per team member inside that workspace.** The first member
   takes the root pane; further panes come from
   `herdr pane split --pane <a pane in the team workspace> --no-focus`, which
   returns the new id as `.result.pane.pane_id`. Never `--current`, and never
   the manager's `$HERDR_PANE_ID`.
3. **Start and drive each member through the agent commands:**
   `herdr agent start <role-name> --kind <kind> --pane <pane id>`, then
   `herdr agent prompt <role-name> "<brief>"`, then `herdr agent wait
   <role-name>`, then `herdr agent read <role-name>`. **A pair runs in
   parallel only if both are prompted before either is waited on:**
   `prompt --wait` blocks until that member settles, so using it on planner A
   first finishes A before B has started. Start both, prompt both without
   `--wait`, then wait on each and read each — and record `parallel: true`
   only when that is what happened. `prompt --wait` is fine for the
   coordinator and the final reviewer, who work alone. Names are unique among
   live agents, so prefix them with the work item (`limits-planner-a`). A
   member reported `blocked` is waiting on an approval or a question: read
   it, and ask the user before answering.
4. **Long deliverables go to a file** in the run directory, not to scrollback.
   Tell each member the path to write, then read the file.
5. **A pane that did start beside the manager is moved out:**
   `herdr pane move <pane> --workspace <team workspace id>`, or
   `--new-workspace --label "<work-item-slug>"` when no team workspace exists
   yet. The pane gets a new id after a move; continue with the agent name.
6. **At done, close only what you created:**
   `herdr workspace close <recorded workspace id>` — after the worktree is
   clean and every artifact is in the run directory.

The coordinator stays alive in its pane from the merge to the final fixes, so
its context carries the reason behind every decision.

### Rung 2 — headless CLIs

Different kinds without a multiplexer: for example `claude -p`, `codex exec`,
`opencode run`. Check each tool's `--help` before use; do not assume flags.
Run each from the worktree as a background process with its output going to a
file in the run directory. A headless run has no later turn, so the
coordinator's continuity comes from that tool's resume mechanism, or from
handing the next run the merged plan, the Progress list, and `git log`.

### Rung 3 — native subagents

Start paired roles in a single message so they run concurrently. One kind is
all this rung has, so vary the model between the members of a pair and record
that they are not different kinds. Continue the coordinator through the
host's resume mechanism (sending a further message to the same subagent). If
the host has none, the manager plays coordinator and says so in the hand-back.

## Giving a member a sibling skill it does not have

The planners use `plan-feature`, the reviewers `review-pr`, and the
coordinator `simplify-sweep`. A member started as another kind may not have
this plugin installed. In order:

1. The member invokes the skill by name.
2. Else the manager gives the **absolute path of the sibling skill's
   directory** — it sits beside this skill's directory — and the member reads
   `SKILL.md` and the sub-prompt files there.
3. Else, when a sandbox blocks that read, the manager pastes the sibling's
   **whole bundle verbatim** into the prompt: `SKILL.md` plus every file it
   tells the orchestrator to read or run — `lenses/*.md` for plan-feature,
   `domains/*.md` and `scripts/diff-target.sh` for review-pr, `domains/*.md`
   for simplify-sweep. `SKILL.md` alone is not enough: each of them hands
   those files to its own sub-agents verbatim.
4. Else that kind cannot fill the role. Use another kind and record the
   degradation.

Never hand over a rewritten summary of a sibling skill: a copy drifts, and the
member then follows the copy.

## Independence, in practice

- Planners and reviewers are told nothing about their counterpart and given
  no path where its output lives. Give each its own file in the run directory.
- The coordinator receives the plans labelled A and B with the authoring kind
  removed; the manager keeps the mapping for the hand-back.
- Reviewers get the acceptance criteria and the commit, never the
  coordinator's implementation report.
- The final reviewer is a new agent, not a reviewer from the earlier pair
  with a fresh prompt.

## Model choice

Planners, reviewers, and the coordinator run at the session's tier: each
makes judgement calls. The fan-outs inside the sibling skills keep their own
lesser-tier default, which is where most of the agent count is.
