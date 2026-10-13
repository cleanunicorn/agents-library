# Herdr transport

Load the `herdr` skill when its precondition in SKILL.md holds. Its guidance
and installed CLI syntax (`herdr <group>`) override these examples. This
reference is self-contained so batch-merge works without the manager skill.

## Agents

Use one tab per read-only reviewer or investigator in the current workspace:

1. Choose an installed kind from `herdr agent`, with review-pr available for
   the reviewer; prefer a kind different from yours for independent review.
2. Create: `herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd
   <repo-root> --label <name> --no-focus`. Use unique
   `bmp-<YYYYMMDD-HHMM>-review` or `bmp-<YYYYMMDD-HHMM>-investigate-<n>` names.
   Record `.result.tab.tab_id` and `.result.root_pane.pane_id` from JSON;
   never infer IDs from a listing or create another workspace.
3. Start: `herdr agent start <name> --kind <kind> --pane <root-pane-id>`.
   On `agent_not_ready`, read the pane before prompting.
4. Prompt with the brief and `<run-dir>/<role>.md` for the full report;
   request a path-only reply because scrollback can truncate records.
   Prompt parallel workers before waiting; use background waits where
   supported. Read the saved report when finished.

A blocked agent needs its UI read with `herdr agent read <name> --source
recent-unwrapped`; relay any question or approval to the user and send back
the answer with `agent send-keys` or `agent prompt`. Never approve for them.
A timeout is not failure: read the agent before retrying.

After reports are saved, close only recorded tabs you created with
`herdr tab close <tab-id>`, never a workspace or server.

## Tests

Plain processes share one pane, separate from agent tabs:

1. Create once: `herdr pane split --current --direction right|down --cwd
   <repo-root> --no-focus` (right for a wide pane, down for a tall one).
   Record `.result.pane.pane_id`.
2. Run: `herdr pane run <pane> "bash <skill>/scripts/run-gate.sh <label>
   <run-dir>/<label>.log '<command>'"`. Wait with `herdr pane wait-output
   <pane> --regex 'GATE <label> exit=[0-9]+' --source recent-unwrapped
   --timeout <ms>`. Read results from the log, not scrollback.
3. Run failure attribution in this pane too, waiting for `CULPRIT `.
4. Close only this recorded pane with `herdr pane close <pane-id>`.

On timeout, read the pane before running anything again.

## Fallback

If Herdr is absent, or tab/agent/pane creation fails, use native subagents
and your shell with the same scripts and records. Note the fallback in the
report; absence is the normal path on hosts without Herdr.
