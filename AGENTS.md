# Agent guide

This is a generic working guide for coding agents operating in any repository.
It defines *how* to work — orientation, workflow, communication, and quality
bars — without assuming a particular language, framework, or stack. Pair it
with the single-purpose agents in [`agents/`](agents/), and supplement it with
a project-specific section once you know the codebase.

Several different models read this guide, in interactive sessions and in
unattended runs. It says what to do, what done looks like, and the reason
behind each boundary; how to get there is left to judgement.

## Start edits in a worktree

Before the first edit, create a git worktree updated from `origin/main` and
do all work there — never on `main` directly, and never in a worktree that's
stale relative to `origin/main`. Read-only work (explaining, diagnosing,
reviewing) can use the current checkout and must not fetch, switch, reset, or
rebase unless asked.

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

## Where to look

Read what the change needs, not the whole project: a typo fix needs nothing
below; a change that crosses a layer needs the layering; a new component needs
the registration pattern.

- Project docs (README, CONTRIBUTING, architecture notes, agent guides) for
  the intended **layering** — how entry points, business logic, data access,
  configuration, presentation, and background work are separated, and which
  layer may call which.
- The **shared infrastructure** when the change touches it: the central config
  object, shared helpers, the data layer, and where cross-cutting concerns
  (auth, error reporting, logging) live.
- A couple of well-built modules for the **conventions that aren't written
  down**; copy their structure.
- The lint, format, test, and build **commands** — in the project-specific
  section below when one exists.

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

## Workflow

### Bug fixes

1. Reproduce the bug with a failing test FIRST. Do not attempt a fix before this.
2. Then fix — every instance, not just the one reported (see
   [Fix it everywhere](#fix-it-everywhere)). Prove the fix with the test passing.
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

### Fix it everywhere

The problem in front of you is rarely the only copy. When you find one — a
bug, a hygiene gap, a stale doc, a pattern violation — before fixing it:

1. Search the whole repository for the same problem. Search for the *shape*,
   not the literal text: the pattern, the call, the rule a linter would apply.
2. Fix every instance in the same PR, the same way. An instance that needs a
   judgement call is listed in the PR as a follow-up, not forced. Keep going
   while the instances stay mechanically identical, independently verifiable,
   and reviewable as one change, and put the count up front so the reviewer
   sees the scale. Stop and list the rest when the blast radius or the
   verification cost changes: generated code, vendored dependencies, an
   instance whose fix would differ, or anything the project says to ask
   about.
3. Put the search and its count in the PR — the exact query, and
   `7 found · 6 fixed · 1 left (needs a design call)`.

A fix applied to one instance while identical ones remain is incomplete: the
next contributor copies whichever one they find first. This is the instance
twin of *Close the gap* above — that step widens the check, this one widens
the fix. It does not license bundling: a *different* problem next door still
gets its own PR.

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

## Finish the job

Define done before starting, and work to it. For an implementation request,
done means the change is implemented, wired, tested, and documented, the checks
are green, and it is delivered at the terminal state the workflow calls for — a
PR where the project or the request asks for one, otherwise a committed branch
— not that the first implementation compiles. A
read-only request (explain, diagnose, review) is done when the report is
delivered, and a terminal state the user named ("stop after the plan") wins
over both. If the request includes getting the result running, inspecting it,
and fixing what fails, that is part of the task: do it rather than returning
for review. When the scope is ambiguous, state the scope you are completing and
any part you left, with the reason, instead of stopping to ask. Stop early only
at a decision that genuinely needs confirmation (below), or when nothing
qualifies — a report saying so beats an empty PR.

## Decision boundaries

Say what is safe, not only what is forbidden, and give the reason behind each
boundary: a bare "ask first" either stops work that should continue or gets
ignored.

- **Safe by default:** the project's linter, formatter, type-checker, and test
  suite are the feedback loop. Run them as often as needed, fix what your
  change broke, and rerun without checking in. A project-specific section
  names any suite that touches a shared or live resource; that one needs
  authorization, and without it you run what is safe and report what was
  skipped.
- **Needs confirmation unless already authorized:** external contracts
  (public API paths and shapes, serialized field names, stored data), anything
  the project lists as ask-first, and destructive or hard-to-reverse actions.
  A request that already covers it ("rename the endpoint too") is the
  confirmation. Without it, in an unattended run there is nobody to ask:
  leave that instance unchanged and list it in the PR with the reason.
- **Never:** the Security section below, and whatever the project marks as
  such.

## Communication

- Explain your reasoning behind decisions and approaches.
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
- A qualitative claim — cleaner structure, accurate docs, a clearer name — is
  not exempt from evidence, but its evidence is not a number: cite the code
  path, the project rule, the test, or the before/after that lets a reader
  check it.
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
the concrete lint/format/test/build commands and whether they are safe to run
unattended, the layout and layering, the auth and configuration model, the test
layout and naming conventions, and the decisions that need a person, with the
reason.

## Project-specific section — this repository

This repo is a **plugin marketplace for both Claude Code and Codex**, and is
**directly compatible with opencode** via its `.opencode/` directory of
symlinked agent/skill definitions. There is no runtime, database, or build —
"behavior" is the prose contracts each tool loads and executes.

- **Layout** — `agents/<name>.md` are 8 standalone subagents (frontmatter +
  role; `mode: subagent` in frontmatter so opencode registers them as
  subagents). `skills/<name>/SKILL.md` are 10 orchestrators that fan out to
  sub-prompt files in `domains/` (review-pr, review-design,
  review-ux-psychology, simplify-sweep), `lenses/` (describe-codebase,
  plan-feature), or
  `references/` (batch-merge-prs, triage-issues, install-agents, manager). Each skill
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
  produces an implementation plan and saves it when requested. triage-issues
  and batch-merge-prs follow the same orient → fan out → consolidate shape and
  then add *decide* → *act* → *summarize* phases, acting only on what was
  approved. install-agents is a linear installer with no fan-out (orient → one
  confirmation → install via script → schedule → ledger). manager is the
  delivery pipeline that composes the others, in two roles. The invoking
  agent is the super manager: it starts one manager per work item, each in
  its own workspace, is the user's only contact, and reports a questions
  section plus one header and one fixed status block per manager. Each
  manager runs: orient, ask early, and pick a roster sized to the work item
  from the agent-type catalogue (`references/agent-types.md` — no count is
  prescribed) → parallel planners (plan-feature) → a coordinator's SWOT merge
  → implement → parallel reviewers (review-pr) → validate and fix → simplify
  (simplify-sweep) → final review of what was committed since the last review
  → hand back in the fixed per-team status block. A manager's questions are
  records the super manager relays and answers by id. Planners and reviewers
  only read; one agent writes at a time; the team runs in a sub-space of its
  manager's workspace, never the super manager's, and each level closes only
  what it created.
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
  …}` verdicts for triage-issues; `{planner, plan, decisions}` plan records,
  `{id, quadrant, claim, evidence, affects, action}` SWOT records, `{topic,
  plan_<label> per plan, chosen, rule, reason, swot_refs}` decision records,
  `{roster, signals, reason, cost, changes}` roster records, and
  `{source_ids, raised_by, severity, verdict, evidence, scope, audited,
  action, sweep, status}` validation records, `{id, phase, question, why,
  options, default, blocks, status, answer}` question records, and
  `{work_item, slug, manager, workspace, run_dir, state, questions,
  last_summary, closed}` super-manager ledger rows for manager, defined in
  its `references/` files; the
  `INSTALLED|IDENTICAL|CONFLICT|UPDATED|JOURNAL <name>` status lines
  install-agents.sh emits for install-agents' ledger).
- **Adding a component** — agents/skills are auto-discovered by directory; create
  the file(s) and add a README entry. No manifest edit needed.
- **Commands** — `bash scripts/check.sh` runs the fast local gate: shell/JSON
  syntax, Claude/Codex packaging contracts (`scripts/test-plugin-layout.py`),
  shared frontmatter fields, the fix-everywhere contract
  (`scripts/test-fix-everywhere.py`), opencode link validation and regression tests,
  installer smoke tests, and eval case validation (`--dry-run`). Requires
  Python 3.9+ and Bash; no host CLI, model calls, credentials, or installs —
  safe to run as often as needed.
  These are repository contracts, not full host schema or arbitrary YAML
  validation. Lint/format/build: no separate tools. Behavioral skill
  evals: `python3 run_evals.py` — **manual-only and expensive** (real agent
  runs); never wire them into CI, hooks, or push automation. See `docs/evals.md`.
  Prose quality is still enforced by the bars in this guide and each SKILL.md.

**Where to look:** README.md for install and update paths; this file for the
working guide; `agents/architect.md` for the agent shape;
`skills/review-pr/SKILL.md` for the orchestrator shape, and its `domains/` for
the shape of a sub-prompt.
