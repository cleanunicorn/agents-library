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

A blocked agent is waiting on an approval or a question: § Approvals.
A timeout is not failure: read the agent before retrying.

After reports are saved, close only recorded tabs you created with
`herdr tab close <tab-id>`, never a workspace or server.

## Approvals

A worker waiting on a permission prompt is stalled, and almost none of those
prompts need the user. Read just the prompt with `herdr agent read <name>
--source recent-unwrapped --lines 40` and classify it — role, action,
target:

- **Answer every routine prompt yourself.** Routine is what a read-only
  reviewer's or investigator's job needs: reading the repository and its
  `.git`, writing its report in the run directory, shell commands and test
  runs that write nowhere else, and network fetches. Choose the broadest
  persistent option the menu offers ("Allow always", "don't ask again",
  session-wide) that writes no settings outside the run's own scope — never
  the user's global host settings, nor a settings file in the user's
  checkout. Where only such an option persists, take the session or once
  option. Send it with `herdr agent send-keys <name> <keys>` — `agent
  prompt` is refused while blocked — confirm any follow-up dialog, then
  `herdr agent get <name>` until it is no longer `blocked`.
- **Log each answer** as a `| time | worker | asked | option |` row in
  `<run-dir>/approvals.md`, escalations and rejections included.
- **Redact any secret** a prompt shows — a token, key or password — before
  it reaches the log or the user.
- **Relay to the user only** these cases, verbatim with the host's options,
  and send exactly the option the user names:
  1. merging, a push or force-push, any PR write (create, edit, comment,
     close) or other GitHub write, or a commit to the main branch — this
     skill makes none of them, so its workers never need one;
  2. destruction of what this run did not create — `rm -rf` outside its
     run directory, deleting a branch or worktree this run did not create;
  3. anything touching secrets or credentials, or the user's global host
     settings;
  4. the project's ask-first list — a public contract, stored data;
  5. a prompt you cannot classify confidently.
- **Relay questions** the same way; they are the user's to answer.

A host prompt never authorizes what SKILL.md forbids: "Allow" on a push is
still a breach of its no-GitHub-writes rule. Nor does approving widen a role
— host permission is not role permission, so a reviewer's prompt to edit
source is rejected and logged. Phase 1's merges are this session's own script,
not a worker prompt. Unattended, answer an escalation with reject and log it
as `assumed`; the worker continues.

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
