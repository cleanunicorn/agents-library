# Running agents and tests in Herdr

Use this file when the host lists a `herdr` skill and `test "${HERDR_ENV:-}"
= 1 && command -v herdr` passes. Load the `herdr` skill first; it and the
installed binary (`herdr <group>` with no subcommand prints its syntax)
overrule any command below. Herdr changes only the transport — every rule in
`SKILL.md` still holds.

## Agents: one tab each

Agents follow the manager skill's tab pattern —
[`../../manager/references/herdr.md`](../../manager/references/herdr.md),
sections *Set up*, *Drive*, and *Tear down* — with these specifics:

- **Names:** `bmp-<YYYYMMDD-HHMM>-<role>`, e.g. `bmp-20261013-1405-review`
  and `bmp-20261013-1405-investigate-42`. The same string labels the tab and
  names the agent, unique among live agents.
- **Roles:** one `review` agent (Phase 3) and at most one `investigate-<n>`
  agent per culprit PR (Phase 2). Both only read.
- **Kind:** any kind `herdr agent` lists that has the review-pr skill
  installed; prefer one different from your own so the review is independent.
- **Cwd:** the repository root, with the batch branch checked out.
- **Records:** tell each agent to write its full report to
  `<run-dir>/<role>.md` and reply with the path only; read the file.

## Tests: one pane

Tests are plain processes, not agents, so they get a pane, not a tab:

1. Once, before the first command: `herdr pane split --current --direction
   right|down --cwd <repo-root> --no-focus` (split a wide pane right, a tall
   one down). Record `.result.pane.pane_id`.
2. Per command: `herdr pane run <pane> "bash <skill>/scripts/run-gate.sh
   <label> <run-dir>/<label>.log '<command>'"`, then `herdr pane wait-output
   <pane> --regex 'GATE <label> exit=[0-9]+' --source recent-unwrapped
   --timeout <ms>`. Read the result from the log file, not from scrollback,
   which may not hold it.
3. Run `attribute-failure.sh` in the same pane the same way, waiting on
   `CULPRIT `.
4. At the end, `herdr pane close <recorded pane id>` — only the pane you
   created.

A timeout is not a failure: read the pane before running anything again.

## Fallback

When the precondition fails, or `tab create`, `agent start`, or `pane split`
fails, use native subagents for agents and your own shell for tests — the
same scripts, the same records — and note the fallback in the report. This
plugin also ships to Codex, opencode, and Kilo, which have no Herdr; the
fallback is their normal path, not a degraded one.
