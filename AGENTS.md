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
3. If the bug genuinely cannot be expressed as a test, say so explicitly and
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

### When stuck

- State the hypothesis: "I think X because Y. Test: Z."
- If a hypothesis fails twice, stop and re-examine assumptions instead of
  trying variants.

## Communication

- Always explain your reasoning behind decisions and approaches.
- When claiming something works or is fixed, prove it with a passing test, a
  script that validates the behavior, and a clear explanation of why it works.
  Don't just assert — convince with evidence.
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
  subagents). `skills/<name>/SKILL.md` are 8 orchestrators that fan out to
  sub-prompt files in `domains/` (review-pr, review-design,
  review-ux-psychology, simplify-sweep), `lenses/` (describe-codebase), or
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
- **Skill shape** — every skill is Phase 0 *orient* → Phase 1 *fan out in
  parallel* → *consolidate/rank* → later phases *apply or persist*. review-pr and
  review-ux-psychology insert a *verify* pass (fresh skeptical agents re-check
  each finding) between fan-out and consolidate, so their consolidate step is
  Phase 3. install-agents is the one exception: a linear installer with no
  fan-out (orient → one confirmation → install via script → schedule → ledger).
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
  `CHANGELOG.md` is a frozen pre-automation archive; don't append to it. PR
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
  location, problem, fix, effort}` for review-pr, which its verify pass then
  annotates with `{verdict, confidence}`; `{id, severity, lens, principle,
  location, problem, fix, effort}` for review-design; `{id, severity, lens,
  principle, location, problem, fix, hypothesis, effort}` for
  review-ux-psychology, which (like review-pr) runs a verify pass that annotates
  survivors with `{verdict, confidence}`; `{lens, topic, location, detail}` for
  describe-codebase; `{issue, recommendation, kind, validity, evidence, labels,
  …}` verdicts for triage-issues; the
  `INSTALLED|IDENTICAL|CONFLICT|UPDATED|JOURNAL <name>` status lines
  install-agents.sh emits for install-agents' ledger).
- **Adding a component** — agents/skills are auto-discovered by directory; create
  the file(s) and add a README entry. No manifest edit needed.
- **Commands** — lint/format/build: none. Tests: `python3 run_evals.py`
  (validate with `--dry-run` first) runs the skill evals — **manual-only and
  expensive** (real agent runs); never wire it into CI, hooks, or push
  automation. See `docs/evals.md`. Prose quality is still enforced by the bars
  in this guide and each SKILL.md.

**Start here:** README.md → AGENTS.md → agents/architect.md →
skills/review-pr/SKILL.md → skills/review-pr/domains/correctness.md
