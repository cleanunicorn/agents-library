# Hosting the team

This file tells the **manager** how to start, address, and shut down the
team — two planners, one coordinator, two reviewers, one final reviewer — on
whatever the host offers. The roles, the isolation between them, and the
records they return are the same on every rung. Only the transport changes.

## The rule that does not change

Rule 8 of `SKILL.md` — the manager's workspace stays clear — holds on every
rung: one new dedicated workspace per work item, nothing started beside the
manager, and only the workspace the manager created is ever closed. The table
says how each rung meets it; a host with no workspaces records `workspace:
n/a` and what isolates the team instead.

## Pick the highest rung available, and record which

| Rung | Host | How the rule above is met |
|------|------|---------------------------|
| 1 | Live agents of different kinds in a terminal multiplexer such as Herdr | A new workspace per work item — see below |
| 2 | Other agent CLIs run headless from the worktree | Background processes that write to the run directory; nothing attaches to the manager's terminal |
| 3 | Native subagents of one kind (the host's Agent/Task tool) | Subagents own no panes, so the rule holds with no extra step — say so in the ledger |
| 4 | No delegation | The manager runs each pass in sequence and reports the loss of independence |

Falling a rung is a recorded degradation, not a failure.

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
   `herdr workspace close <recorded workspace id>`. Phase 8 says when.

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

Rule 2 of `SKILL.md` says who may see what. In practice: give each planner
and each reviewer its own file in the run directory and no path to its
counterpart's, and give reviewers the acceptance criteria and the commit —
never the coordinator's implementation report.
