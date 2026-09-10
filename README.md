# Agents Library

A set of stack-agnostic, single-purpose coding agents. Each agent does **one small, focused, well-verified change per run** and opens a reviewable pull request — never committing directly to the main branch.

These are general-purpose definitions: they reference *roles* (linter, test suite, architecture, auth model) rather than any specific language, framework, or tooling. Point one at a codebase and it learns that project's conventions before acting.

See [AGENTS.md](AGENTS.md) for the shared working guide (orientation, workflow, communication, and quality bars) that applies to every agent here. Notable changes live in [GitHub Releases](https://github.com/cleanunicorn/agents-library/releases) (see [Releasing](#releasing)).

## Install (Codex plugin)

Two steps — register the marketplace, then install the plugin from it:

```
codex plugin marketplace add cleanunicorn/agents-library
codex plugin add agents-library@agents-library
```

Codex's in-thread plugin UI takes this repository's URL,
`https://github.com/cleanunicorn/agents-library`, in place of the first command.

If you registered the marketplace before this repo carried a Codex manifest,
`marketplace add` is a no-op (`alreadyAdded`) and leaves you on the old pinned
snapshot, so the second command fails:

```
Error: plugin `agents-library` was not found in marketplace `agents-library`
```

Refresh the snapshot first, then install:

```
codex plugin marketplace upgrade agents-library
```

Either way Codex records it as a Git marketplace named `agents-library` under
`[marketplaces.agents-library]` in `~/.codex/config.toml` — that name is what
updates it later — and `codex plugin list -m agents-library` reports whether the
plugin itself is installed. Registering the marketplace on its own does not
install it.

The marketplace manifest is
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json); the
plugin metadata is [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json).
Start a new Codex thread after installing so the skills load. To pick up later
changes, see [Updating](#updating).

## Install (Claude Code plugin)

This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr`, `/review-design`, `/review-ux-psychology`, `/batch-merge-prs`,
`/triage-issues`, `/simplify-sweep`, `/describe-codebase`,
`/plan-feature`, and `/install-agents` skills plus all eight agents as subagents.

```
/plugin marketplace add cleanunicorn/agents-library
/plugin install agents-library@agents-library
```

Then start a new session. The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr`,
`/review-design`, `/review-ux-psychology`, `/batch-merge-prs`, `/triage-issues`,
`/simplify-sweep`, `/describe-codebase`, `/plan-feature`, and `/install-agents`.

Outside a session, the same works from the CLI:

```
claude plugin marketplace add cleanunicorn/agents-library
claude plugin install agents-library@agents-library
```

## Install (opencode)

This repo is directly compatible with [opencode](https://opencode.ai).

**Work inside the clone** — just run `opencode` in the repo root. The
`.opencode/` directory is auto-discovered, no install step needed:

- `.opencode/agents/*.md` → the eight subagents (architect, deadwood, docbot,
  refactor, sentinel, testforge, uidesigner, uxpolish), each carrying
  `mode: subagent` so opencode registers them as subagents (invokable via
  `@mention` or dispatched by the orchestrator skills).
- `.opencode/skills/<name>/SKILL.md` → the nine orchestrator skills
  (`review-pr`, `review-design`, `review-ux-psychology`, `batch-merge-prs`,
  `triage-issues`, `simplify-sweep`, `describe-codebase`, `plan-feature`,
  `install-agents`),
  loaded on demand via opencode's `skill` tool.

Both directories symlink to the canonical `agents/` and `skills/` at the repo
root, so there is a single source of truth.

**Install into other projects or globally** — run the installer script from
the repo root:

```
# Global: symlink all 8 agents + 9 skills into ~/.config/opencode/
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

## Updating

Both tools **pin** what they fetched — Claude Code the plugin's commit SHA,
Codex the marketplace snapshot's revision and the copy installed from it. New
commits on `main` do not reach either until you update it.

In Claude Code, one command does it:

```
claude plugin update agents-library@agents-library
```

It refreshes the marketplace itself before resolving, so a separate
`claude plugin marketplace update agents-library` is not needed — and a
marketplace refresh on its own is *not* enough: it updates the catalog and
leaves the installed plugin on its old SHA.

The update reports the SHA it lands on — `updated from … to … for scope ….
Restart to apply changes.` — or tells you it is already at the latest, in which
case there is nothing to apply. A move never reaches a session already running:
restart it, or update from the in-session `/plugin` manager, which points you at
`/reload-plugins` instead. There is no `/plugin update` slash command.

`claude plugin update` defaults to `--scope user`. If you installed at project
scope, pass it explicitly from that project's directory:

```
claude plugin update agents-library@agents-library --scope project
```

`claude plugin list --json` shows the scope, pinned version, and install path of
every install.

In Codex, also one:

```
codex plugin marketplace upgrade agents-library
```

It re-points the marketplace snapshot at the latest `main` *and* refreshes the
installed copy from it, so no reinstall is needed — and it lands new commits
even when the plugin version is unchanged. Omit the name to refresh every
configured Git marketplace. Codex records the revision it pinned as
`last_revision` under `[marketplaces.agents-library]` in `~/.codex/config.toml`.
Start a new Codex thread afterwards.

In opencode, the update path depends on how you installed:

- **Working inside the clone** — no update step; `.opencode/` is always current.
- **Global symlink install** — `git pull` in this repo updates every linked
  install automatically (the symlinks point here).
- **Project copy install** — re-run the installer with `--force` to refresh:

  ```
  cd /path/to/your/project
  /path/to/agents-library/scripts/install-opencode.sh --project --force
  ```

### Troubleshooting

**`Permission denied (publickey)`.** `claude plugin install` and
`claude plugin update` clone the plugin source over SSH (`git@github.com:…`)
with no HTTPS fallback, so an unavailable key fails them with
`Failed to clone repository: … git@github.com: Permission denied (publickey)`.
The marketplace refresh does fall back to HTTPS, which is why
`claude plugin marketplace update` can succeed while the update right after it
fails. Check your agent: `ssh-add -l` reporting *Error connecting to agent*
means `$SSH_AUTH_SOCK` is stale. Load your key:

```
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
```

If you would rather not use SSH at all, `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`
switches both clones to HTTPS for that one command — it is not in
`claude plugin --help`, so treat it as undocumented and version-dependent:

```
CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin update agents-library@agents-library
```

The equivalent git-level rewrite works too, but note the blast radius: it
rewrites **every** `git@github.com:` URL on the machine, for fetch and push, in
every repo, and needs a credential helper for pushes that were using SSH keys.

```
git config --global url."https://github.com/".insteadOf git@github.com:
# undo: git config --global --unset url."https://github.com/".insteadOf
```

**`Failed to update plugin …: Plugin "agents-library" is not installed at scope
<scope>`.** The update is looking at a scope that has no install — most often
the default `--scope user` when yours is at project or local scope. Check the
scopes with `claude plugin list --json`. If the entry really is gone from
`~/.claude/plugins/installed_plugins.json`, reinstall it:

```
claude plugin install agents-library@agents-library --scope user
```

## The Feature Planning Skill

[`/plan-feature`](skills/plan-feature/SKILL.md) turns a feature request into a
plan grounded in the current repository before coding starts: reuse and
integration points, acceptance criteria mapped to real tests and the command
that runs them, and an ordered checklist covering implementation, wiring, and
delivery risk. Missing test infrastructure becomes the first step. The plan
stays in chat unless you ask for a file, and a request to plan *and* implement
continues into implementation without asking again; no GitHub remote is
required.

## The PR Review Skill

[`/review-pr`](skills/review-pr/SKILL.md) reviews the work on your current branch
before you finalize it. Ten specialized reviewers inspect the local diff, and a
separate verification pass screens their findings before presenting a ranked
list. It can apply approved fixes or run an improve-until-converged loop behind
the project's lint and test gate; no GitHub remote is required.

## The Review Design Skill

[`/review-design`](skills/review-design/SKILL.md) is the design-focused
counterpart to `review-pr`: it reviews a view, component, frontend path, or
branch diff against the project's visual system and core UI principles. It
ranks findings across five design lenses, then can apply approved fixes or run
an improve-until-converged loop behind the lint and build gate. No `gh` or
remote is required.

## The UX Psychology Review Skill

[`/review-ux-psychology`](skills/review-ux-psychology/SKILL.md) is the
behavior-and-conversion counterpart to `review-design`. It reviews a screen,
flow, path, or branch diff against behavioral principles for a named product
metric, using rendered evidence when available and independently verifying each
finding. It can apply approved fixes or iterate behind the project's lint and
build gate; no `gh` or remote is required.

## The Batch PR Merge Skill

[`/batch-merge-prs`](skills/batch-merge-prs/SKILL.md) triages the project's open
pull requests and collects approved trivial ones onto a branch you name. Each PR
is assessed for scope, type, correctness, CI, and mergeability before you choose
what to include. Merges are local and abort cleanly on conflict; nothing is
pushed or closed on GitHub. Requires the `gh` CLI.

## The Issue Triage Skill

[`/triage-issues`](skills/triage-issues/SKILL.md) triages the project's open
GitHub issues into a code-grounded action plan covering duplicates, easy wins,
needs-info cases, and larger work. Every GitHub write needs per-action approval;
approved easy wins are fixed in separate worktrees and pull requests behind the
project's lint and test gate. Requires the `gh` CLI.

## The Simplify Sweep Skill

[`/simplify-sweep`](skills/simplify-sweep/SKILL.md) surveys a target you choose —
the whole repository, a path/glob, or the current branch diff — for
**behavior-preserving** simplifications across redundancy, complexity, clarity,
and documentation. It ranks findings, then can apply approved changes or run an
improve-until-converged loop behind the project's lint and test gate. No `gh` or
remote is required.

## The Describe Codebase Skill

[`/describe-codebase`](skills/describe-codebase/SKILL.md) is the read-to-explain
counterpart to `review-pr`. It maps a whole repository or subsystem, or traces
one feature end to end, producing an orientation brief with `file:line`
evidence. The analysis is read-only; it writes `ARCHITECTURE.md` or updates
`AGENTS.md` only with explicit approval. No `gh` or remote is required.

## The Install Agents Skill

[`/install-agents`](skills/install-agents/SKILL.md) puts a project on automatic
maintenance by copying a chosen set into `.claude/agents/`, seeding journals,
and optionally scheduling staggered runs weekly by default. It supports Claude
Code schedules, GitHub Actions, and local cron, and preserves locally customized
agent files unless you explicitly approve an overwrite. Re-running upgrades or
extends an installation.

## Local checks

Run the repository's local validation before opening a PR:

```sh
bash scripts/check.sh
```

The same command covers all three supported platforms:

| Platform | Local coverage |
| --- | --- |
| Claude Code | Plugin/marketplace identity, GitHub source, agent and skill discovery paths, and the intentionally versionless manifest. |
| Codex | Plugin/marketplace identity, local source path, release version, interface metadata, availability policy, and skill discovery. |
| opencode | Agent/skill symlink targets, stale or missing definitions, and installer smoke tests. |

It also checks shell and manifest JSON syntax, shared definition names and
required frontmatter fields, and eval cases with `run_evals.py --dry-run`.
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

## Skill Evals

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

## Releasing

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
[Updating](#updating) for how an installed copy picks it up.

The skill evals are **not** part of any workflow — they spawn real agent runs
and stay manual-only (`python3 run_evals.py`, see [docs/evals.md](docs/evals.md)).

## The Agents

| Agent | Emoji | Focus |
|-------|-------|-------|
| [Architect](agents/architect.md) | 🏗️ | Align code with the project's established architecture |
| [DeadWood](agents/deadwood.md) | 🌲 | Remove dead code without changing live behavior |
| [DocBot](agents/docbot.md) | 📝 | Fill documentation gaps without changing code |
| [Refactor](agents/refactor.md) | 🔧 | Micro-refactors that improve clarity without changing behavior |
| [Sentinel](agents/sentinel.md) | 🛡️ | Light security hygiene (auth guards, error leakage, hardcoded config) |
| [TestForge](agents/testforge.md) | 🧪 | Fill test gaps without changing production code |
| [UIDesigner](agents/uidesigner.md) | 🖌️ | Visual-design fixes (hierarchy, spacing, type, color, depth) using the project's tokens |
| [UXPolish](agents/uxpolish.md) | 🎨 | Frontend UX friction fixes without touching contracts |

Install them into any project as weekly periodic agents with
[`/install-agents`](skills/install-agents/SKILL.md).

## Shared Conventions

Every agent follows the same operating model:

- **How Much to Do Per Run** — one *Primary* change, up to two closely-related same-kind changes, and an *"Also spotted"* report of everything else found but not touched.
- **Learn the project first** — read the docs and copy the prevailing patterns; refactor *toward* the existing style, never toward a personal preference.
- **Verify before committing** — run the project's linter and test suite; evidence before claims.
- **Numbers, not adjectives** — every claim in the PR body carries the value measured, the threshold it is judged against, and the command that produced it. "Not measured" beats a vague adjective.
- **Leave a guardrail** — each PR names what would now fail if the problem came back (a test, a lint rule, a CI check), or says why nothing is warranted.
- **Reviewable PRs** — a worktree off main, Conventional Commits title, structured PR body, and a confidence indicator (🟢 / 🟡 / 🔴).
- **Journal critical learnings only** — record recurring patterns, not routine work.

## Adapting to a Project

Each agent is written against generic roles. To use one on a specific codebase, give it (or its host project's docs) the concrete details:

- the lint, format, test, and build commands
- the architecture/layering conventions
- the auth and configuration model
- the test layout and naming conventions

The agents are designed to discover most of this themselves, but supplying it up front makes them sharper.

## Journals

Agents append durable, codebase-specific learnings to `agents/journals/<agent>.md`. These are intentionally empty here — they accumulate per project.
