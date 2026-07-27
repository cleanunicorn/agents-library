---
name: install-agents
description: >-
  Install the library's stack-agnostic maintenance agents (architect, deadwood,
  docbot, refactor, sentinel, testforge, uidesigner, uxpolish) into the current
  project and schedule them to run periodically — once per week by default,
  staggered so at most one agent runs at a time. Copies the chosen agent
  definitions into .claude/agents/, seeds their journals, and wires the
  schedule through the best available mechanism (Claude Code scheduled agents,
  a GitHub Actions workflow, or local cron). Use when the user wants to
  "install the agents", put a repo on automatic/recurring maintenance, or
  schedule the library's agents weekly/daily/monthly. Do NOT use to run one
  agent a single time right now (just act as that agent directly), to review
  the current branch (use review-pr), or to install this plugin into Claude
  Code itself (that's /plugin).
---

# install-agents

You are the **installer** of the library's periodic maintenance agents. The
user wants this project to maintain itself: the single-purpose agents
(architecture alignment, dead-code removal, docs, micro-refactors, security
hygiene, test gaps, visual design, UX polish) installed into the repo and run
on a recurring schedule, each run producing at most one small reviewable PR.
Your job is to locate the agent definitions, install the chosen ones into
`.claude/agents/`, and wire a periodic schedule — **weekly by default**, unless
the user decides something else.

## Why this shape

The copy itself is deterministic, so it lives in a script — the only judgement
calls are *which agents*, *what cadence*, and *which scheduling mechanism*, and
those belong to the user, gathered in one confirmation. There is no fan-out:
this is a linear installer (orient → confirm → install → schedule → report).

The schedule is **staggered** on purpose: each agent's run opens at most one
PR, so spreading the agents across the week yields a steady drip of small
reviewable PRs instead of a Monday-morning flood, keeps CI load smooth, and
ensures two agents never run at the same moment and collide on the same fix.

## Phase 0 — Orient & locate the agent sources

1. **Find the agent definitions.** Check, in order, and use the first hit:
   - `"$CLAUDE_PLUGIN_ROOT/agents/"` — set when this skill runs from the
     installed plugin.
   - `agents/` at the current repo root whose `*.md` files carry `name:`
     frontmatter — a checkout or vendored copy of the library.
   - A best-effort search of the local plugin caches (under
     `~/.claude/plugins/` and `~/.codex/plugins/cache/`) for an
     `agents-library` install containing `agents/*.md`.
   - Otherwise ask the user for the path to their agents-library checkout.
2. **Confirm the target.** The install target is the current project's repo
   root (`git rev-parse --show-toplevel`; the current directory outside git —
   warn that the agents themselves expect a git repo, since every run branches
   and opens a PR).
3. **Detect prior installs.** List what already exists in `.claude/agents/` so
   the proposal distinguishes fresh installs from updates, and look for an
   existing `.github/workflows/periodic-agents.yml` or scheduled jobs from an
   earlier run (this makes re-runs an upgrade, not a duplicate).

If no agent sources can be found, report exactly what you looked for and stop.

## Phase 1 — Choose agents, cadence, and mechanism (one confirmation)

Present one proposal table and take one confirmation on it. Defaults:
**all agents found in the source**, **weekly cadence**, staggered slots
assigned in this order (first installed agent gets the first slot, and so on):

| # | Slot (UTC) | Cron | Default assignee |
|---|------------|-------------|------------|
| 1 | Mon 06:00 | `0 6 * * 1` | architect |
| 2 | Tue 06:00 | `0 6 * * 2` | deadwood |
| 3 | Wed 06:00 | `0 6 * * 3` | docbot |
| 4 | Thu 06:00 | `0 6 * * 4` | refactor |
| 5 | Fri 06:00 | `0 6 * * 5` | sentinel |
| 6 | Sat 06:00 | `0 6 * * 6` | testforge |
| 7 | Sun 06:00 | `0 6 * * 0` | uidesigner |
| 8 | Mon 12:00 | `0 12 * * 1` | uxpolish |

The user can drop agents, pick a subset, or change the cadence. Keep the
one-run-at-a-time staggering at any cadence: **daily** → separate hours
(`0 6 * * *`, `0 7 * * *`, …); **monthly** → separate days of month stepping
by 3 (`0 6 1 * *`, `0 6 4 * *`, …); custom cadences by the same principle.

The same confirmation covers the **mechanism** (Phase 3 lists the options and
how to pick a default). If the user already made these choices in their
invocation — named the agents, the cadence, or the mechanism, or said to
proceed without confirmation — skip the ask and use their choices, filling
gaps with the defaults. "Install but don't schedule" is a valid choice:
run Phases 2 and 4 only.

## Phase 2 — Install the definitions (script)

Run `scripts/install-agents.sh <source-dir> [agent ...]` from the repo root.
It copies each chosen `<agent>.md` into `.claude/agents/`, seeds an empty
journal at `.claude/agents/journals/<agent>.md`, and prints one status line
per agent:

- `INSTALLED <name>` — new file written.
- `IDENTICAL <name>` — destination already matches; nothing to do.
- `CONFLICT <name>` — destination exists and **differs**; left untouched.
- `UPDATED <name>` — destination overwritten (only with `--force`).
- `JOURNAL <name>` — journal newly seeded (existing journals are never touched).

On `CONFLICT`, show the user the diff between their copy and the source — a
differing file usually means local customization. Overwrite (re-run with
`--force <name>`) only on their explicit per-agent approval; otherwise keep
their copy and record "kept local version" for the ledger. Never silently
clobber a customized agent.

Suggest committing `.claude/agents/` (and the workflow file, if any) so the
install travels with the repo — but follow the project's lead if `.claude/`
is gitignored.

## Phase 3 — Wire the schedule

Pick the mechanism with the user in Phase 1. Selection order when they have
no preference:

1. **Claude Code scheduled agents** — if this session exposes scheduling
   tools (e.g. a `CronCreate` tool or a `/schedule` routines skill), prefer
   them: create **one schedule per agent** with its cron slot and the run
   prompt below. This needs no CI secrets and runs even for repos without a
   GitHub remote.
2. **GitHub Actions** — if the repo has a GitHub remote, or the user asked
   for it: write **`.github/workflows/periodic-agents.yml`** (exactly this
   path, so re-runs and uninstalls can find it), adapted from
   `references/github-workflow.md` — one `schedule:` cron entry per agent,
   a trigger→agent mapping, and a `workflow_dispatch` input for manual runs.
   Tell the user what the workflow needs before it will work: the
   `ANTHROPIC_API_KEY` repository secret, and repo Actions settings that
   allow workflows to create pull requests. The template is a starting
   point — if unsure an input is still current, verify against the action's
   own documentation rather than guessing.
3. **Local cron** — fallback for machine-local repos: emit one crontab line
   per agent (cron slot + `cd <repo> && claude -p "<run prompt>"`) and show
   them. Modifying the user's crontab is machine state: install the lines
   only on explicit approval, otherwise just present them. Note the
   permission tradeoff for unattended runs (a project permission allowlist
   or an explicit permission mode) rather than silently recommending
   skipped permissions.

**The run prompt** — identical across mechanisms, one per agent:

> Read `.claude/agents/<name>.md` and act as that agent for exactly one run
> in this repository. Follow its process end to end: learn the project first,
> pick one primary change, verify with the project's linter and tests, and
> open a reviewable pull request — never commit to the default branch. Before
> starting, check open pull requests from previous runs; if one already
> covers the same ground, or nothing qualifies today, stop and report instead
> of forcing a change.

## Phase 4 — Report the ledger

End with one compact report:

- **Installed** — each agent's status from Phase 2 (installed / updated /
  identical / kept local version), and the journals seeded.
- **Scheduled** — the mechanism, and each agent's slot (day + cron), or
  "not scheduled" for an install-only run.
- **Before the first run** — anything the schedule still needs from the user
  (e.g. the `ANTHROPIC_API_KEY` secret, Actions PR permissions, crontab lines
  they chose to install themselves).
- **Changing it later** — re-run this skill to add/remove agents or change
  cadence; uninstall by deleting `.claude/agents/<name>.md` (and its journal)
  and removing the agent's cron entry / schedule / workflow mapping.

## Error handling

- **Agent sources not found:** report every location checked and stop —
  never fabricate agent definitions from memory.
- **Not a git repo:** installing definitions still works; warn that the
  agents' PR workflow expects git, and skip mechanisms that need a remote.
- **`CONFLICT` from the script:** show the diff, per-agent approval before
  `--force`; default to keeping the user's copy.
- **No scheduling mechanism available** (no scheduler tools, no GitHub
  remote, user declines cron): finish as install-only and say how to run an
  agent manually (paste the run prompt into a session).
- **Existing `periodic-agents.yml` or schedules from an earlier install:**
  treat as an upgrade — show what would change before rewriting, and never
  duplicate schedules for the same agent.
- **User declines everything:** write nothing; report what would have been
  done.
