# Agent guide

This is a generic working guide for coding agents operating in any repository.
It defines *how* to work — orientation, workflow, communication, and quality
bars — without assuming a particular language, framework, or stack. Pair it
with the single-purpose agents in [`agents/`](agents/), and supplement it with
a project-specific section once you know the codebase.

## Always start in a worktree

Before doing anything else, create a git worktree updated from `origin/main`
and do all work there — never on `main` directly, and never in a worktree
that's stale relative to `origin/main`.

```
git fetch origin
git worktree add ../<repo>-<task-slug> origin/main
cd ../<repo>-<task-slug>
```

If a worktree already exists for this task, `git fetch origin` and rebase or
merge it onto `origin/main` before continuing.

Follow the project's convention for where worktrees live if it has one (often a
gitignored directory such as `.claude/worktrees/`). If the harness offers a
worktree tool, use it — it does the same thing and moves the session into it.

## Orient yourself first

Before changing anything, build an accurate map of the project:

- Read the project docs (README, CONTRIBUTING, architecture notes) and any
  existing agent/contributor guides.
- Identify the **layering**: how entry points, business logic, data access,
  configuration, presentation, and background work are separated, and which
  layer is allowed to call which.
- Find the **shared infrastructure**: the central config object, shared
  dependencies/helpers, the data layer, and where cross-cutting concerns
  (auth, error reporting, logging) live.
- Find the **conventions that aren't written down** by reading a couple of
  well-built modules and copying their structure.
- Locate the **commands** that matter: how to lint, format, test, and build.

When in doubt, infer the rule from the prevailing pattern in the codebase —
not from your own preference.

## Conventions

- Match the surrounding code's conventions before importing your own.
- Wire new components where the codebase expects (router/module registry,
  DI container, dispatch table) — follow how existing ones are registered.
- Keep configuration in the central config object; don't read the environment
  directly from business code.
- Keep data-structure ownership where the project puts it (e.g. schema and
  migrations own structure; runtime code does not create it).
- Run the linter and the test suite before committing.

## Workflow

### Bug fixes

1. Reproduce the bug with a failing test FIRST. Do not attempt a fix before this.
2. Then fix. Prove the fix with the test passing.
3. **Close the gap that let it through.** A bug that reached a user got past
   whatever was supposed to stop it. Name that thing and fix it in the same PR.
   It is usually one of:
   - **The check didn't exist.** Add it.
   - **The check existed but didn't cover this shape.** This is the common case,
     and the more valuable half of the fix. A contrast test that asserts only
     the pairs someone thought to list; a size guard that reads a header the
     sender chose; a lint rule that never ran on this directory — each stays
     green while the defect ships. Widen it to the *shape* that broke, not just
     to the one instance.
   - **The check can't cover this.** Say so plainly, and name what does.

   Give the gap its own section in the PR. Why this was possible deserves as
   much review attention as what changed.
4. If the bug genuinely cannot be expressed as a test, say so explicitly and
   explain why.

### Feature work

- **One feature, one PR.** Ship the whole thing — code, tests, docs, and
  wiring — in a single pull request. Never split a feature into a chain of
  dependent PRs that would all land in the same sitting; a plan's milestones
  are checklist steps *within* that one PR. Split only when the pieces ship
  independently (separate deploys or releases, or one is useful on its own) —
  and when you think that applies, state the reason and ask first.
- "Small, focused diff" means *nothing unrelated in it* — not *less of the
  feature in it*. An incomplete feature is not a small change; it's a broken
  one.
- Build the smallest feedback loop before writing logic. If one doesn't exist,
  build it first.
- Acceptable loops: a failing test, a script that exercises the path, a
  command-line invocation, a REPL session.
- **Deleting the wrong feature is a result, not a failure.** When the model a
  feature is built on turns out not to match what the thing is used for, the fix
  is to collapse it, not to keep bolting onto it. Say so, propose the removal
  with what it costs, and — once agreed — lead the PR with what is *gone*: the
  net line count, the list of removed concepts, and an explicit **Kept:** line
  so a reviewer can check nothing they rely on left silently. A large negative
  diff needs the same evidence as a large positive one, not an apology.

### When stuck

- State the hypothesis: "I think X because Y. Test: Z."
- If a hypothesis fails twice, stop and re-examine assumptions instead of
  trying variants.
- **Suspect the measurement before the code.** When a result contradicts what
  you can see, or when a change you "proved" good breaks in the real world, the
  harness is a suspect: the fixture may be the wrong *shape* rather than merely
  too small, the number may be hardcoded where it should be read, the baseline
  may be measured against the wrong moment. Before deleting a working safeguard
  on the strength of an eval, check that the eval's inputs look like the inputs
  users actually send. Fix the instrument, re-run, and only then judge the code.
- Where a harness and the test suite both need the same fixtures, have them
  **share one definition** so they cannot drift apart and disagree later.

## Communication

- Always explain your reasoning behind decisions and approaches.
- When claiming something works or is fixed, prove it with a passing test, a
  script that validates the behavior, and a clear explanation of why it works.
  Don't just assert — convince with evidence.
- **No quality adjective without a number.** "Improved contrast", "faster",
  "fewer errors", "smaller" are not claims — they're moods. Report what you
  measured, the threshold it is judged against, and the value before and after:
  `3.73:1 → 7.13:1 (AA requires 4.5:1)`, `foot 238px in both states`,
  `18 fillers → 3, 3 seeds per arm`, `269 tests pass`, `8,843 lines → 4,989`.
  A table beats a sentence when there is more than one pair.
- Say how you measured it, so the reader can repeat it: the exact command, the
  fixture, the viewport, the seed count. A number nobody can reproduce is an
  assertion wearing a number's clothes.
- If something could not be measured, say that instead of reaching for the
  adjective — and name what would measure it.
- When uncertain about something, say so rather than presenting it as fact.
- End each response with a confidence indicator: 🟢 High | 🟡 Medium | 🔴 Low

## Code style

- Write extremely easy to consume code. Optimize for the next reader;
  skimmable beats clever.
- Early returns over nested conditionals.
- Name things for what they are, not how they're implemented.
- If a function needs a comment to explain *what* it does, the function is
  wrong. Comments explain *why*.
- Match the surrounding code's conventions before importing your own.

## Security

- Never commit secrets, API keys, credentials, or sensitive data.
- Always validate and sanitize user and external input.
- Never silently disable, skip, or delete tests to make a build pass. If a
  test is wrong, say so and propose the fix.

## Subagents

Parallelize independent work via subagents (repo exploration, test triage,
dependency research). Each subagent: one objective, one concrete deliverable.
No subagents for serial or trivial work.

## Project-specific section

Add a section below, per project, capturing what an agent can't infer quickly:
the concrete lint/format/test/build commands, the layout and layering, the
auth and configuration model, and the test layout and naming conventions.

## Project-specific section — this repository

This repo is a **plugin marketplace for both Claude Code and Codex**, and is
**directly compatible with opencode** via its `.opencode/` directory of
symlinked agent/skill definitions. There is no runtime, database, or build —
"behavior" is the prose contracts each tool loads and executes.

- **Layout** — `agents/<name>.md` are 8 standalone subagents (frontmatter +
  role; `mode: subagent` in frontmatter so opencode registers them as
  subagents). `skills/<name>/SKILL.md` are 9 orchestrators that fan out to
  sub-prompt files in `domains/` (review-pr, review-design,
  review-ux-psychology, simplify-sweep), `lenses/` (describe-codebase,
  plan-feature), or
  `references/` (batch-merge-prs, triage-issues, install-agents). Each skill
  also carries an eval suite in `evals/cases.json`. Deterministic
  sub-procedures live as `scripts/` inside their skill, invoked by the phases
  instead of narrated as prose: batch-merge-prs has `list-prs.sh` and
  `merge-prs.sh` (which auto-names the target branch `batch/<YYYYMMDD-HHMM>`
  when passed `auto`), review-pr has `diff-target.sh` (main-branch detection +
  diff computation), triage-issues has `list-issues.sh` (repo slug, labels,
  issue work list), and install-agents has `install-agents.sh` (copies
  `agents/*.md` into a host project's `.claude/agents/` and seeds journals).
  Repo-level scripts (installers, CI helpers) live in top-level `scripts/`.
  The `.opencode/` directory mirrors `agents/` and `skills/` via symlinks so
  opencode auto-discovers both without duplicating files.
  `scripts/install-opencode.sh` installs the agents and skills into an
  opencode discovery path (global `~/.config/opencode/` by default, or a
  target project's `.opencode/` with `--project`) via symlinks or copies.
- **Skill shape** — the review and survey skills follow Phase 0 *orient* →
  Phase 1 *fan out in parallel* → *consolidate/rank* → later phases *apply or persist*. review-pr and
  review-ux-psychology insert a *verify* pass (fresh skeptical agents re-check
  each finding) between fan-out and consolidate, so their consolidate step is
  Phase 3. plan-feature investigates integration and verification in parallel
  when useful (locally for small changes or hosts without delegation), then
  produces an implementation plan and saves it when requested. install-agents
  is a linear installer with no fan-out (orient → one confirmation → install
  via script → schedule → ledger).
- **Config / manifests** — identity in `.claude-plugin/plugin.json`
  (deliberately versionless — versioned by commit SHA); the Codex plugin
  manifest in `.codex-plugin/plugin.json` carries the only SemVer `version`
  field, bumped by release automation. Each tool then needs its own marketplace
  registry, each with a single entry pointing back at this repo:
  `.claude-plugin/marketplace.json` (source `github`, `cleanunicorn/agents-library`)
  and `.agents/plugins/marketplace.json` (source `local` at `"./"`). The two
  cannot be merged: Codex has no `github` source type, and rather than erroring
  it skips the entry silently, so the marketplace loads empty and the failure
  only surfaces later as `plugin ... was not found in marketplace`. Both
  registries resolve to the repo root, so installing on either tool copies the
  **whole repository** into that tool's plugin cache — anything added here
  ships to every user. Enabled plugins in `.claude/settings.json`.
  opencode is the exception: it has no marketplace manifest — `.opencode/`
  is auto-discovered, which is why it mirrors the content tree via symlinks
  rather than pointing at the root.
- **Releases / changelog** — a release is cut automatically when a PR merges
  to main (`.github/workflows/auto-release.yml`): the Conventional-Commit PR
  title decides the bump (`type!:` → major, `feat:` → minor,
  `fix:`/`perf:`/`refactor:` → patch, anything else or `[skip release]` →
  none), the version lands in `.codex-plugin/plugin.json`, main gets a
  `release: vX.Y.Z` commit plus a `v<version>` tag, and a GitHub release is
  created with generated notes. **Those release notes are the changelog** —
  there is no `CHANGELOG.md`; don't create one. PR
  titles are load-bearing and CI-checked (`.github/workflows/pr-title.yml`).
  Never add the skill evals to any workflow — they are manual-only
  (`docs/evals.md`).
- **No auth / error handling / logging / database / migrations** — agents
  inspect *target* projects for these; this repo holds none. The only durable
  per-project state is the per-agent journals in `agents/journals/`.
- **Schemas** — the `{mode, name, description}` frontmatter on every agent
  (`mode: subagent` for opencode compatibility; ignored by Claude Code/Codex),
  the `{name, description}` frontmatter on every skill, and
  the in-skill finding records sub-agents return (`{id, severity, domain,
  location, problem, measured, gap, fix, effort}` for review-pr, which its verify
  pass then annotates with `{verdict, confidence}`; `{id, severity, lens,
  principle, location, problem, measured, fix, effort}` for review-design;
  `{id, severity, lens, location, problem, measured, fix, effort}` for
  simplify-sweep; `{id, severity, lens, principle, location, problem, fix,
  hypothesis, effort}` for review-ux-psychology, which (like review-pr) runs a verify pass that annotates
  survivors with `{verdict, confidence}`; `{lens, topic, location, detail}` for
  describe-codebase; `{topic, evidence, proposal, acceptance_ids}` for
  plan-feature; `{issue, recommendation, kind, validity, evidence, labels,
  …}` verdicts for triage-issues; the
  `INSTALLED|IDENTICAL|CONFLICT|UPDATED|JOURNAL <name>` status lines
  install-agents.sh emits for install-agents' ledger).
- **Adding a component** — agents/skills are auto-discovered by directory; create
  the file(s) and add a README entry. No manifest edit needed.
- **Commands** — `bash scripts/check.sh` runs the fast local gate: shell/JSON
  syntax, Claude/Codex packaging contracts (`scripts/test-plugin-layout.py`),
  shared frontmatter fields, opencode link validation and regression tests,
  installer smoke tests, and eval case validation (`--dry-run`). Requires
  Python 3.9+ and Bash; no host CLI, model calls, credentials, or installs.
  These are repository contracts, not full host schema or arbitrary YAML
  validation. Lint/format/build: no separate tools. Behavioral skill
  evals: `python3 run_evals.py` — **manual-only and expensive** (real agent
  runs); never wire them into CI, hooks, or push automation. See `docs/evals.md`.
  Prose quality is still enforced by the bars in this guide and each SKILL.md.

**Start here:** README.md → AGENTS.md → agents/architect.md →
skills/review-pr/SKILL.md → skills/review-pr/domains/correctness.md
