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
   among live agents, with the role's **pre-grant** after `--`:
   `herdr agent start <slug>-planner-a --kind <kind> --pane <root pane id>
   -- <pre-grant args>`. Record the args in `tabs.md`. On `agent_not_ready`,
   read the pane before prompting.

### Pre-grants per kind

The args give each role what its job needs (`references/console.md`
§ Approvals) so prompts rarely appear, while every escalation case still
surfaces as a prompt. `<repo>` is the repository root: a worktree's commits
land in `<repo>/.git` (`git rev-parse --git-common-dir`), outside the
worktree.

| kind | coordinator | planner, reviewer — writes only to the run directory |
|------|-------------|------------------------------------------------------|
| claude | `--permission-mode auto --add-dir <run_dir> --add-dir <repo>` | `--permission-mode dontAsk --add-dir <run_dir> --allowedTools Read Grep Glob "Edit(/<run_dir>/**)" "Write(/<run_dir>/**)" "Bash(git log:*)" "Bash(git diff:*)" "Bash(git show:*)"`; a reviewer adds `"Bash(<gate command>)"` |
| codex | `-C <worktree> -s workspace-write -a on-request --add-dir <run_dir> --add-dir <repo>/.git -c sandbox_workspace_write.network_access=true` | `-C <worktree> -s read-only -a on-request`; its record write and a reviewer's gate then ask once, and you answer for the session |
| opencode, kilo | `--auto` | none — answer the run directory's external-directory prompt with **Allow always** (it lasts until that agent restarts) and reject a write anywhere else |
| any other kind | read `<kind> --help` at launch and use its persistent-allow or sandbox flags; with none, start it plain and answer its prompts | same, keeping writes to the run directory |

`<run_dir>` is absolute, so claude's rule reads `Edit(//tmp/…/**)`. Never
launch with `--dangerously-skip-permissions`, `--permission-mode
bypassPermissions`, `--dangerously-bypass-approvals-and-sandbox`, or codex
`-a never`: the first three remove every prompt and `-a never` fails the
action silently, so no escalation case could reach you. Never pass args that
write a host's global settings.

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
  read <name> --source recent-unwrapped` and classify it — role, action,
  target — against `references/console.md` § Approvals:
  - **Routine:** choose the persistent option the menu offers ("Allow
    always", "don't ask again", "for this session") with `herdr agent
    send-keys <name> <keys>` — `agent prompt` is refused while blocked — and
    confirm any follow-up dialog. In opencode 1.19.0 that is `right`,
    `enter`, then `enter` on "Always allow … until OpenCode is restarted".
    Add the row to the board's **auto-approved** list, then `herdr agent get
    <name>` until it is no longer `blocked`.
  - **An escalation case, or a question:** relay it to the user tagged
    `[<slug>]` and deliver the answer the same way. Unattended, answer an
    escalation with reject and mark it `assumed`; the worker continues.
- **A timeout is not a failure to deliver.** Read the agent before sending
  anything again.

## Tear down

At an item's Phase 5, after its records are in the run directory: `herdr tab
close <recorded tab id>` for each of its tabs still open. Other items' tabs
stay. Close only tabs you created and recorded — never by label, never from a
listing, never a workspace, never `herdr server stop`.
