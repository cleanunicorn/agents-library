<!--
AGENTS.md template — copy this file to the root of your project as AGENTS.md,
then fill in every {{PLACEHOLDER}} and delete the guidance comments (like this
one) and any sections that don't apply.

The goal of AGENTS.md is to capture what a coding agent CANNOT infer quickly on
its own: the concrete commands, the layering, the conventions that aren't
written down, and the project-specific gotchas. Keep it short and factual —
this is a map, not a tutorial. If something is obvious from a glance at the
code, leave it out.
-->

# {{PROJECT_NAME}} — Agent guide

Guidance for AI agents (and humans) contributing to **{{PROJECT_NAME}}**.

{{ONE_PARAGRAPH: what this project is, who uses it, and what "done" looks like
for a change. State the working model up front — e.g. "This project follows
GitHub flow: `{{DEFAULT_BRANCH}}` is always releasable, all work happens on
short-lived branches, and every change lands through a reviewed pull request."}}

Read [README.md](README.md) for setup{{, and [ARCHITECTURE.md](ARCHITECTURE.md)
for the full design}}. This file is the operational checklist for *how to work*
here.

## Prerequisites

What you need installed and available before the commands below will work. List
exact minimum versions where they matter.

- {{RUNTIME}} — {{e.g. "Python ≥ 3.12" / "Node.js ≥ 20 + npm" / "Go ≥ 1.22"}}
- {{SERVICES}} — {{e.g. "Docker + Docker Compose (Postgres runs in a container)"}}
- {{TOOLING}} — {{e.g. "the `gh` CLI for PRs; `uv` if present, else venv"}}
- {{CREDENTIALS/KEYS}} — {{where they go and what a live run needs. Note if keys
  are app settings / a secrets manager rather than `.env`, and never commit them.}}

## Commands

The commands an agent should run for each task. Fill in the exact invocations —
not "run the tests" but the literal command. If the project wraps these behind a
task runner (Makefile, npm scripts, `just`), prefer the wrapped form and treat
it as the single source of truth (see Golden rules).

- **Install / bootstrap:** `{{INSTALL_CMD}}`
- **Run locally:** `{{RUN_CMD}}`
- **Stop / teardown:** `{{STOP_CMD}}`
- **Lint:** `{{LINT_CMD}}`
- **Format:** `{{FORMAT_CMD}}`
- **Type-check:** `{{TYPECHECK_CMD}}`
- **Test (all):** `{{TEST_CMD}}`
- **Test (single file / focused):** `{{TEST_ONE_CMD}}`
- **Build:** `{{BUILD_CMD}}`

Always run the linter and the test suite before opening a PR.

## Golden rules

The non-negotiables. Keep this list short — only rules that, if broken, cause
real damage or break an invariant an agent can't see from the code.

1. **Never commit directly to `{{DEFAULT_BRANCH}}`.** Always branch, always PR.
2. **Never force-push a shared branch.**
3. **Keep `{{DEFAULT_BRANCH}}` green.** Run the checks locally before opening a
   PR (see [Run the checks](#5-run-the-checks-locally)).
4. **Use the project's task runner.** `{{TASK_RUNNER}}` ({{e.g. `make`, npm
   scripts}}) is the single source of the dev flow — don't hand-roll the
   underlying commands. If the flow needs to change, change the runner so
   everyone (and CI) stays in sync.
5. **Never disable, skip, or delete a test to make a build pass.** If a test is
   wrong, say so and propose the fix.
6. {{PROJECT INVARIANT — the thing that's easy to break and hard to notice.
   e.g. "Every user-facing claim must trace to a registered source" / "The
   public API in `api/` is a contract; don't change response shapes."}}
7. {{PROJECT INVARIANT — architectural constraint. e.g. "No new runtime
   dependencies without a good reason" / "Business logic never reads env
   directly; config flows through `config/`."}}

## Communication

- Always explain the reasoning behind decisions and approaches.
- When claiming something works or is fixed, prove it — a passing test, a
  script that validates the behavior, or a clear explanation of why. Don't just
  assert.
- When uncertain, say so rather than presenting a guess as fact.
- End each response with a confidence indicator: 🟢 High | 🟡 Medium | 🔴 Low

## The GitHub flow, step by step

### 1. Start from an up-to-date `{{DEFAULT_BRANCH}}`

```bash
git checkout {{DEFAULT_BRANCH}}
git pull origin {{DEFAULT_BRANCH}}
```

### 2. Create a branch

Branch names are short, lowercase, hyphenated, and prefixed by intent:

```
feat/<short-description>      # new feature
fix/<short-description>       # bug fix
refactor/<short-description>  # internal change, no behavior change
docs/<short-description>      # documentation only
chore/<short-description>     # tooling, deps, housekeeping
```

### 3. Make focused changes

- One logical change per PR. Don't bundle an unrelated refactor into a fix.
- Match the surrounding style: {{name the dominant patterns — e.g. "typed
  models between layers, early returns, framework X idioms"}}.
- Keep diffs small and reviewable.

### 4. Commit

Commit subjects are imperative, under ~72 characters, and lead with the area or
theme when it helps. Explain the *why* in the body when it isn't obvious.

```
fix: {{example imperative subject}}
{{Area}}: {{example subject leading with the area}}
```

### 5. Run the checks locally

Do not open a PR with these failing — they mirror what CI runs:

```bash
{{LINT_CMD}}
{{TEST_CMD}}
{{FORMAT_CMD}}    # run before lint if you touched code it formats
{{ANY_EXTRA_GATE}} # e.g. type-check, frontend build, integration/eval gate
```

### 6. Push and open a PR

```bash
git push -u origin {{feat/<short-description>}}
gh pr create --base {{DEFAULT_BRANCH}} --fill
```

Target **`{{DEFAULT_BRANCH}}`**.

## PR description

Keep it short and useful:

- **What** changed and **why** (the motivation/problem).
- **How to test** / what you ran ({{LINT_CMD}}, {{TEST_CMD}}, any extra gate).
- **Linked issues**: `Closes #123` when it resolves one.
- Screenshots for UI changes.

## After opening the PR

- Make sure **CI is green**.
- Address review feedback by pushing more commits to the same branch.
- {{PROJECT RULE — e.g. "changes to `<sensitive area>` need maintainer sign-off;
  never self-merge them."}}

## Project map (where things live)

How the codebase is organized and which layer may call which. Keep this to the
directories that matter.

```
{{DIR}}/            {{what lives here}}
  {{SUBDIR}}/         {{what lives here}}
{{DIR}}/            {{what lives here}}
{{tests}}/          {{test suite}}
```

{{Describe the layering: e.g. "HTTP handlers call services; services call
repositories; nothing skips a layer or reaches into another's internals."}}

{{See [ARCHITECTURE.md](ARCHITECTURE.md) for the full architecture.}}

## Conventions

The rules that aren't obvious from a single file. Match the surrounding code
before importing outside conventions.

- **Naming:** {{e.g. files kebab-case, types PascalCase, tests `*_test.go`}}
- **Configuration:** {{where config lives; how secrets are read}}
- **Data / schema ownership:** {{who owns structure — e.g. "migrations own the
  schema; runtime code never creates tables"}}
- **Error handling:** {{the project's pattern}}
- **Registering new components:** {{how new routes/modules/jobs get wired in}}

## Testing

- **Framework / runner:** {{e.g. pytest, vitest, go test}}
- **Location & naming:** {{where tests live and how they're named}}
- **What to cover:** {{happy path + error paths + edge cases; the bar for new code}}
- **Fixtures / stubs:** {{how to run without network or keys, if applicable}}

## Security

- Never commit secrets, API keys, credentials, or sensitive data.
- Always validate and sanitize user and external input.
- {{PROJECT-SPECIFIC: authn/authz model, which endpoints are protected, how
  permissions are checked}}

## Gotchas

Non-obvious traps that have bitten people before. Delete if none.

- {{e.g. "The `legacy/` module is frozen — do not modify it."}}
- {{e.g. "Migrations run automatically on boot in dev but not in prod."}}

## Start here

The fastest path to understanding this codebase:

{{FILE_1}} → {{FILE_2}} → {{FILE_3}}
