# Agents Library

A set of stack-agnostic, single-purpose coding agents. Each agent picks one problem, **fixes every instance of it in the repository**, verifies the result, and opens a reviewable pull request — never committing directly to the main branch.

These are general-purpose definitions: they reference *roles* (linter, test suite, architecture, auth model) rather than any specific language, framework, or tooling. Point one at a codebase and it learns that project's conventions before acting.

See [AGENTS.md](AGENTS.md) for the shared working guide (orientation, workflow, communication, and quality bars) that applies to every agent here. Notable changes live in [GitHub Releases](https://github.com/cleanunicorn/agents-library/releases) (see [Releasing](#releasing)).

<!-- toc:start -->
**Contents**

- [Install (Codex plugin)](#install-codex-plugin)
- [Install (Claude Code plugin)](#install-claude-code-plugin)
- [Install (opencode)](#install-opencode)
- [Install (Kilo Code)](#install-kilo-code)
- [Choose a skill](#choose-a-skill)
- [Update (Claude Code plugin)](#update-claude-code-plugin)
- [Update (Codex plugin)](#update-codex-plugin)
- [Update (opencode)](#update-opencode)
- [Update (Kilo Code)](#update-kilo-code)
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

## Install (Codex plugin)

Two steps — register the marketplace, then install the plugin from it:

```
codex plugin marketplace add cleanunicorn/agents-library
codex plugin add agents-library@agents-library
```

Codex's in-thread plugin UI takes this repository's URL,
`https://github.com/cleanunicorn/agents-library`, in place of the first command.

Registering the marketplace does not install the plugin. Check installation
with `codex plugin list -m agents-library --json`.

The marketplace manifest is
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json); the
plugin metadata is [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json).
Start a new Codex thread after installing so the skills load. To pick up later
changes, see [Update (Codex plugin)](#update-codex-plugin).

Something failed? See [Troubleshooting Codex](#troubleshooting-codex).

## Install (Claude Code plugin)

This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr`, `/review-design`, `/review-ux-psychology`, `/batch-merge-prs`,
`/triage-issues`, `/simplify-sweep`, `/describe-codebase`,
`/plan-feature`, `/install-agents`, and `/manager` skills plus all eight agents
as subagents.

Claude Code 2.1.286 uses SSH for this plugin by default: provide a GitHub SSH
key **or** [opt into HTTPS](#troubleshooting-claude-code). For the in-session
commands below, run `export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` before starting
`claude` if you want HTTPS.

```
/plugin marketplace add cleanunicorn/agents-library
/plugin install agents-library@agents-library
```

Then start a new session. The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr`,
`/review-design`, `/review-ux-psychology`, `/batch-merge-prs`, `/triage-issues`,
`/simplify-sweep`, `/describe-codebase`, `/plan-feature`, `/install-agents`, and
`/manager`.

Outside a session, the same works from the CLI:

```
claude plugin marketplace add cleanunicorn/agents-library
claude plugin install agents-library@agents-library
```

Something failed? See [Troubleshooting Claude Code](#troubleshooting-claude-code).

## Install (opencode)

With Git, Bash, and `opencode` installed, first clone the library via HTTPS:

```sh
git clone https://github.com/cleanunicorn/agents-library.git
cd agents-library
```

This repo is directly compatible with [opencode](https://opencode.ai).

**Work inside the clone** — just run `opencode` in the repo root. The
`.opencode/` directory is auto-discovered, no install step needed:

- `.opencode/agents/*.md` → the eight subagents (architect, deadwood, docbot,
  refactor, sentinel, testforge, uidesigner, uxpolish), each carrying
  `mode: subagent` so opencode registers them as subagents (invokable via
  `@mention` or dispatched by the orchestrator skills).
- `.opencode/skills/<name>/SKILL.md` → the ten orchestrator skills
  (`review-pr`, `review-design`, `review-ux-psychology`, `batch-merge-prs`,
  `triage-issues`, `simplify-sweep`, `describe-codebase`, `plan-feature`,
  `install-agents`, `manager`),
  loaded on demand via opencode's `skill` tool.

Both directories symlink to the canonical `agents/` and `skills/` at the repo
root, so there is a single source of truth.

**Install into other projects or globally** — run the installer script from
the repo root:

```
# Global: symlink all 8 agents + 10 skills into ~/.config/opencode/
./scripts/install-opencode.sh

# Project: copy into a specific project's .opencode/
cd /path/to/your/project
/path/to/agents-library/scripts/install-opencode.sh --project

# Pick specific items only
./scripts/install-opencode.sh review-pr simplify-sweep architect
```

Global installs use symlinks by default, so `git pull` in this repo updates
every linked install. Project installs use copies for self-containment. Run
`./scripts/install-opencode.sh --help` for all options.

Something failed? See [Troubleshooting opencode](#troubleshooting-opencode).

## Install (Kilo Code)

With Git, Bash, and `kilo` installed, first clone the library via HTTPS:

```sh
git clone https://github.com/cleanunicorn/agents-library.git
cd agents-library
```

This repo is directly compatible with [Kilo Code](https://kilo.ai). Kilo
auto-discovers a `.kilo/` config directory, so there is no marketplace or
manifest — the same install paths as opencode.

**Work inside the clone** — just run `kilo` in the repo root. The `.kilo/`
directory is auto-discovered, no install step needed:

- `.kilo/agents/*.md` → the eight subagents (architect, deadwood, docbot,
  refactor, sentinel, testforge, uidesigner, uxpolish), each carrying
  `mode: subagent` so Kilo registers them as subagents (dispatchable via the
  Task tool or by the orchestrator skills).
- `.kilo/skills/<name>/SKILL.md` → the ten orchestrator skills
  (`review-pr`, `review-design`, `review-ux-psychology`, `batch-merge-prs`,
  `triage-issues`, `simplify-sweep`, `describe-codebase`, `plan-feature`,
  `install-agents`, `manager`),
  loaded on demand via Kilo's `skill` tool.

Both directories symlink to the canonical `agents/` and `skills/` at the repo
root, so there is a single source of truth.

**Install into other projects or globally** — run the installer script from
the repo root:

```
# Global: symlink all 8 agents + 10 skills into ~/.config/kilo/
./scripts/install-kilo.sh

# Project: copy into a specific project's .kilo/
cd /path/to/your/project
/path/to/agents-library/scripts/install-kilo.sh --project

# Pick specific items only
./scripts/install-kilo.sh review-pr simplify-sweep architect
```

Global installs use symlinks by default, so `git pull` in this repo updates
every linked install. Project installs use copies for self-containment. Run
`./scripts/install-kilo.sh --help` for all options.

Something failed? See [Troubleshooting Kilo Code](#troubleshooting-kilo-code).

## Choose a skill

Pick the skill that matches the job:

- **Deliver work:** [`/manager`](#the-manager-skill) or [`/plan-feature`](#the-feature-planning-skill).
- **Review or improve:** [`/review-pr`](#the-pr-review-skill), [`/review-design`](#the-review-design-skill), [`/review-ux-psychology`](#the-ux-psychology-review-skill), or [`/simplify-sweep`](#the-simplify-sweep-skill).
- **Handle project queues and maintenance:** [`/batch-merge-prs`](#the-batch-pr-merge-skill), [`/triage-issues`](#the-issue-triage-skill), or [`/install-agents`](#the-install-agents-skill).
- **Understand a codebase:** [`/describe-codebase`](#the-describe-codebase-skill).

### The Manager Skill

[`/manager`](skills/manager/SKILL.md) delivers a work item end to end by
directing a small team of coding agents — at most five per item. The agent you
invoke it on is the manager and your single point of contact: it asks its
clarifying questions at the start, before any planner runs.

One or two planners — two when the design is contested — each write an
independent plan with `plan-feature`. A coordinator, which wrote none of them,
runs a SWOT analysis on each plan, merges the best decisions into one plan
that opens with a Progress checklist, and implements it in a dedicated
worktree as one PR. An independent reviewer — two for security, stored data,
or a public contract — runs `review-pr`; every finding is confirmed, refuted,
or kept open as uncertain, with evidence, before the confirmed ones are fixed,
and the manager re-checks the fix commits itself. Planners and reviewers use a
different agent kind (such as Claude, Codex, or opencode) from the coordinator
when the host offers one. Inside the Herdr terminal multiplexer, with its `herdr`
skill installed, each team member runs as a live agent in its own tab of your
current workspace, so you can watch each one work. Several work items run one after another, each with
its own PR. It never merges the PR.

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

[`/batch-merge-prs`](skills/batch-merge-prs/SKILL.md) triages the project's open
pull requests and collects approved trivial ones onto a branch you name. Each PR
is assessed for scope, type, correctness, CI, and mergeability before you choose
what to include. Merges are local and abort cleanly on conflict; nothing is
pushed or closed on GitHub. Requires the `gh` CLI.

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

## Update (Claude Code plugin)

Update the installed plugin, then restart Claude Code to apply the changes:

```sh
claude plugin update agents-library@agents-library
```

Check `claude plugin list --json` for the installed scope. To target a project
install explicitly, run from that project's directory:

```sh
claude plugin update agents-library@agents-library --scope project
```

Claude Code 2.1.286 auto-detects the update scope; older versions may differ.

Something failed? See [Troubleshooting Claude Code](#troubleshooting-claude-code).

## Update (Codex plugin)

[Refresh the Git marketplace](https://developers.openai.com/plugins/build/plugins)
and start a new Codex thread:

```sh
codex plugin marketplace upgrade agents-library
```

Omit the marketplace name to refresh all configured Git marketplaces.

Something failed? See [Troubleshooting Codex](#troubleshooting-codex).

## Update (opencode)

The update path depends on how you installed:

- **Working inside the clone** — run `git pull` in the clone; no reinstall
  is needed for `.opencode/` discovery.
- **Global symlink install** — `git pull` in this repo updates every linked
  install automatically (the symlinks point here).
- **Copy installs** — pull the clone first, then refresh the destination. For
  a global copy, run `./scripts/install-opencode.sh --global --copy --force`
  from the clone. For a project copy:

  ```
  cd /path/to/your/project
  /path/to/agents-library/scripts/install-opencode.sh --project --force
  ```

Something failed? See [Troubleshooting opencode](#troubleshooting-opencode).

## Update (Kilo Code)

As with opencode, update the source clone before refreshing copies:

- **Working inside the clone** — run `git pull` in the clone; no reinstall
  is needed for `.kilo/` discovery.
- **Global symlink install** — `git pull` in this repo updates every linked
  install automatically (the symlinks point here).
- **Copy installs** — pull the clone first, then refresh the destination. For
  a global copy, run `./scripts/install-kilo.sh --global --copy --force`
  from the clone. For a project copy:

  ```
  cd /path/to/your/project
  /path/to/agents-library/scripts/install-kilo.sh --project --force
  ```

Something failed? See [Troubleshooting Kilo Code](#troubleshooting-kilo-code).

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
opencode/Kilo installers also need Bash and standard shell utilities
(including `cp`, `diff`, `ln`, `mkdir`, `mv`, `readlink`, `rm`) and a complete
local clone.
Keep the clone if you install symlinks; copy installs can survive its removal.

**opencode/Kilo installer errors (install or update):** the
[shared installer](scripts/install-host.sh) reports the following:

| Symptom | Diagnosis and remedy |
| --- | --- |
| `install-host.sh: No such file or directory` | The wrapper was copied or symlinked out of `scripts/`. Invoke the original wrapper by its path inside the clone; it needs the adjacent `install-host.sh`. |
| `FATAL: agents/ not found` or `skills/ not found` | The script is detached from a complete clone. Invoke the script inside the clone; invoking it by absolute path from another project is supported. |
| `CONFLICT <name>` (exit 2) | The destination differs. Inspect/back up customizations before rerunning with `--force`; pass selected names to limit replacement. |
| `FAILED <name>` (exit 3) | Read the adjacent shell error and check the destination. Repair that failure (for example permissions or disk space), then retry. |
| `… is a symlink — refusing to write through it` | The guard covers the global/project root and its `agents/`/`skills/` directories. Inspect the named path with `ls -ld`. For global scope, inspect/back up dotfile-managed links and targets before deliberately converting the blocked directory to a real directory; alternatively use `--project` with real directories. `--copy` does not bypass this guard. |

### Troubleshooting Claude Code

**Install: marketplace missing or plugin not found.** Check
`claude plugin marketplace list` and `claude plugin list --json`. Marketplace
registration and plugin installation are
[separate steps](https://code.claude.com/docs/en/plugin-marketplaces): run the
two commands in [Install (Claude Code plugin)](#install-claude-code-plugin).

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
for copies, rerun the matching command in [Update (opencode)](#update-opencode).
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
/path/to/agents-library/scripts/install-kilo.sh --project
```

Resolve any [installer error](#git-access-https-ssh-and-prerequisites) above.
Restart the [Kilo CLI](https://kilo.ai/docs/code-with-ai/platforms/cli) in that
project; these instructions target the CLI, not the editor extension.

**Update: old skills or broken links.** Pull the source clone first and refresh
copies using [Update (Kilo Code)](#update-kilo-code). For a global symlink
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

Every agent follows the same operating model:

- **How much to do per run** — one *Primary* problem, a *Sweep* of the whole repository that fixes every other instance of it in the same PR, and an *"Also spotted"* report of everything else found but not touched (instances that needed a judgement call are tagged `same-pattern`).
- **Fix it everywhere** — the PR body reports the exact search run for other instances and its count (`N found · N fixed · N left`). A *different* problem, however close by, still gets its own PR.
- **Look where the fix needs** — the project's docs and a well-built module, read as far as the change requires; refactor *toward* the existing style, never toward a personal preference.
- **Evidence before claims** — the linter and tests are the feedback loop, run without asking; the PR carries their output.
- **Numbers, not adjectives** — every claim in the PR body carries the value measured, the threshold it is judged against, and the command that produced it. "Not measured" beats a vague adjective; a qualitative claim cites the code path, rule, test, or before/after that makes it checkable.
- **Leave a guardrail** — each PR names what would now fail if the problem came back (a test, a lint rule, a CI check), or says why nothing is warranted.
- **Reviewable PRs** — a worktree off main, Conventional Commits title, structured PR body, and a confidence indicator (🟢 / 🟡 / 🔴).
- **Journal critical learnings only** — record recurring patterns, not routine work.

### Adapting to a Project

Each agent is written against generic roles. To use one on a specific codebase, give it (or its host project's docs) the concrete details:

- the lint, format, test, and build commands
- the architecture/layering conventions
- the auth and configuration model
- the test layout and naming conventions

The agents are designed to discover most of this themselves, but supplying it up front makes them sharper.

### Journals

Agents append durable, codebase-specific learnings to `agents/journals/<agent>.md`. These are intentionally empty here — they accumulate per project.

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
| opencode | Agent/skill symlink targets, stale or missing definitions, and installer smoke tests. |
| Kilo Code | Agent/skill symlink targets, stale or missing definitions, and installer smoke tests (shared with opencode via `scripts/install-host.sh`). |

It also checks shell and manifest JSON syntax, shared definition names and
required frontmatter fields, context ceilings (descriptions ≤ 60 words, per-file
word ceilings on agent and skill roots), the fix-everywhere contract
(`scripts/test-fix-everywhere.py`), this README's table of contents and the
in-page links in README.md, AGENTS.md, and templates/AGENTS.md
(`scripts/test-readme-toc.py`), and eval cases with `run_evals.py --dry-run`.
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
[Update (Claude Code plugin)](#update-claude-code-plugin) for how an installed
copy picks it up.

The skill evals are **not** part of any workflow — they spawn real agent runs
and stay manual-only (`python3 run_evals.py`, see [docs/evals.md](docs/evals.md)).
