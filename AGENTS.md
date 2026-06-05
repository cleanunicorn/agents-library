# Agent guide

This is a generic working guide for coding agents operating in any repository.
It defines *how* to work — orientation, workflow, communication, and quality
bars — without assuming a particular language, framework, or stack. Pair it
with the single-purpose agents in [`agents/`](agents/), and supplement it with
a project-specific section once you know the codebase.

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
