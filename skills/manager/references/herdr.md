# Workers in Herdr

Use this file when the host lists a `herdr` skill and its precondition holds:
`test "${HERDR_ENV:-}" = 1 && command -v herdr`. Load the `herdr` skill
first; it and the installed binary (`herdr <group>` with no subcommand prints
its syntax) overrule any command below.

Your pane stays the console. This is the explicit topology request required
by the Herdr skill: one full-size, watchable tab per worker in the current
workspace, grouped by `<slug>-` labels. Herdr supplies transport and live
context, with the same roles and rules as native workers.

## Your tab

On the first turn, once, label your own tab so the user can find the console
among the workers' tabs: run `bash <skill>/scripts/rename-herdr-tab.sh
manager`, `<skill>` being this skill's directory, from the project's working
directory — never `cd` into the skill first, or the label names the skill.
It renames `$HERDR_TAB_ID` to `manager <project>`,
where `<project>` is the git toplevel directory's name, else the working
directory's. It needs only `HERDR_ENV=1` and `HERDR_TAB_ID`, not this file's
precondition, so it also runs when workers are native. Outside Herdr it does
nothing; a failed rename prints one warning and never blocks startup. Do not
retry it or rename it per item.

## Start a worker

1. **Pick kinds.** `herdr agent` lists the kinds this Herdr knows; use the
   installed ones. Give planners and reviewers a kind different from the
   coordinator's.
2. **One tab per worker**, created when that worker is needed, in your own
   workspace only: `herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd
   <dir> --label "<slug>-<role>-<label>" --no-focus`. The coordinator's
   `<dir>` is the repository root, since it creates the worktree; every later
   worker's is that worktree, and a helper's (`references/console.md`
   § Helpers) the repository root. Add the kind's `--env` from § Pre-grants per
   kind, if any, to this command. Record `.result.tab.tab_id` and
   `.result.root_pane.pane_id` per worker in `<run_dir>/<slug>/tabs.md`. Never
   split your own pane, never `--current`, never a new workspace.
3. **Start the agent** in that tab's root pane under the tab's label, unique
   among live agents, with the role's **pre-grant** after `--`:
   `herdr agent start <slug>-planner-a --kind <kind> --pane <root pane id>
   -- <pre-grant args>`. Record the args in `tabs.md`. On `agent_not_ready`,
   read the pane before prompting.

### Pre-grants per kind

A helper launches with the planner, reviewer column. The args give each
role what its job needs (`references/console.md`
§ Approvals) so prompts rarely appear, while every escalation case still
surfaces as a prompt. A host's own default can approve silently what no flag
names, so each recipe also adds **ask rules** for the escalation commands —
`git push` with `--force`, `-f` or the main branch, `gh pr merge`, `gh pr
ready`, `git branch -D`, `git worktree remove`, `rm -rf` — that fire even
where routine work runs without a prompt. `<repo>` is the repository root: a
worktree's commits land in `<repo>/.git` (`git rev-parse --git-common-dir`),
outside the worktree. `<worktree>` is the item's worktree, which exists only
after the coordinator creates it, so only later workers start there.

| kind | coordinator | planner, reviewer — writes only to the run directory |
|------|-------------|------------------------------------------------------|
| claude | `--permission-mode auto --add-dir <run_dir> --add-dir <repo> --settings <claude ask>` | `--permission-mode dontAsk --add-dir <run_dir> --allowedTools Read Grep Glob "Edit(/<run_dir>/**)" "Write(/<run_dir>/**)" "Bash(git log:*)" "Bash(git diff:*)" "Bash(git show:*)"`; a reviewer adds `"Bash(<gate command>)"` |
| codex | `-C <repo> -s workspace-write -a on-request --add-dir <run_dir> --add-dir <repo>/.git`; every push, `gh` call and fetch then asks, and so does the first write to a worktree outside `<repo>`, which you answer for the session | `-C <worktree> -s read-only -a on-request`; its record write asks once and you answer it for the session, and so does a reviewer's gate that writes only to the run directory (`TMPDIR=<run_dir>`) |
| opencode, kilo | none; `tab create --env OPENCODE_CONFIG_CONTENT=<opencode ask>` (kilo: `KILO_CONFIG_CONTENT`) | the same `--env` with `"edit":"ask"` added; answer the run directory's prompts with **Allow always** (it lasts until that agent restarts) and reject a write anywhere else |
| any other kind | read `<kind> --help` at launch and use its persistent-allow or sandbox flags; with none, start it plain and answer its prompts | same, keeping writes to the run directory |

Why: claude's `auto` mode would approve a push to the main branch, so an ask
rule forces the prompt, loaded for that session only by `--settings`; its
deny rules repeat per other active item's worktree, or drop when there is
none. opencode and kilo allow every tool by default, so their ask rules come
in through the environment, for that agent only. codex has no per-command ask
rule and `-a on-request` leaves asking to the model, so its sandbox is the
prompt surface: without network, a remote write cannot run unasked.
`<main>` is the main branch:

```
<claude ask> = '{"permissions":{"deny":["Edit(/<other worktree>/**)","Write(/<other worktree>/**)"],"ask":["Bash(git push *--force*)","Bash(git push *-f*)","Bash(git push * <main>*)","Bash(gh pr merge *)","Bash(gh pr ready *)","Bash(git branch -D *)","Bash(git worktree remove *)","Bash(rm -rf *)"]}}'
<opencode ask> = '{"permission":{"bash":{"git push*--force*":"ask","git push*-f*":"ask","git push* <main>*":"ask","gh pr merge*":"ask","gh pr ready*":"ask","git branch -D*":"ask","git worktree remove*":"ask","rm -rf*":"ask"}}}'
```

`<run_dir>` is absolute, so claude's rule reads `Edit(//tmp/…/**)`. Never
launch with `--dangerously-skip-permissions`, `--permission-mode
bypassPermissions`, `--dangerously-bypass-approvals-and-sandbox`, codex
`-a never`, or opencode or kilo `--auto`: `-a never` fails the action
silently and the others approve it silently — `--auto` even approves an ask
rule, since it passes everything not explicitly denied — so no escalation
case could reach you. Ask rules match a command as written, so a variant can
slip past them; `references/console.md` § Approvals checks afterwards. Never
pass args that write a host's global settings.

`tab create` or `agent start` failing falls back to a native subagent for
that worker, retried once under SKILL.md rule 8; record the degradation on
the board. That worker loses its pre-grant args and runs on your session's
permissions, so `references/console.md` § Native subagents' rules and its
worktree check apply to it. Parse every id from JSON; never derive one from
a listing.

## Drive

- **Prompt** with the verbatim brief, the path its record goes to —
  `<run_dir>/<slug>/<role>-<label>.md` — and its result path beside it,
  `<role>-<label>.result`. Tell the worker to save its result block
  (`references/console.md` § Results) there and reply with that path. Read
  only that file: never the record, and never the pane's scrollback for a
  result.
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
- **`blocked`** means an approval or a question UI. Read just the prompt with
  `herdr agent read <name> --source recent-unwrapped --lines 40` and classify it — role, action,
  target — against `references/console.md` § Approvals:
  - **Routine:** choose the persistent option the menu offers ("Allow
    always", "don't ask again", "for this session") that writes no settings
    file outside the item's worktree (`references/console.md` § Approvals)
    with `herdr agent
    send-keys <name> <keys>` — `agent prompt` is refused while blocked — and
    confirm any follow-up dialog. In opencode 1.19.0 that is `right`,
    `enter`, then `enter` on "Always allow … until OpenCode is restarted".
    Add the row to the board's **approvals answered** list, then `herdr agent get
    <name>` until it is no longer `blocked`.
  - **An escalation case, or a question:** relay it to the user tagged
    `[<slug>]`, verbatim with its options and any secret redacted, and
    send exactly the option the user names with `send-keys`. Unattended,
    answer an escalation with reject and mark it `assumed`; the worker
    continues.
- **A timeout is not a failure to deliver.** Read the agent before sending
  anything again.

## Tear down

At an item's Phase 5, after its records are in the run directory: `herdr tab
close <recorded tab id>` for each of its tabs still open. Other items' tabs
stay. Close only tabs you created and recorded — never by label, never from a
listing, never a workspace, never `herdr server stop`.
