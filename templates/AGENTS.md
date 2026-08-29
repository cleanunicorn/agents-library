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
- {{BROWSERS}} — {{delete if there are no browser tests: "Playwright browser
  binaries — `npx playwright install --with-deps`, once per machine or
  container"}}
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
- **Test (end-to-end):** `{{E2E_CMD}}` {{— delete if there are no browser tests;
  see [End-to-end tests](#end-to-end-tests-playwright)}}
- **Build:** `{{BUILD_CMD}}`

Always run the linter and the test suite before opening a PR.

## Golden rules

The non-negotiables. Keep this list short — only rules that, if broken, cause
real damage or break an invariant an agent can't see from the code.

1. **Never commit directly to `{{DEFAULT_BRANCH}}`.** Always branch, always PR.
   {{If it's protected and/or merging ships something, say so here — e.g. "it is
   the release branch; merging auto-publishes a release."}}
2. **Never force-push a shared branch.**
3. **Keep `{{DEFAULT_BRANCH}}` green.** Run the checks locally before opening a
   PR (see [Run the checks](#5-run-the-checks-locally)).
4. **Use the project's task runner.** `{{TASK_RUNNER}}` ({{e.g. `make`, npm
   scripts}}) is the single source of the dev flow — don't hand-roll the
   underlying commands. If the flow needs to change, change the runner so
   everyone (and CI) stays in sync.
5. **Never disable, skip, or delete a test to make a build pass.** If a test is
   wrong, say so and propose the fix.
6. {{IF TITLES DRIVE AUTOMATION — delete if they don't: "**The PR title is
   load-bearing.** It drives the released version bump, so it must be a valid
   Conventional Commits string (see [PR titles](#pr-titles))."}}
7. {{PROJECT INVARIANT — the thing that's easy to break and hard to notice.
   e.g. "Every user-facing claim must trace to a registered source" / "The
   public API in `api/` is a contract; don't change response shapes."}}
8. {{PROJECT INVARIANT — architectural constraint. e.g. "No new runtime
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

### 2. Create a branch — in a worktree

**Never edit a checkout of `{{DEFAULT_BRANCH}}` directly.** Create the worktree
before the first edit, do the whole change there, and open the PR from it:

```bash
git worktree add {{WORKTREE_DIR}}/<short-topic> -b <short-topic>
```

{{WORKTREE_DIR — where this project keeps them, e.g. `.claude/worktrees/`, and
confirm it is gitignored. If the harness has a worktree tool, name it here.}}

Branch names are short, lowercase, hyphenated, and prefixed by intent. Match the
Conventional Commits type you expect the PR to use (see [Commit](#4-commit)):

```
feat/<short-description>      # new feature
fix/<short-description>       # bug fix
refactor/<short-description>  # internal change, no behavior change
perf/<short-description>      # performance work
docs/<short-description>      # documentation only
chore/<short-description>     # tooling, deps, housekeeping
```

Examples: `{{fix/short-example}}`, `{{feat/short-example}}`.

### 3. Make focused changes

- One logical change per PR — and a whole feature *is* one logical change.
  Ship its code, tests, and docs together; don't split it across a chain of
  dependent PRs. Don't bundle an unrelated refactor into a fix either.
- Match the surrounding style: {{name the dominant patterns — e.g. "typed
  models between layers, early returns, framework X idioms"}}.
- Keep diffs focused: everything in the diff should serve that one change.
  Focused is about relevance, not size — don't ship half a feature to keep the
  diff short.

### 4. Commit

Commits follow [Conventional Commits](https://www.conventionalcommits.org):

```
type(optional-scope): short imperative description
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`. Add `!` before the colon for a breaking change.

```
fix: {{example imperative subject}}
feat({{scope}}): {{example scoped subject}}
{{type}}!: {{example breaking change}}
```

Write in the imperative mood ("add", not "added"). Keep the subject under ~72
characters and explain the *why* in the body when it isn't obvious.

### 5. Run the checks locally

Do not open a PR with these failing — they mirror what CI runs:

```bash
{{LINT_CMD}}
{{TEST_CMD}}
{{FORMAT_CMD}}    # run before lint if you touched code it formats
{{ANY_EXTRA_GATE}} # e.g. type-check, frontend build, e2e, integration/eval gate
```

{{If the end-to-end suite is too slow to be part of the local gate, say so here
and name what does run it — e.g. "e2e runs in CI only; run `{{E2E_CMD}}` locally
when you touched a user-facing flow."}}

### 6. Push and open a PR

```bash
git push -u origin {{feat/<short-description>}}
gh pr create --base {{DEFAULT_BRANCH}} --fill
```

Target **`{{DEFAULT_BRANCH}}`**.

## PR titles

The PR title follows the same Conventional Commits format as commits:

```
type(optional scope)!: description
```

{{If a CI check enforces this, say so — e.g. "a GitHub Action blocks the merge on
an invalid title." If the title also drives a release, see Release automation.}}

## PR description

Keep it short and useful:

- **What** changed and **why** (the motivation/problem).
- **Numbers, not adjectives.** Anything you claim improved carries the value you
  measured, the threshold it is judged against, and how to reproduce it —
  `3.73:1 → 7.13:1 (AA needs 4.5:1)`, `{{TEST_CMD}}: 269 pass`, `-412 lines`.
  A table when there is more than one pair. "Not measured" beats a vague
  adjective.
- **The gap**, for a bug fix: what was supposed to catch this, why it didn't,
  and what now would. Give it its own heading — it is the half of the fix a
  reviewer can't reconstruct from the diff.
- **How to test** / what you ran ({{LINT_CMD}}, {{TEST_CMD}}, any extra gate).
- **Linked issues**: `Closes #123` when it resolves one.
- Screenshots for UI changes.
- When the change is mostly a removal, lead with what is **gone** (net lines,
  the concepts dropped) and add an explicit **Kept:** line.

## After opening the PR

- Make sure **CI is green**. {{Note which jobs matter and why — e.g. "all three
  platforms; the binaries ship per-OS."}}
- {{If a PR-title check fails, edit the title — it re-validates on edit.}}
- Address review feedback by pushing more commits to the same branch.
- {{PROJECT RULE — e.g. "changes to `<sensitive area>` need maintainer sign-off;
  never self-merge them."}}

## Release automation

Delete this section if merging doesn't ship anything.

- **Is `{{DEFAULT_BRANCH}}` protected?** {{yes/no}}
- **What does merging trigger?** {{e.g. "bumps `{{VERSION_FILE}}`, tags, and
  dispatches the release build" / "deploys to staging" / "nothing"}}
- **Does the PR title/prefix decide the bump?** {{yes/no — if yes, fill the table}}

| PR title prefix | Release effect |
| --- | --- |
| `{{type}}!: …` (any `type!:`) | **major** |
| `feat: …` | **minor** |
| `fix: …`, `perf: …`, `refactor: …` | **patch** |
| `docs:`, `style:`, `test:`, `build:`, `ci:`, `chore:`, `revert:` | **none** |

> ⚠️ Choose the prefix deliberately — it decides whether (and how big) a release
> ships when the PR merges.

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

Unit and integration tests. Browser tests have their own section below.

- **Framework / runner:** {{e.g. pytest, vitest, go test}}
- **Location & naming:** {{where tests live and how they're named}}
- **What to cover:** {{happy path + error paths + edge cases; the bar for new code}}
- **Fixtures / stubs:** {{how to run without network or keys, if applicable}}

## End-to-end tests (Playwright)

Delete this section if the project has no browser tests.

E2E is where an automated run most often stalls or goes flaky — a missing
browser binary, a report server that never exits, a login replayed per test.
Record the exact invocations and the traps.

- **Specs live in:** `{{e2e/}}`, named `{{*.spec.ts}}`
- **Config:** `{{playwright.config.ts}}` — base URL `{{http://localhost:3000}}`
- **Does the run start the app itself?** {{yes — the `webServer` block boots
  `{{RUN_CMD}}` and waits for the base URL / no — start it yourself first}}
- **Browser binaries:** `npx playwright install --with-deps`. A "browser not
  found" / "executable doesn't exist" error means this hasn't been run.

Prefer the task runner's wrapper if there is one (`{{E2E_CMD}}`); the raw forms:

```bash
npx playwright test                        # everything, headless
npx playwright test {{e2e/login.spec.ts}}  # one spec
npx playwright test -g "{{test title}}"    # one test by title
npx playwright test --reporter=list        # plain streaming output
```

> ⚠️ `npx playwright show-report` and `npx playwright show-trace` both start a
> **blocking** web server — they never return. Never run either in an automated
> session. Read the artifacts on disk instead.

**`--headed`, `--debug`, and `--ui`** are for a human at a terminal. `--headed`
needs a display; `--debug` and `--ui` additionally wait for input, so they hang
an automated run.

**Writing tests here:**

- **Selectors:** {{the project's rule — e.g. "`getByRole`/`getByLabel` first;
  `data-testid` only when there's no accessible handle; never CSS or XPath tied
  to styling"}}
- **Waiting:** use web-first assertions — `await expect(locator).toBeVisible()`
  auto-retries until the timeout. Never `waitForTimeout`; a fixed sleep is how
  flake gets in, and it passes locally right up until CI is slower.
- **Auth:** {{how a test gets a signed-in session — e.g. "a setup project saves
  `storageState` once; don't drive the login form in every test"}}
- **Test data:** {{how each test gets isolated data, and what's shared}}
- **Isolation:** tests run in parallel against {{a shared database/environment}},
  so no test may depend on another's leftovers or on file order.

**When one fails:** {{where artifacts land — e.g. "the trace, screenshot, and
video for a failed run are under `test-results/<test>/`"}}. Read the screenshot
and the error text first; they identify most failures without opening a trace.

{{**Snapshots:** how visual/DOM snapshots are updated (`--update-snapshots`) and
the rule for it — e.g. "only when the change to the UI is intended, and the
regenerated files get reviewed in the diff like any other change."}}

A flaky e2e test is a real finding, not noise — fix it or report it. Never
`test.skip` or `--grep-invert` one to get a green run (see
[Golden rules](#golden-rules)).

## Security

- Never commit secrets, API keys, credentials, or sensitive data.
- Always validate and sanitize user and external input.
- {{PROJECT-SPECIFIC: authn/authz model, which endpoints are protected, how
  permissions are checked}}

## Hazards

Traps that have already cost someone real time or real damage here. This is the
highest-value section in the file and the one an agent cannot infer — a
convention can be read off the code, an incident cannot. Delete if none.

Write one subsection per hazard, not a bullet. A bullet says *don't*; a
subsection says *why, and what to do instead*, which is the part that makes the
rule survive contact with a plausible-looking shortcut. Each one:

1. **The rule, in bold, up front.** Imperative and unhedged.
2. **The mechanism** — what actually goes wrong, concretely enough that a
   reader can recognise a new variant of it rather than only the exact case.
3. **The evidence it is real** — what it broke and how often. *"This has taken
   the production instance down twice"* stops an agent that *"be careful with
   process management"* does not.
4. **The safe recipe**, as a copy-pasteable block. A hazard without an
   alternative just gets worked around.
5. **The near-misses**, when the obvious workaround is also unsafe — name it
   explicitly, or someone will reinvent it.

````markdown
### {{Never <do the tempting thing>}}

**{{The rule as one imperative sentence.}}**

{{The mechanism: what matches too broadly, runs in the wrong environment, is
cached, or fires out of order — and why it looks correct right up until it
isn't.}}

{{The evidence: what this broke, when, and how many times.}}

```sh
{{the safe recipe}}
```

{{The near-misses: "`X`, `Y` and `Z` are the same hazard." Say so, or they will
be tried next.}}
````

Short hazards that genuinely need no recipe can stay one-liners:

- {{e.g. "The `legacy/` module is frozen — do not modify it."}}
- {{e.g. "Migrations run automatically on boot in dev but not in prod."}}

When an incident produces a rule, add it here in the same PR that fixes the
incident — that is when the mechanism is still understood.

## Start here

The fastest path to understanding this codebase:

{{FILE_1}} → {{FILE_2}} → {{FILE_3}}
