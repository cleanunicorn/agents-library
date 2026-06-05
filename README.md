# Agents Library

A set of stack-agnostic, single-purpose coding agents. Each agent does **one small, focused, well-verified change per run** and opens a reviewable pull request — never committing directly to the main branch.

These are general-purpose definitions: they reference *roles* (linter, test suite, architecture, auth model) rather than any specific language, framework, or tooling. Point one at a codebase and it learns that project's conventions before acting.

See [AGENTS.md](AGENTS.md) for the shared working guide (orientation, workflow, communication, and quality bars) that applies to every agent here.

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
