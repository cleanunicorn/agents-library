# Agents Library

A set of stack-agnostic, single-purpose coding agents. Each agent picks one problem, **fixes every instance of it in the repository**, verifies the result, and opens a reviewable pull request — never committing directly to the main branch.

These are general-purpose definitions: they reference *roles* (linter, test suite, architecture, auth model) rather than any specific language, framework, or tooling. Point one at a codebase and it learns that project's conventions before acting.

See [AGENTS.md](AGENTS.md) for the shared working guide (orientation, workflow, communication, and quality bars) that applies to every agent here. Notable changes live in [GitHub Releases](https://github.com/cleanunicorn/agents-library/releases) (see [Releasing](#releasing)).

<!-- toc:start -->
**Contents**

- [Install](#install)
- [Choose a skill](#choose-a-skill)
- [Update](#update)
- [Troubleshooting](#troubleshooting)
- [About the agents](#about-the-agents)
- [Architect](#architect)
- [DeadWood](#deadwood)
- [DocBot](#docbot)
- [Refactor](#refactor)
- [Sentinel](#sentinel)
- [TestForge](#testforge)
- [UIDesigner](#uidesigner)
- [UXPolish](#uxpolish)
- [Maintain the library](#maintain-the-library)
<!-- toc:end -->

## Install

Clone the library and run its installer. It finds the agent hosts on your
machine and shows two checklists, with everything checked by default:

```sh
git clone https://github.com/cleanunicorn/agents-library.git
cd agents-library
./install.py
```

1. **Hosts**: Claude Code, Codex, opencode, and Kilo Code. Hosts whose CLI
   is on your `PATH` start checked.
2. **Agents and skills**: the eight agents and ten skills. Uncheck any you
   don't want. This screen appears only when opencode or Kilo is checked,
   because Claude Code and Codex install the plugin as a whole.

Arrows or `j`/`k` move, space toggles, `a` toggles all, enter confirms, and
`q` or Esc cancels without changing anything.

**Your choice is saved.** The installer saves your host choices and the items
you unchecked to `~/.config/agents-library/selection.json` (`$XDG_CONFIG_HOME` is respected),
and the next `./install.py` starts from it. Items the library adds later start
checked. Unchecking an item you already installed removes it, but only if it
is still the library's version. A file you changed is left in place and
reported as `KEPT`.

| Host | What the installer does | Item checklist applies |
| --- | --- | --- |
| Claude Code | `claude plugin install agents-library --marketplace cleanunicorn/agents-library`, which registers the marketplace and installs the plugin in one command | No: whole plugin |
| Codex | `codex plugin marketplace add cleanunicorn/agents-library`, then `codex plugin add agents-library@agents-library` | No: whole plugin |
| opencode | Symlinks into `~/.config/opencode/{agents,skills}/` | Yes |
| Kilo Code | Symlinks into `~/.config/kilo/{agents,skills}/` | Yes |

Restart the host afterwards (a new Claude Code session, a new Codex thread).
In Claude Code the agents become subagents (e.g. `architect`, `refactor`,
`testforge`) and the skills are available as `/review-pr`, `/review-design`,
`/review-ux-psychology`, `/batch-merge-prs`, `/triage-issues`,
`/simplify-sweep`, `/describe-codebase`, `/plan-feature`, `/install-agents`,
and `/manager`.

**Without the checklist** (scripts, CI, a remote shell), pass `--yes`. The
installer then uses the saved selection, or everything on a first run. Flags
change the selection and are saved the same way:

```sh
./install.py --yes                                # saved selection
./install.py --yes --hosts opencode,kilo          # choose hosts
./install.py --yes --skip manager,triage-issues   # uncheck (and remove) items
./install.py --yes --only review-pr,architect     # keep these, remove the rest
./install.py --yes --all                          # re-check every item
./install.py --list                               # hosts, items, what is saved
./install.py --yes --dry-run                      # show, change nothing
```

**Into one project**, run the installer from that project. Files are copied
instead of symlinked, Claude Code installs at project scope, Codex is
`SKIPPED` because it has no project scope, and the selection is saved in that
project's `.agents-library.json`:

```sh
cd /path/to/your/project
/path/to/agents-library/install.py --project
```

`--copy`, `--symlink`, and `--force` (replace items that differ) work in
either scope; `./install.py --help` lists every flag and status line. The
installer needs Python 3.9+ and nothing else. The checklist uses `curses`,
which Windows' Python lacks, so pass `--yes` there.

Something failed? See [Troubleshooting](#troubleshooting).

### Install without cloning (Claude Code, Codex)

The plugin hosts don't need the clone. Each host takes two steps, registering
the marketplace and then installing the plugin from it. Registering the
marketplace does not install the plugin.

Claude Code 2.1.286 uses SSH for this plugin by default, both here and through
the installer. Provide a GitHub SSH key **or**
[opt into HTTPS](#troubleshooting-claude-code). For the in-session commands,
run `export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` before starting `claude` if you
want HTTPS.

In Claude Code, run these one at a time. Pasting both together fails: the
prompt reads them as one command, and the second line becomes part of the
first command's argument.

1. Register the marketplace:

   ```
   /plugin marketplace add cleanunicorn/agents-library
   ```

2. Install the plugin from it:

   ```
   /plugin install agents-library@agents-library
   ```

The same from the CLI is
`claude plugin marketplace add cleanunicorn/agents-library` then
`claude plugin install agents-library@agents-library`. The installer runs
`claude plugin install agents-library --marketplace cleanunicorn/agents-library`,
which does both in one command.

In Codex, the same two steps:

1. Register the marketplace:

   ```
   codex plugin marketplace add cleanunicorn/agents-library
   ```

2. Install the plugin from it:

   ```
   codex plugin add agents-library@agents-library
   ```

These are the commands the installer runs.

Codex's in-thread plugin UI takes this repository's URL,
`https://github.com/cleanunicorn/agents-library`, in place of the first command.
Check installation with `claude plugin list --json` in Claude Code and
`codex plugin list -m agents-library --json` in Codex. The manifests are
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json) and
[`.codex-plugin/plugin.json`](.codex-plugin/plugin.json).

### Work inside the clone (opencode, Kilo Code)

Running `opencode` or `kilo` in the clone's root needs no install. They
auto-discover `.opencode/` and `.kilo/`, whose `agents/*.md` (eight subagents,
each carrying `mode: subagent`) and `skills/<name>/SKILL.md` (ten skills,
loaded on demand via the `skill` tool) are symlinks to the canonical `agents/`
and `skills/` at the repo root, so there is a single source of truth.

## Choose a skill

Pick the skill that matches the job:

- **Deliver work:** [`/manager`](#the-manager-skill) or [`/plan-feature`](#the-feature-planning-skill).
- **Review or improve:** [`/review-pr`](#the-pr-review-skill), [`/review-design`](#the-review-design-skill), [`/review-ux-psychology`](#the-ux-psychology-review-skill), or [`/simplify-sweep`](#the-simplify-sweep-skill).
- **Handle project queues and maintenance:** [`/batch-merge-prs`](#the-batch-pr-merge-skill), [`/triage-issues`](#the-issue-triage-skill), or [`/install-agents`](#the-install-agents-skill).
- **Understand a codebase:** [`/describe-codebase`](#the-describe-codebase-skill).

### The Manager Skill

![Manager workflow: three parallel item teams, each with a coordinator, planners, and reviewers. Plans feed implementation and tests, followed by independent review, a fix-and-recheck loop, final push and draft PR, CI, and a ready PR. Results return to the manager.](docs/assets/manager-workflow.png)

The manager launches every worker; three item teams can run concurrently. Each
coordinator combines independent plans and implements in its own worktree;
reviewers return findings for validation, fixes, tests, and re-checks. Local
review and testing finish before the final push creates the draft PR. CI
failures return to the same fix loop; the PR becomes ready only when the
tested commit matches the PR and CI, with no open findings.

[`/manager`](skills/manager/SKILL.md) turns this session into a console:
workers do the work while it briefs them, relays questions, and maintains a
status board. The session stays a console until you end it: every later
message — a new request, a question, a skill you invoke, "start an agent" —
goes to a worker on the same transport (a Herdr tab, or a native subagent),
and a board header records the mode so it survives a context summary. In Herdr it pre-grants each worker the access its role needs
at launch; as native subagents, which share its session's permissions, it
checks that session at intake and each read-only worker's worktree after
it. It answers routine permission prompts itself with the host's persistent
option, logging each on the board. Only five kinds go to you: actions the
skill forbids such as merging or force-pushing, destruction outside the item,
secrets or global settings, the project's ask-first list, and prompts it
cannot classify. Planners and reviewers still write only to the run
directory. It never edits code, plans, reviews, or runs tests itself,
even when asked. To keep its own context small, it reads only each worker's
few-line result block — status, record path, head SHA, gate exit, counts —
and hands full plans and reviews between workers by path. Three items run concurrently and a fourth queues, each in
its own worktree with one PR and at most five workers.

One or two independent `plan-feature` planners feed a coordinator's SWOT
merge and Progress checklist. The coordinator implements; one independent
`review-pr` reviewer (two for high risk) reviews. Findings are validated with
evidence before fixes; the raising reviewer audits refutations and re-checks
fix commits. Gate claims need a saved log at the branch head.

The deliverable is a PR that is fully tested and fully reviewed. It stays a
draft until the gate log, the PR head, and the CI log share one SHA, the
gate exits 0, every required CI check passes, and the last re-check leaves
no finding open. A failing check is fixed and re-checked like any other
finding. The PR body carries the evidence: Progress, the gate result, CI
status, and a findings table. With no remote or `gh`, the manager asks
whether a branch is acceptable; unattended, the item ends `blocked: no
remote`. The `direct`
playbook skips planning for an obvious edit, retaining review. Planners and
reviewers use a different agent kind from the coordinator when available.

With Herdr and its skill installed, each worker has a tab in your current
workspace; otherwise it uses native subagents. With neither, it refuses.
Transport instructions are local to each skill so either can be installed
alone. The manager never merges a PR.

### The Feature Planning Skill

[`/plan-feature`](skills/plan-feature/SKILL.md) turns a feature request into a
plan grounded in the current repository before coding starts: reuse and
integration points, acceptance criteria mapped to real tests and the command
that runs them, and an ordered checklist covering implementation, wiring, and
delivery risk. Missing test infrastructure becomes the first step. The plan
stays in chat unless you ask for a file, and a request to plan *and* implement
continues into implementation without asking again; no GitHub remote is
required.

### The PR Review Skill

[`/review-pr`](skills/review-pr/SKILL.md) reviews the work on your current branch
before you finalize it. Ten specialized reviewers inspect the local diff, and a
separate verification pass screens their findings before presenting a ranked
list. It can apply approved fixes or run an improve-until-converged loop behind
the project's lint and test gate; no GitHub remote is required.

### The Review Design Skill

[`/review-design`](skills/review-design/SKILL.md) is the design-focused
counterpart to `review-pr`: it reviews a view, component, frontend path, or
branch diff against the project's visual system and core UI principles. It
ranks findings across five design lenses, then can apply approved fixes or run
an improve-until-converged loop behind the lint and build gate. No `gh` or
remote is required.

### The UX Psychology Review Skill

[`/review-ux-psychology`](skills/review-ux-psychology/SKILL.md) is the
behavior-and-conversion counterpart to `review-design`. It reviews a screen,
flow, path, or branch diff against behavioral principles for a named product
metric, using rendered evidence when available and independently verifying each
finding. It can apply approved fixes or iterate behind the project's lint and
build gate; no `gh` or remote is required.

### The Batch PR Merge Skill

[`/batch-merge-prs`](skills/batch-merge-prs/SKILL.md) merges the pull requests
you name onto one new local branch (`batch/<YYYYMMDD-HHMM>` unless you name
it), skipping each PR main already contains and showing the evidence. A
conflicting PR is aborted with its files listed while the rest still merge. It
then runs the tests the project's own docs and CI call for, skipping any suite
marked as touching live or shared resources unless you authorize it. It names
the PR behind each failure and reviews the merged branch with `review-pr`.
Inside Herdr, agents get tabs and tests share a pane; otherwise it uses
native subagents and the shell. Its transport guide needs no manager install.
It answers its Herdr workers' routine permission prompts itself, logging each
answer, and relays to you only merges, pushes and other GitHub writes,
main-branch commits, destruction outside the run, secrets or global
settings, the project's ask-first list, and prompts it cannot classify.
Without a PR list it shows open PRs and waits for your selection. Nothing is
pushed or changed on GitHub. Requires the `gh` CLI.

### The Issue Triage Skill

[`/triage-issues`](skills/triage-issues/SKILL.md) triages the project's open
GitHub issues into a code-grounded action plan covering duplicates, easy wins,
needs-info cases, and larger work. Every GitHub write needs per-action approval;
approved easy wins are fixed in separate worktrees and pull requests behind the
project's lint and test gate. Requires the `gh` CLI.

### The Simplify Sweep Skill

[`/simplify-sweep`](skills/simplify-sweep/SKILL.md) surveys a target you choose —
the whole repository, a path/glob, or the current branch diff — for
**behavior-preserving** simplifications across redundancy, complexity, clarity,
and documentation. It ranks findings, then can apply approved changes or run an
improve-until-converged loop behind the project's lint and test gate. No `gh` or
remote is required.

### The Describe Codebase Skill

[`/describe-codebase`](skills/describe-codebase/SKILL.md) is the read-to-explain
counterpart to `review-pr`. It maps a whole repository or subsystem, or traces
one feature end to end, producing an orientation brief with `file:line`
evidence. The analysis is read-only; it writes `ARCHITECTURE.md` or updates
`AGENTS.md` only with explicit approval. No `gh` or remote is required.

### The Install Agents Skill

[`/install-agents`](skills/install-agents/SKILL.md) puts a project on automatic
maintenance by copying a chosen set into `.claude/agents/`, seeding journals,
and optionally scheduling staggered runs weekly by default. It supports Claude
Code schedules, GitHub Actions, and local cron, and preserves locally customized
agent files unless you explicitly approve an overwrite. Re-running upgrades or
extends an installation.

## Update

Pull the clone and rerun the installer:

```sh
git pull
./install.py --yes
```

- **opencode and Kilo symlinks** already point at the clone, so `git pull`
  updates them. The rerun links any items the library added.
- **Copies** (`--project` or `--copy`) differ from the pulled clone and report
  `CONFLICT` until refreshed. Inspect customizations, then rerun with
  `--force`, for example `/path/to/agents-library/install.py --project --yes --force`
  from the project.
- **Claude Code**: the installer reports an installed plugin as `OK` and
  does not update it. Update it, then restart Claude Code:

  ```sh
  claude plugin update agents-library@agents-library
  ```

  Check `claude plugin list --json` for the installed scope, and add
  `--scope project` from a project directory to target a project install.
  Claude Code 2.1.286 auto-detects the scope; older versions may differ.
- **Codex**: [refresh the Git marketplace](https://developers.openai.com/plugins/build/plugins)
  with `codex plugin marketplace upgrade agents-library`, then start a new
  thread. Omit the name to refresh all configured Git marketplaces.

Something failed? See [Troubleshooting](#troubleshooting).

## Troubleshooting

Find your host: [Claude Code](#troubleshooting-claude-code),
[Codex](#troubleshooting-codex), [opencode](#troubleshooting-opencode),
[Kilo Code](#troubleshooting-kilo-code).

### Git access: HTTPS, SSH, and prerequisites

This repository is public: **HTTPS clone, fetch, and pull need no GitHub
account, token, or SSH key**. SSH URLs (`git@github.com:…`) require an
[SSH key recognized by GitHub](https://docs.github.com/en/get-started/git-basics/about-remote-repositories).
For Claude Code's default SSH plugin install/update, provide a GitHub SSH key
or [opt into HTTPS](#troubleshooting-claude-code).

**Install or update fails to reach GitHub.** Check Git and anonymous HTTPS
access before changing host settings:

```sh
git --version
git ls-remote https://github.com/cleanunicorn/agents-library.git HEAD
```

If this fails, inspect the reported network/proxy error and Git URL rewrites
(`git config --get-regexp '^url\..*\.insteadof$'`); no output means no matching
rewrite. If HTTPS works but the host reports `Permission denied (publickey)`,
it is using SSH. Choose HTTPS using the host remedy below, or fix your SSH
configuration if you intend to use keys. `ssh-add -l` checks keys loaded in an
agent; an agent is only one way to supply an SSH key.

The plugin commands require Git and the corresponding host CLI on PATH.
[`install.py`](install.py) needs Python 3.9+ and a complete local clone. Keep
the clone if you install symlinks; copy installs survive its removal.

**Installer errors (install or update).** Each status line names
`<host>/<item>`, and the reason is printed on stderr. A `FATAL:` line exits 1
before anything is installed or saved. When a run prints both `CONFLICT` and
`FAILED`, it exits 3.

| Symptom | Diagnosis and remedy |
| --- | --- |
| `FATAL: not a terminal; pass --yes` | The checklist needs an interactive terminal. Pass `--yes`, plus `--hosts`/`--skip`/`--only` to choose without it. |
| `FATAL: cannot run the checklist on this terminal` or `cannot run the checklist: this Python has no curses module` | curses cannot drive this terminal (the message names `TERM`), or this Python has no `curses` module, as on Windows. Pass `--yes`, or set `TERM` to your terminal's type (for example `xterm-256color`). |
| `FATAL: agents/ or skills/ not found at …` | `install.py` was copied out of the clone. Run it by its path inside the clone; running it by absolute path from another project is supported. |
| `FATAL: saved selection … is malformed` or `cannot read saved selection` | Fix or delete the named JSON file. The installer won't overwrite a file it can't read. |
| `FATAL: cannot save selection` | The selection's directory or file isn't writable (the message names it). Fix its permissions, then rerun. |
| `FATAL: cancelled` | You pressed `q` or Esc in a checklist. Nothing was installed or saved. |
| `FATAL: unknown host` or `unknown agent or skill` | A name passed to `--hosts`, `--only`, or `--skip` isn't one the installer knows. `./install.py --list` prints the valid names. |
| `FATAL: bad arguments` | A flag is unknown, is missing its value, or can't be combined (`--copy` with `--symlink`). See `./install.py --help`. |
| `FATAL: no host selected and none found on PATH` | Every host is unchecked or saved as off, and none has its CLI on PATH. Pass `--hosts`, for example `--hosts opencode`. |
| `CONFLICT <host>/<item>` (exit 2) | The destination differs. Inspect/back up customizations, then rerun with `--force`, which replaces every item that printed `CONFLICT`. Don't narrow it with `--only` or `--skip`: they uncheck the other items, and an unchecked item the library installed is removed. |
| `FAILED claude/agents-library` or `FAILED codex/agents-library` (exit 3), stderr says `` `claude` is not on PATH `` | The host is checked (or saved as checked) but its CLI isn't installed. Install the CLI, or drop the host: uncheck it in the checklist or pass `--hosts` without it. |
| `FAILED claude/agents-library` or `FAILED codex/agents-library` (exit 3), stderr says `` `…` exited <n> `` | The host CLI ran and failed; its output follows on stderr. See that host's section below. |
| `FAILED <host>/<item>` (exit 3) | Read the error on stderr and check the destination. Repair that failure (for example permissions or disk space), then retry. |
| `… is a symlink; refusing to write through it` | The guard covers the global/project root and its `agents/`/`skills/` directories. Inspect the named path with `ls -ld`. For global scope, inspect/back up dotfile-managed links and targets before deliberately converting the blocked directory to a real directory; alternatively use `--project` with real directories. `--copy` does not bypass this guard. |

### Troubleshooting Claude Code

**Install: marketplace missing or plugin not found.** Check
`claude plugin marketplace list` and `claude plugin list --json`. Marketplace
registration and plugin installation are
[separate steps](https://code.claude.com/docs/en/plugin-marketplaces): run the
two commands in [Install without cloning](#install-without-cloning-claude-code-codex).

**Install/update: `Permission denied (publickey)`.** The failing clone uses
SSH, even if marketplace registration succeeded. For this public repository,
prefer HTTPS for the failing command:

```sh
CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin install agents-library@agents-library
CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin update agents-library@agents-library
```

Run the install or update command as needed; the same prefix can be used with
`claude plugin marketplace add`. This preference was confirmed by inspecting
Claude Code 2.1.286's GitHub URL selection; it is undocumented and
version-dependent. Adding an HTTPS marketplace URL alone does not change this
marketplace's separate GitHub plugin source.

**Update: `Plugin "agents-library" is not installed at scope <scope>`.** Check
`claude plugin list --json`; update with the matching `--scope` from the
project directory for project/local installs. If absent, install at the
intended scope instead. If commands succeed but skills remain old or missing,
restart the session.

### Troubleshooting Codex

**Install: `plugin … was not found in marketplace …`.** Check
`codex plugin marketplace list` for `agents-library`, then
`codex plugin list -m agents-library --json` for the plugin. If the marketplace
is absent, register it using an HTTPS URL:

```sh
codex plugin marketplace add https://github.com/cleanunicorn/agents-library.git
```

If registered but its snapshot lacks the plugin, refresh it, then install:

```sh
codex plugin marketplace upgrade agents-library
codex plugin add agents-library@agents-library
```

**Update: skills still absent or old.** Run the marketplace upgrade above,
check `codex plugin list -m agents-library --json`, and start a new thread.
If the plugin is not installed, run `codex plugin add` as above; registering
or refreshing a marketplace alone is not proof of installation. These CLI
commands were checked with Codex 0.159.2; see the
[official marketplace guidance](https://developers.openai.com/plugins/build/plugins).
For Git errors, use [Git access](#git-access-https-ssh-and-prerequisites).

### Troubleshooting opencode

**Install: agents or skills not discovered.** Run `opencode debug skill` in the
intended project to list available skills. Check that the installer succeeded
and files exist in `~/.config/opencode/{agents,skills}/` for a
global install or `.opencode/{agents,skills}/` in the project. These are
[opencode's agent directories](https://opencode.ai/docs/agents/) and
[skill directories](https://opencode.ai/docs/skills/).
Resolve any [installer error](#git-access-https-ssh-and-prerequisites) above,
then restart opencode in the intended project.

**Update: old skills or broken links.** Run `git pull` in the source clone;
for copies, rerun the installer as in [Update](#update).
If you moved/deleted a symlinked clone, `ls -l ~/.config/opencode/skills/` shows
the old targets. Restore the clone or rerun the installer from its new location
with `--force` after inspecting destination customizations. For a fresh
destination, choose `--copy` to avoid dependence on the clone; refresh copies
on later updates.

### Troubleshooting Kilo Code

**Install: global skills not discovered.** This installer targets
`~/.config/kilo/{agents,skills}/`, but current
[Kilo skill documentation](https://kilo.ai/docs/customize/skills) lists
`~/.kilo/skills/` as its global skill directory. Run `kilo debug skill` in the
intended project to list available skills. If your global install is absent
from that listing, use the documented `.kilo/skills/` project path:

```sh
cd /path/to/your/project
/path/to/agents-library/install.py --project --hosts kilo
```

Resolve any [installer error](#git-access-https-ssh-and-prerequisites) above.
Restart the [Kilo CLI](https://kilo.ai/docs/code-with-ai/platforms/cli) in that
project; these instructions target the CLI, not the editor extension.

**Update: old skills or broken links.** Pull the source clone first and refresh
copies using [Update](#update). For a global symlink
install, inspect `ls -l ~/.config/kilo/skills/`: moving/deleting the clone breaks
its links. Restore the clone or rerun the installer from the new clone with
`--force` after inspecting customizations. A project copy avoids dependence on
the clone's location; restart Kilo after refreshing it.

## About the agents

Eight agents, one section each below — the linked file is the full
definition, and every host loads them as subagents. Install them into any
project as weekly periodic agents with
[`/install-agents`](skills/install-agents/SKILL.md).

### Shared Conventions

Each agent file defines only a personality and a purpose — what it cares about,
what it leaves alone, and that it fixes one kind of problem everywhere it
occurs. How to work (orienting, verifying, opening a PR) comes from the host
project's own guide, such as its `AGENTS.md`, and the model's judgement.

### Adapting to a Project

Each agent is written against generic roles. To use one on a specific codebase, give it (or its host project's docs) the concrete details:

- the lint, format, test, and build commands
- the architecture/layering conventions
- the auth and configuration model
- the test layout and naming conventions

The agents are designed to discover most of this themselves, but supplying it up front makes them sharper.

### Journals

`/install-agents` seeds an empty journal per agent at `.claude/agents/journals/<agent>.md` for durable, codebase-specific notes. The copies in `agents/journals/` are intentionally empty — they accumulate per project.

## Architect

🏗️ **[Architect](agents/architect.md)** — Aligns code with the project's established architecture without changing behavior. Use when a layer bypasses its boundary, business code reads the environment directly, a shared helper is duplicated across modules, or equivalent operations return different shapes.

## DeadWood

🌲 **[DeadWood](agents/deadwood.md)** — Removes dead code without changing live behavior. Use for unused imports or variables, commented-out blocks, unreachable branches, orphaned files, stale TODO/FIXME comments, or dead parameters, once nothing references them — dynamic dispatch included.

## DocBot

📝 **[DocBot](agents/docbot.md)** — Fills documentation gaps without changing code. Use when a public function, class, or contract has no doc comment, a module's purpose is not obvious from its name, or a README or architecture note went stale after a change.

## Refactor

🔧 **[Refactor](agents/refactor.md)** — Behavior-preserving micro-refactors. Use to extract duplicated logic into a helper, replace a magic value with a named constant, flatten deep nesting with early returns, rename a vague identifier, or simplify redundant boolean logic. Not for bug fixes.

## Sentinel

🛡️ **[Sentinel](agents/sentinel.md)** — Light security-hygiene fixes without changing business logic. Use for a missing auth guard on a protected endpoint, internal error details reaching clients, a hardcoded secret or config value, missing input validation, or sensitive data in logs. Hygiene only, not vulnerability research.

## TestForge

🧪 **[TestForge](agents/testforge.md)** — Fills test-suite gaps without changing production code. Use to cover an untested error path or edge case, replace a status-only or truthiness assertion with a specific one, share a copy-pasted fixture, or stabilize a flaky test.

## UIDesigner

🖌️ **[UIDesigner](agents/uidesigner.md)** — Visual-design fixes using the project's existing tokens and components. Use for competing primary actions, off-scale spacing or type, contrast below WCAG AA, dark-mode or shadow inconsistencies, or mismatched icons. Interaction states and friction belong to UXPolish.

## UXPolish

🎨 **[UXPolish](agents/uxpolish.md)** — Frontend UX friction fixes without touching backend behavior or API contracts. Use to add a loading, empty, or error state, a confirmation for a destructive action, keyboard handling, an accessibility label, or a clearer button label. Visual-system fixes belong to UIDesigner.

## Maintain the library

### Local checks

Run the repository's local validation before opening a PR:

```sh
bash scripts/check.sh
```

The same command covers all four supported hosts:

| Host | Local coverage |
| --- | --- |
| Claude Code | Plugin/marketplace identity, GitHub source, agent and skill discovery paths, and the intentionally versionless manifest. |
| Codex | Plugin/marketplace identity, local source path, release version, interface metadata, availability policy, and skill discovery. |
| opencode | Agent/skill symlink targets, stale or missing definitions, and installer tests. |
| Kilo Code | Agent/skill symlink targets, stale or missing definitions, and installer tests (shared with every host via `install.py`, tested by `scripts/test-install.py` against stub host CLIs). |

It also checks shell and manifest JSON syntax, shared definition names and
required frontmatter fields, context ceilings (descriptions ≤ 60 words, per-file
word ceilings on agent and skill roots), the fix-everywhere contract
(`scripts/test-fix-everywhere.py`), batch-merge-prs' approval contract
(`scripts/test-batch-merge-approval.py`), this README's table of contents and the
in-page links in README.md, AGENTS.md, and templates/AGENTS.md
(`scripts/test-readme-toc.py`), one slash command per fenced block in every
Markdown file (`scripts/test-paste-blocks.py`), the manager's approval contract
(`scripts/test-manager-approval.py`), the manager's persistent console
(`scripts/test-manager-console.py`), the Herdr prompt-delivery gate
(`scripts/test-herdr-prompt-delivery.py`), skill-installer write failures and ledger
behavior (`scripts/test-install-agents.sh`), staged/unstaged review-target
regressions (`scripts/test-diff-target.sh`), the eval runner's offline
transcript parsing and delegation traces (`scripts/test-run-evals.py`), and
eval cases with `run_evals.py --dry-run`.
The command is local and manual: it starts no model runs, needs no credentials,
and changes no installed plugins. It requires `bash`, Python 3.9+, and the usual
Unix command-line tools.

These are repository packaging checks, not complete host schema validation or
behavioral evals in Claude/Codex. The frontmatter checks cover the library's
existing unquoted keys/names and block descriptions (`description: >-`), not
arbitrary YAML. Required fields must appear exactly once.
When Claude Code is installed, its manifest checks can also be run explicitly:

```sh
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

The missing-version warning for Claude is intentional; Codex owns the release
version. `claude plugin validate .` selects the marketplace in this repository,
so it must not be treated as validation of every skill and agent. The local gate
does not require either CLI or depend on their user-specific plugin caches.

### Skill Evals

Every skill ships an eval suite (`skills/<name>/evals/cases.json`) — at least
10 outcome-based cases each, including cross-triggering negatives that must
route to a *different* skill — executed by [`run_evals.py`](run_evals.py) at the repo
root. Each trial runs the prompt through a real agent in a clean, isolated
workspace (fixtures include fake `gh` shims, so no network is needed) and
grades outcomes, not whether the skill loaded. The runner also supports
ablation (`--ablation`) to detect skills the bare model can already replace.

Evals are **manual-only** — never wired to CI or git hooks. Start with
`python3 run_evals.py --dry-run`; see [docs/evals.md](docs/evals.md) for the
full guide and cost notes.

### Releasing

Releases are cut **automatically when a PR merges to main**, sized by the
Conventional-Commit prefix of the PR title
([.github/workflows/auto-release.yml](.github/workflows/auto-release.yml)).
The title format is enforced by a CI check
([.github/workflows/pr-title.yml](.github/workflows/pr-title.yml)) because the
title drives the version bump:

| PR title | Release |
| --- | --- |
| `feat!: …` (any `type!:`) | major |
| `feat: …` | minor |
| `fix: …`, `perf: …`, `refactor: …` | patch |
| anything else (`chore:`, `docs:`, free-form, `[skip release]`) | none |

The workflow bumps the version in `.codex-plugin/plugin.json`, commits
`release: vX.Y.Z` to main, tags it, and creates the GitHub release with
generated notes. **Those release notes are the changelog** — there is no
`CHANGELOG.md` to update. The Claude Code plugin stays versioned by commit SHA
rather than by release tag, so both tools track `main` — see
[Update](#update) for how an installed
copy picks it up.

The skill evals are **not** part of any workflow — they spawn real agent runs
and stay manual-only (`python3 run_evals.py`, see [docs/evals.md](docs/evals.md)).
