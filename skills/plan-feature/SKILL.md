---
name: plan-feature
description: >-
  Turn a feature request into a repository-grounded implementation plan:
  acceptance criteria, integration points, ordered changes, test strategy.
  Use when asked to plan, design, or scope a feature before coding. Not a
  substitute for a direct implementation request; describe-codebase explains
  existing code, review-pr reviews a diff.
---

# plan-feature

You are the **orchestrator** of a repository-grounded planning pass. Turn the
user's intended behavior into a plan another developer can implement without
rediscovering the repository. Keep the plan proportional to the change: a small
feature needs a short checklist, not a new architecture document.

Planning is read-only by default; the only thing ever written is a plan
document the user asked for. Implementing the plan is a separate task. If the
user already asked for both a plan and implementation, finish the plan and
continue with that authorization rather than asking again. Do not turn a direct
"add X" request into a plan-only result.

## Phase 0 — Orient and define the outcome

1. **Read the project's guidance and relevant source**, including existing local
   changes. Work from the current checkout; a remote or GitHub CLI is not
   required. Do not reset changes or switch branches just to plan.
2. **Identify the requested user-visible outcome**, constraints, and explicit
   non-goals. Follow a named subsystem or path where supplied. If no feature is
   specified, ask for the intended capability instead of inventing one.
3. **Find an existing analogous feature** and trace its entry point, logic,
   data, and registration. Read the actual test and build configuration, and
   distinguish commands that execute assertions from syntax checks or
   placeholder scripts — by inspecting them, not by running them. Do not run
   installs, test suites, paid evals, or stateful services merely to write a
   plan; a planning pass leaves the working tree exactly as it found it.
4. **Draft observable acceptance criteria** (AC1, AC2, …): the input/action,
   expected result, and relevant failure behavior. Preserve the user's product
   choices. Ask only about missing decisions that would materially change the
   plan; continue independent investigation while waiting, label reasonable
   defaults as assumptions, and keep decision-dependent steps conditional until
   answered. **When nobody can answer** — a non-interactive run, a one-shot
   prompt, or a user who asked for the plan without discussion — do not end the
   turn on a question: proceed under labelled assumptions and list the decision
   under *Open decisions* in the plan.

An empty repository is valid: say there is no implementation to inspect, label
new paths and commands as proposals, and start with the smallest runnable
scaffold and feedback loop. Do not invent existing architecture or test coverage.

## Phase 1 — Investigate implementation and verification

For a change spanning independent areas, dispatch two read-only explorers **in
parallel** — issue both Agent/Task calls in a single message — using the host's
available subagent mechanism.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only exploration, or inherit the
session model. Retry at the session tier only when required fields or assigned
coverage are missing.

Each explorer's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the user's request, scope, constraints,
   and non-goals; the draft acceptance criteria; the project-guidance summary;
   and the analogous feature, test configuration, and starting paths you
   already found — so the explorers extend your trace instead of repeating it.
2. **The lens prompt** — read the matching file from `lenses/` (resolved
   relative to this skill's directory, not the target repository) and include
   it **verbatim**. That file is the explorer's entire instruction set; never
   hand it a path to go and read, because the explorer's working directory is
   the target repository.
3. **The output contract** — the finding schema below, with the instruction:
   *read-only; do not modify any file; return findings in this exact schema,
   citing existing `path:line` evidence or an explicit unknown.*

| Explorer | File | Deliverable |
| --- | --- | --- |
| Integration | `lenses/integration.md` | Reuse points, necessary changes, wiring, and compatibility constraints. |
| Verification | `lenses/verification.md` | Acceptance-to-test mapping, failure cases, and feedback loop gaps. |

For a small change, or when delegation is unavailable, perform both passes
yourself with the same lenses. If an explorer fails, cover that area locally or
name the unresolved gap; a missing report is not evidence that no work is
needed. No named model, vendor-specific tool, or sibling skill is required.

## Phase 2 — Reconcile and produce the plan

Check the cited source and reconcile conflicting recommendations yourself.
Reuse the project's patterns and dependencies where they satisfy the outcome.
Explain any necessary departure. Only compare alternatives when a real tradeoff
changes the decision; do not add frameworks or abstractions for hypothetical
future requirements.

Present these elements, combining them where the feature is small:

- **Outcome and scope:** requested behavior, non-goals, constraints, and
  assumptions. Separate unanswered product decisions from technical unknowns.
- **Current behavior and proposed approach:** cite existing paths and symbols;
  clearly label proposed new files. Explain where the change belongs and why.
- **Acceptance and verification:** for each AC, name the observable result,
  test location or proposed test, relevant failure/boundary case, and exact
  discovered command. If no useful test exists, make creating the smallest
  assertion-based loop the first implementation step. Mark proposed commands
  as proposed; never describe unrun tests as passing.
- **Ordered implementation checklist:** concrete paths/symbols and dependencies,
  covering the full behavior, registration, configuration, tests, and user docs
  where needed. Each step names its completion evidence. Keep one cohesive
  feature in one PR; checklist steps are milestones, not separate dependent
  PRs. Propose a split only when a piece genuinely ships on its own, and say
  why in one line.
  When the plan fixes a defect or a pattern, a step covers **every instance of
  it in the repository**, not only the reported one — with the search that
  found them as its evidence.
- **Compatibility and delivery:** address only boundaries this change touches.
  For stored data or public contracts, include old/new compatibility, migration
  order, and recovery limitations. For irreversible changes, explain what a
  code rollback cannot restore. For a local additive feature, a short revert
  note may suffice; omit deployment machinery the project does not have.
- **Open decisions:** what remains unknown, how to resolve it, and which steps
  it blocks. Label the plan provisional when an unresolved choice affects it.

Before presenting, check that every AC has an implementation step and a way to
verify it, all steps serve the requested outcome, and the smallest complete
change includes its wiring. A repository citation supports current behavior;
it does not prove the proposed behavior works.

## Phase 3 — Deliver or persist

Return the plan in chat unless the user requested a file. For an authorized
save, use the requested path or the repository's plan convention; if neither
exists, choose `docs/plans/<feature-slug>.md` and report it. Read an existing
target first and update only the relevant plan, preserving unrelated content.

Do not create issues, commits, PRs, or production changes as a side effect of
planning. Honor any separately requested implementation or publication after
delivering the plan, using the project's normal workflow and existing
authorization. Finish by stating any validation limits and the next actionable
step, rather than asking for approval already given.

## Finding schema

Each explorer returns findings as records with these fields:

```
topic:           short label (e.g. "list dispatch", "limit validation test")
evidence:        existing path:line, or an explicit "unknown: <what was searched>"
proposal:        the change or test this finding calls for; new paths marked proposed
acceptance_ids:  the AC labels this finding serves (e.g. [AC1, AC3])
```

You compose these into the plan; you do not surface the raw records.
