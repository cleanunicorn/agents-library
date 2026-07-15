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

{{ONE_PARAGRAPH: what this project is, who uses it, and what "done" looks like
for a change. Example: "A REST API that powers the customer dashboard. Changes
ship when the linter and test suite pass and a reviewer approves the PR."}}

## Commands

The commands an agent should run for each task. Fill in the exact invocations —
not "run the tests" but the literal command.

- **Install / bootstrap:** `{{INSTALL_CMD}}`
- **Lint:** `{{LINT_CMD}}`
- **Format:** `{{FORMAT_CMD}}`
- **Type-check:** `{{TYPECHECK_CMD}}`
- **Test (all):** `{{TEST_CMD}}`
- **Test (single file / focused):** `{{TEST_ONE_CMD}}`
- **Build:** `{{BUILD_CMD}}`
- **Run locally:** `{{RUN_CMD}}`

Always run the linter and the test suite before committing.

## Layout & layering

How the codebase is organized and which layer may call which. Keep this to the
directories that matter.

- `{{DIR}}/` — {{WHAT LIVES HERE}}
- `{{DIR}}/` — {{WHAT LIVES HERE}}
- {{Describe the layering: e.g. "HTTP handlers call services; services call
  repositories; nothing skips a layer or reaches into another's internals."}}

## Conventions

The rules that aren't obvious from a single file. Match the surrounding code
before importing outside conventions.

- **Naming:** {{e.g. files kebab-case, types PascalCase, tests `*_test.go`}}
- **Configuration:** {{where config lives; how secrets are read — e.g. "all
  config flows through `config/`; never read process.env from business code"}}
- **Data / schema ownership:** {{who owns structure — e.g. "migrations own the
  schema; runtime code never creates tables"}}
- **Error handling:** {{the project's pattern — e.g. "return typed errors; never
  swallow; user-facing messages come from `errors/`"}}
- **Registering new components:** {{how new routes/modules/jobs get wired in}}

## Testing

- **Framework / runner:** {{e.g. pytest, vitest, go test}}
- **Location & naming:** {{where tests live and how they're named}}
- **What to cover:** {{happy path + error paths + edge cases; the bar for new code}}
- Never disable, skip, or delete a test to make a build pass. If a test is
  wrong, say so and propose the fix.

## Workflow

- **Bug fixes:** reproduce with a failing test FIRST, then fix, then prove the
  fix with the test passing. If a bug genuinely can't be expressed as a test,
  say so and explain why.
- **Features:** build the smallest feedback loop (a failing test, a script, a
  CLI invocation) before writing logic.
- **Branching / PRs:** {{branch naming, PR target branch, review expectations}}
- Never commit directly to `{{DEFAULT_BRANCH}}`; open a reviewable PR.

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
