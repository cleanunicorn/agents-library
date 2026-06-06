# Agents Library

A set of stack-agnostic, single-purpose coding agents. Each agent does **one small, focused, well-verified change per run** and opens a reviewable pull request — never committing directly to the main branch.

These are general-purpose definitions: they reference *roles* (linter, test suite, architecture, auth model) rather than any specific language, framework, or tooling. Point one at a codebase and it learns that project's conventions before acting.

See [AGENTS.md](AGENTS.md) for the shared working guide (orientation, workflow, communication, and quality bars) that applies to every agent here.

## Install (Claude Code plugin)

This repo is a Claude Code plugin marketplace. Installing it gives you the
`/review-pr` and `/batch-merge-prs` skills plus all seven agents as subagents.

```
/plugin marketplace add cleanunicorn/agents-library
/plugin install agents-library@agents-library
```

Then start a new session. The agents become subagents (e.g. `architect`,
`refactor`, `testforge`) and the skills are available as `/review-pr` and
`/batch-merge-prs`.

Outside a session, the same works from the CLI:

```
claude plugin marketplace add cleanunicorn/agents-library
claude plugin install agents-library@agents-library
```

To update later, push to the repo and run `/plugin marketplace update agents-library`.

## The PR Review Skill

[`review-pr`](skills/review-pr/SKILL.md) reviews the work on your current branch
before you finalize it — the reviewer you start in a fresh agent after
implementing a change. It orients on the project, computes the local branch
diff, fans out nine specialized review sub-agents (correctness, architecture,
dead code, docs, refactor, testing, UX polish, security, conventions),
consolidates their findings into one ranked list, and then either applies a
chosen subset or runs an autonomous improve-until-converged loop — every applied
fix gated on the project's lint and tests. No GitHub remote required; it works
on the local diff before a PR exists.

## The Batch PR Merge Skill

[`batch-merge-prs`](skills/batch-merge-prs/SKILL.md) triages the project's open
pull requests and collects the trivial ones onto a branch you name. It lists
every open PR, fans out one review sub-agent per PR that reads the diff and
judges it across four lenses (size/scope, change type, mergeability/CI, and an
actual correctness read), then recommends include / review / skip with
reasoning. It consolidates the verdicts into one ranked decision table, lets you
pick which to take, and locally `git merge`s the chosen PRs into your target
branch — aborting cleanly on conflict — before reporting a final ledger. The
sub-agents only assess; you confirm what merges. Nothing is pushed and no PRs are
closed on GitHub. Requires the `gh` CLI.

## The Agents

| Agent | Emoji | Focus |
|-------|-------|-------|
| [Architect](agents/architect.md) | 🏗️ | Align code with the project's established architecture |
| [DeadWood](agents/deadwood.md) | 🌲 | Remove dead code without changing live behavior |
| [DocBot](agents/docbot.md) | 📝 | Fill documentation gaps without changing code |
| [Refactor](agents/refactor.md) | 🔧 | Micro-refactors that improve clarity without changing behavior |
| [Sentinel](agents/sentinel.md) | 🛡️ | Light security hygiene (auth guards, error leakage, hardcoded config) |
| [TestForge](agents/testforge.md) | 🧪 | Fill test gaps without changing production code |
| [UXPolish](agents/uxpolish.md) | 🎨 | Frontend UX friction fixes without touching contracts |

## Shared Conventions

Every agent follows the same operating model:

- **How Much to Do Per Run** — one *Primary* change, up to two closely-related same-kind changes, and an *"Also spotted"* report of everything else found but not touched.
- **Learn the project first** — read the docs and copy the prevailing patterns; refactor *toward* the existing style, never toward a personal preference.
- **Verify before committing** — run the project's linter and test suite; evidence before claims.
- **Reviewable PRs** — branch off main, Conventional Commits title, structured PR body, and a confidence indicator (🟢 / 🟡 / 🔴).
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
