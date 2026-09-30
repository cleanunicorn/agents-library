# Hosting the team in Herdr

Use this file when the host lists a `herdr` skill and its precondition holds:
`test "${HERDR_ENV:-}" = 1 && command -v herdr`. Load the `herdr` skill
first; it and the installed binary (`herdr <group>` with no subcommand prints
its syntax) overrule any command below. This file is the explicit topology
request the `herdr` skill asks for: each team member gets its own tab in your
current workspace, rooted at the worktree — not a sibling pane beside you, not
a new workspace. One tab per member keeps every agent full-size and readable,
and labels keep them grouped by work item in the tab bar.

Herdr adds no roles and changes no rule in `SKILL.md`; it replaces only the
transport. Its gain is live agents of different kinds side by side, which the
user can watch and which you can prompt again without a resume mechanism.

## Set up

1. **Pick kinds.** `herdr agent` lists the kinds this Herdr knows; use the
   ones installed here. Give planners and reviewers a kind different from the
   coordinator's.
2. **One tab per live member**, created when that member is needed (after
   the Phase 0 worktree exists), in your own workspace only:
   `herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd <worktree>
   --label "<slug>-<role>-<label>" --no-focus`. Record `.result.tab.tab_id`
   and `.result.root_pane.pane_id` per member in the run directory. Never
   split your own pane, never `--current`, never a new workspace.
3. **Start each member** in its tab's root pane with the same name as the
   tab label, unique among live agents: `herdr agent start
   <slug>-planner-a --kind <kind> --pane <root pane id>`. On
   `agent_not_ready`, read the pane before prompting.

`tab create` or `agent start` failing falls back to native
subagents for that member, retried once as rule 8 says; record the
degradation. Parse every id from JSON; never derive one from a listing.

## Drive

- **Prompt** with the verbatim brief and the path it writes its record to:
  `<run_dir>/<role>-<label>.md`. Records are long; scrollback may not hold
  them. Tell the member to reply with the path only, then read the file.
- **Same-role members run together only if all are prompted before any is
  waited on.** Prompt planner A and planner B without `--wait`, then `herdr
  agent wait` each. `prompt --wait` is fine for a member working alone.
- **The coordinator stays live** from Phase 2 to Phase 5: each later phase is
  a further `herdr agent prompt` to the same name, so it keeps its context.
- **Planners are done after Phase 1.** Close the tabs you created for them
  (`herdr tab close <recorded tab id>`) once their records are saved, so the
  tab bar shows only live members and reviewers never share scrollback with
  a plan.
- **`blocked`** means an approval or a question UI. Read it with `herdr agent
  read <name> --source recent-unwrapped`; relay it to the user as rule 7 says
  and deliver the answer with `herdr agent send-keys` or `agent prompt`.
  Never answer an approval on the user's behalf; unattended, that member has
  failed (rule 8).
- **A timeout is not a failure to deliver.** Read the agent before sending
  anything again.

## Tear down

At Phase 5, after the records are in the run directory: `herdr tab close
<recorded tab id>` for every member tab still open. Close only the tabs you
created and recorded —
never by label, never from a listing, never a workspace, never
`herdr server stop`.
