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

| kind | coordinator | planner, reviewer — writes only to the run directory | verified |
|------|-------------|------------------------------------------------------|----------|
| claude | `--permission-mode auto --add-dir <run_dir> --add-dir <repo> --settings <claude ask>` | `--permission-mode dontAsk --add-dir <run_dir> --allowedTools Read Grep Glob "Edit(/<run_dir>/**)" "Write(/<run_dir>/**)" "Bash(git log:*)" "Bash(git diff:*)" "Bash(git show:*)"`; a reviewer adds `"Bash(<gate command>)"` | in use |
| codex | `-C <repo> -s workspace-write -a on-request --add-dir <run_dir> --add-dir <repo>/.git`; every push, `gh` call and fetch then asks, and so does the first write to a worktree outside `<repo>`, which you answer for the session | `-C <worktree> -s read-only -a on-request`; its record write asks once and you answer it for the session, and so does a reviewer's gate that writes only to the run directory (`TMPDIR=<run_dir>`) | in use |
| opencode, kilo | none; `tab create --env OPENCODE_CONFIG_CONTENT=<opencode ask>` (kilo: `KILO_CONFIG_CONTENT`) | the same `--env` with `"edit":"ask"` added; answer the run directory's prompts with **Allow always** (it lasts until that agent restarts) and reject a write anywhere else | in use |
| pi | `tab create --env PI_MANAGER_ROLE=coordinator --env PI_MANAGER_RUN_DIR=<run_dir> --env PI_MANAGER_MAIN=<main> --env PI_MANAGER_DENY=<other worktrees>`; args `--no-extensions --no-mcp --no-approve -e <manager>/scripts/pi-permissions.mjs` | `tab create --env PI_MANAGER_ROLE=planner` (or `reviewer`, adding `--env PI_MANAGER_GATE=<gate command>`) `--env PI_MANAGER_RUN_DIR=<run_dir> --env PI_MANAGER_MAIN=<main>`; args `--no-extensions --no-mcp --no-approve -e <manager>/scripts/pi-permissions.mjs`; a write outside `<run_dir>` is blocked, and a command other than a read or the gate asks | smoke-checked 2026-10-24, pi 1.2.0 |
| gemini | `--approval-mode auto_edit --include-directories <run_dir>,<repo> --policy <run_dir>/<slug>/gemini-coordinator.toml`, that file holding `<gemini coordinator policy>` | `--approval-mode default --include-directories <run_dir> --policy <run_dir>/<slug>/gemini-reader.toml`, that file holding `<gemini reader policy>`; only a top-level `.md`, `.result` or `.log` write in `<run_dir>/<slug>/` is allowed, every other write is denied, and every shell command asks | --help-derived; unknown whether the installed release has `--policy` — when `gemini --help` does not list it, both cells are unknown: do not launch |
| cursor | unknown — do not launch under this role: no per-process rule can make an escalation ask, so an allow in the user's own `~/.cursor/cli-config.json` (`Shell(git)`, say) runs a force-push unasked | unknown — do not launch under this role: no per-process way to limit writes to the run directory | --help-derived |
| any other kind | read `<kind> --help` at launch and use its persistent-allow or sandbox flags; with none, start it plain and answer its prompts | same, keeping writes to the run directory | fallback |

Why: claude's `auto` mode would approve a push to the main branch, so an ask
rule forces the prompt, loaded for that session only by `--settings`; its
deny rules repeat per other active item's worktree, or drop when there is
none. opencode and kilo allow every tool by default, so their ask rules come
in through the environment, for that agent only. codex has no per-command ask
rule and `-a on-request` leaves asking to the model, so its sandbox is the
prompt surface: without network, a remote write cannot run unasked.
pi asks before no tool call at all (its `docs/security.md`), so the
skill's own extension `<manager>/scripts/pi-permissions.mjs` (`<manager>` is
this skill's directory) is the prompt surface: it reads the role from the
tab's environment, asks for each escalation command every time, blocks a
reader's write outside `<run_dir>`, and blocks every call when a setting is
missing; `--no-extensions` keeps other extensions from answering first.
Smoke check (herdr 0.9.5, pi 1.2.0): `rm -rf` raised the extension's
"Allow once / Deny" dialog and Deny left the target intact, a planner's
write into the worktree was blocked and its run-directory write allowed —
and Herdr reported the agent `done`, not `blocked`, while the dialog was up.
Every prompt a pi worker shows is this dialog, so treat a pi worker's `done`
with no saved result as § Drive's `blocked`: read the pane, then answer.
gemini's `--policy` file replaces the user's own policy directory for that
process (gemini-cli `packages/core/src/policy/config.ts`), and an `ask_user`
rule outranks the routine allow by priority. cursor reads permissions only
from `~/.cursor/cli-config.json` or the project's `.cursor/cli.json`, a
global file and a checked-in one, so nothing per-process can grant or limit
it. **verified** says how far each row is proven: `smoke-checked` — started
in a Herdr tab, prompted, and an escalation surfaced as a prompt;
`--help-derived` — read from the kind's help, source or official docs,
never run here, with every cell those do not settle reading `unknown`; `in
use` — the recipe the manager already runs; `fallback` — no recipe. A cell
that reads `unknown — do not launch` rules that kind out for that role.
`<main>` is the main branch:

```
<claude ask> = '{"permissions":{"deny":["Edit(/<other worktree>/**)","Write(/<other worktree>/**)"],"ask":["Bash(git push *--force*)","Bash(git push *-f*)","Bash(git push * <main>*)","Bash(gh pr merge *)","Bash(gh pr ready *)","Bash(git branch -D*)","Bash(git worktree remove *)","Bash(rm -rf *)","Bash(git -C * push*)","Bash(git -C * branch -D*)","Bash(git -C * worktree remove*)","Bash(git push *+*)","Bash(git push *:<main>*)","Bash(rm -fr *)","Bash(git push *--all*)","Bash(git push *--mirror*)"]}}'
<opencode ask> = '{"permission":{"bash":{"git push*--force*":"ask","git push*-f*":"ask","git push* <main>*":"ask","gh pr merge*":"ask","gh pr ready*":"ask","git branch -D*":"ask","git worktree remove*":"ask","rm -rf*":"ask","git -C * push*":"ask","git -C * branch -D*":"ask","git -C * worktree remove*":"ask","git push*+*":"ask","git push*:<main>*":"ask","rm -fr*":"ask","git push*--all*":"ask","git push*--mirror*":"ask"}}}'
```

```toml
# <gemini coordinator policy>
[[rule]]
toolName = "run_shell_command"
decision = "allow"
priority = 100

[[rule]]
toolName = "run_shell_command"
commandRegex = '.*\b(git(\s+-\S+(\s+[^-\s]\S*)?)*\s+push\b.*\s(--force|--all\b|--mirror\b|-[a-zA-Z]*f\b|\+\S)|git(\s+-\S+(\s+[^-\s]\S*)?)*\s+push\b.*\s(\S*:)?<main>(\s|$)|gh\s+pr\s+(merge|ready)\b|git(\s+-\S+(\s+[^-\s]\S*)?)*\s+branch\b.*\s(-[a-zA-Z]*D[a-zA-Z]*|--delete\s+--force|--force\s+--delete)(\s|$)|git(\s+-\S+(\s+[^-\s]\S*)?)*\s+worktree\s+remove\b|rm\s+(.*\s)?((-[a-zA-Z]*[rR]\S*|--recursive)\s+(.*\s)?(-[a-zA-Z]*f\S*|--force)|(-[a-zA-Z]*f\S*|--force)\s+(.*\s)?(-[a-zA-Z]*[rR]\S*|--recursive)|-[a-zA-Z]*([rR][a-zA-Z]*f|f[a-zA-Z]*[rR])))'
decision = "ask_user"
priority = 900

[[rule]]
toolName = ["write_file", "replace"]
argsPattern = '"file_path":"<other worktree>/'
decision = "deny"
priority = 950
```

```toml
# <gemini reader policy>; no shell allow, so every other command asks
[[rule]]
toolName = ["read_file", "grep_search", "glob", "list_directory"]
decision = "allow"
priority = 100

[[rule]]
toolName = "run_shell_command"
commandRegex = '.*\b(git(\s+-\S+(\s+[^-\s]\S*)?)*\s+push\b.*\s(--force|--all\b|--mirror\b|-[a-zA-Z]*f\b|\+\S)|git(\s+-\S+(\s+[^-\s]\S*)?)*\s+push\b.*\s(\S*:)?<main>(\s|$)|gh\s+pr\s+(merge|ready)\b|git(\s+-\S+(\s+[^-\s]\S*)?)*\s+branch\b.*\s(-[a-zA-Z]*D[a-zA-Z]*|--delete\s+--force|--force\s+--delete)(\s|$)|git(\s+-\S+(\s+[^-\s]\S*)?)*\s+worktree\s+remove\b|rm\s+(.*\s)?((-[a-zA-Z]*[rR]\S*|--recursive)\s+(.*\s)?(-[a-zA-Z]*f\S*|--force)|(-[a-zA-Z]*f\S*|--force)\s+(.*\s)?(-[a-zA-Z]*[rR]\S*|--recursive)|-[a-zA-Z]*([rR][a-zA-Z]*f|f[a-zA-Z]*[rR])))'
decision = "ask_user"
priority = 900

[[rule]]
toolName = ["write_file", "replace"]
decision = "deny"
priority = 150

[[rule]]
toolName = ["write_file", "replace"]
argsPattern = '"file_path":"<run_dir>/<slug>/[^"/]+\.(md|result|log)"'
decision = "allow"
priority = 200

[[rule]]
toolName = ["write_file", "replace"]
argsPattern = '"file_path":"[^"]*\.\.'
decision = "deny"
priority = 300
```

Write each policy file into `<run_dir>/<slug>/` from its block, placeholders
filled, before starting the gemini worker that loads it; the reader's policy
denies it a `.toml` write, so it cannot rewrite its own.

`<run_dir>` is absolute, so claude's rule reads `Edit(//tmp/…/**)`. Never
launch with `--dangerously-skip-permissions`, `--permission-mode
bypassPermissions`, `--dangerously-bypass-approvals-and-sandbox`, codex
`-a never`, opencode or kilo `--auto`, gemini `--yolo`, `-y` or
`--approval-mode yolo`, cursor `--force`, `-f` or `--yolo`, or pi without
`-e <manager>/scripts/pi-permissions.mjs`: `-a never` fails the action
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
