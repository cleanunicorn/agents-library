---
name: install-agents
description: >-
  Install the library's maintenance agents into the current project and
  optionally schedule them to run periodically through Claude Code schedules,
  GitHub Actions, or cron. Use when the user wants to install the agents or
  put a repo on recurring maintenance. Not for running one agent once (act as
  it directly) or installing this plugin (/plugin).
---

# install-agents

## Overview

Install the library's single-purpose maintenance agents into
`.claude/agents/` and put them on a recurring schedule, each run producing at
most one small reviewable PR.

## When to use

Use when the user wants the agents installed in a repo or on recurring
maintenance. To run one agent once, act as it directly; to install this
plugin, use `/plugin`.

## What good looks like

- **Find the sources, never invent them.** Use `$CLAUDE_PLUGIN_ROOT/agents/`,
  else `agents/` at the repo root with `name:` frontmatter, else the plugin
  caches under `~/.claude/plugins/` and `~/.codex/plugins/cache/`, else ask
  for the checkout path. If none exist, report where you looked and stop.
- **Target the repo root** (`git rev-parse --show-toplevel`). Outside git,
  warn that agents expect a repo (each run branches and opens a PR).
- **One confirmation covers everything.** Propose agents (default all),
  cadence (default weekly) and mechanism, noting what is fresh versus an
  update (existing `.claude/agents/`, `periodic-agents.yml`, schedules). Skip
  the ask for choices the user already made. "Install only" and "install
  nothing" are valid.
- **Stagger runs so only one agent runs at a time.** Weekly default, 06:00
  UTC in alphabetical order: architect Mon, deadwood Tue, docbot Wed,
  refactor Thu, sentinel Fri, testforge Sat, uidesigner Sun, uxpolish Mon
  12:00. Daily: separate hours. Monthly: separate days stepping by 3.
- **Pick the mechanism by preference, else in this order**: Claude Code
  scheduled agents (one per agent, via `CronCreate` or a `/schedule` skill;
  no secrets needed), then GitHub Actions if there is a GitHub remote, then
  local cron lines.
- **GitHub Actions** goes in exactly `.github/workflows/periodic-agents.yml`:
  one `schedule:` cron per agent, a case mapping `github.event.schedule` to
  the agent, a `workflow_dispatch` `agent` input, `contents: write` and
  `pull-requests: write` permissions, checkout with `fetch-depth: 0`, then
  `anthropics/claude-code-action@v1` with the run prompt. Verify input names
  against that action's README rather than guessing. Tell the user it needs
  the `ANTHROPIC_API_KEY` secret and the repo setting allowing Actions to
  create pull requests. Add dependency setup steps if lint or tests need them.
- **The run prompt**, identical for every mechanism: read
  `.claude/agents/<name>.md` and act as that agent for exactly one run; learn
  the project, pick one problem and fix every instance of it, verify with the
  project's linter and tests, open a reviewable PR, never commit to the
  default branch; first check open PRs from earlier runs, and if one covers
  the same ground or nothing qualifies, stop and report.
- **Re-runs are upgrades**: show what would change, and never duplicate an
  agent's schedule.

## Boundaries

- Never overwrite a differing installed agent without the user's per-agent
  approval; show the diff first (it is usually local customization).
- Modify the user's crontab only on explicit approval; otherwise just show
  the lines, and note the permission tradeoff for unattended runs rather than
  recommending skipped permissions.
- Don't schedule an agent whose install failed.
- Suggest committing `.claude/agents/` and the workflow, unless `.claude/`
  is gitignored.

## Scripts

`scripts/install-agents.sh <source-dir> [--force] [agent ...]`, run from the
repo root, copies each agent (all if none named) into `.claude/agents/` and
seeds an empty journal in `.claude/agents/journals/`. Status lines:
`INSTALLED`, `IDENTICAL` (nothing to do), `CONFLICT` (differs, left alone),
`UPDATED` (overwritten, `--force` only), `JOURNAL` (newly seeded; existing
journals are never touched), `FAILED` (reason on stderr). Exit 1 is a fatal
setup or input error, 2 conflicts, 3 any `FAILED` (wins over 2). To keep a
conflicting copy, record "kept local version".

## Output

A short ledger: each agent's status and the journals seeded; the mechanism and
each agent's slot (or "not scheduled"); what the user must still do before
the first run; and how to change it later (re-run this skill, or delete
`.claude/agents/<name>.md`, its journal, and its schedule entry).
