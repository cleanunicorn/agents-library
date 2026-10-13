# Workers in Herdr

Use this file when the host lists a `herdr` skill and its precondition holds:
`test "${HERDR_ENV:-}" = 1 && command -v herdr`. Load the `herdr` skill
first; it and the installed binary (`herdr <group>` with no subcommand prints
its syntax) overrule any command below.

Your pane stays the console. This is the explicit topology request required
by the Herdr skill: one full-size, watchable tab per worker in the current
workspace, grouped by `<slug>-` labels. Herdr supplies transport and live
context, with the same roles and rules as native workers.

## Start a worker

1. **Pick kinds.** `herdr agent` lists the kinds this Herdr knows; use the
   installed ones. Give planners and reviewers a kind different from the
   coordinator's.
2. **One tab per worker**, created when that worker is needed, in your own
   workspace only: `herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd
   <dir> --label "<slug>-<role>-<label>" --no-focus`. The coordinator's
   `<dir>` is the repository root, since it creates the worktree; every later
   worker's is that worktree. Record `.result.tab.tab_id` and
   `.result.root_pane.pane_id` per worker in `<run_dir>/<slug>/tabs.md`. Never
   split your own pane, never `--current`, never a new workspace.
3. **Start the agent** in that tab's root pane under the tab's label, unique
   among live agents: `herdr agent start <slug>-planner-a --kind <kind>
   --pane <root pane id>`. On `agent_not_ready`, read the pane before
   prompting.

`tab create` or `agent start` failing falls back to a native subagent for
that worker, retried once under SKILL.md rule 8; record the degradation on
the board. Parse every id from JSON; never derive one from a listing.

## Drive

- **Prompt** with the verbatim brief and the path its record goes to:
  `<run_dir>/<slug>/<role>-<label>.md`. Records are long and scrollback may
  not hold them, so tell the worker to reply with the path only, then read
  the file.
- **Do not block the console.** Prompt without `--wait`, then wait in the
  background where the host can — `herdr agent wait <name>` as a background
  command that wakes you when it exits — and return to the user. Same-role
  workers start together: prompt both before waiting on either.
- **The board reads live state.** Before showing it, `herdr agent get
  <name>` for each recorded worker: `working`, `idle`, `done`, `blocked`, or
  `unknown`. `unknown` is not done.
- **The coordinator stays live** from Phase 0 to Phase 5, and each reviewer
  from its review to its re-check: each later step is a further `herdr agent
  prompt` to the same name, so it keeps its context.
- **Planners are done after Phase 1.** Close the tabs you recorded for them
  once their records are saved, so reviewers never share scrollback with a
  plan and the tab bar shows only live workers.
- **`blocked`** means an approval or a question UI. Read it with `herdr agent
  read <name> --source recent-unwrapped`; relay it to the user tagged
  `[<slug>]` as SKILL.md rule 7 says, and deliver the answer with `herdr agent
  send-keys` or `agent prompt`. Never answer an approval for the user;
  unattended, that worker has failed (SKILL.md rule 8).
- **A timeout is not a failure to deliver.** Read the agent before sending
  anything again.

## Tear down

At an item's Phase 5, after its records are in the run directory: `herdr tab
close <recorded tab id>` for each of its tabs still open. Other items' tabs
stay. Close only tabs you created and recorded — never by label, never from a
listing, never a workspace, never `herdr server stop`.
