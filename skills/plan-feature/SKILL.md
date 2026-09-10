---
name: plan-feature
description: >-
  Turn a requested feature into a repository-grounded implementation plan with
  observable acceptance criteria, integration points, ordered changes, and a
  test strategy. Use when the user asks to plan or design a feature before
  coding, scope an implementation, or work out how to add a capability.
  Produces a plan in chat; saves it when requested. Do not substitute planning
  for a direct implementation request. For explaining existing code use
  describe-codebase; for reviewing an implemented diff use review-pr.
---

# plan-feature

Turn the user's intended behavior into a plan another developer can implement
without rediscovering the repository. Keep the plan proportional to the change:
a small feature needs a short checklist, not a new architecture document.

Planning is read-only by default. Saving a requested plan is part of this skill;
implementing it is a subsequent task. If the user already asked for both a plan
and implementation, finish the plan and continue with that authorization rather
than asking again. Do not turn a direct “add X” request into a plan-only result.

## Phase 0 — Orient and define the outcome

1. Read the project's guidance and relevant source, including existing local
   changes. Work from the current checkout; a remote or GitHub CLI is not
   required. Do not reset changes or switch branches just to plan.
2. Identify the requested user-visible outcome, constraints, and explicit
   non-goals. Follow a named subsystem or path where supplied. If no feature
   is specified, ask for the intended capability instead of inventing one.
3. Find an existing analogous feature and trace its entry point, logic, data,
   and registration. Read the actual test and build configuration. Distinguish
   commands that execute assertions from syntax checks or placeholder scripts.
4. Draft observable acceptance criteria (AC1, AC2, …): the input/action, expected
   result, and relevant failure behavior. Preserve the user's product choices.
   Ask only about missing decisions that would materially change the plan;
   continue independent investigation while waiting. Label reasonable defaults
   as assumptions, and keep decision-dependent steps conditional until answered.

An empty repository is valid: say there is no implementation to inspect, label
new paths and commands as proposals, and start with the smallest runnable
scaffold and feedback loop. Do not invent existing architecture or test coverage.

## Phase 1 — Investigate implementation and verification

For a change spanning independent areas, dispatch two read-only explorers in
parallel, using the host's available subagent mechanism:

| Explorer | Instructions | Deliverable |
| --- | --- | --- |
| Integration | [lenses/integration.md](lenses/integration.md) | Reuse points, necessary changes, wiring, and compatibility constraints. |
| Verification | [lenses/verification.md](lenses/verification.md) | Acceptance-to-test mapping, failure cases, and feedback loop gaps. |

Give each explorer the user's request, scope, constraints, draft criteria, and
the relevant guidance and starting paths from Phase 0. Resolve resources
relative to this skill's directory, not the target repository. Explorers return
concise records: `topic`, `evidence` (existing `path:line`, or an explicit
unknown), `proposal`, and `acceptance_ids`. They never edit the target.

For a small change, or when delegation is unavailable, perform both passes
yourself. If an explorer fails, cover that area locally or name the unresolved
gap; a missing report is not evidence that no work is needed. No named model,
vendor-specific tool, or sibling skill is required.

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
  feature in one PR; checklist steps are not separate dependent PRs.
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
Do not overwrite an unrelated document just because its path collides.

Do not create issues, commits, PRs, or production changes as a side effect of
planning. Honor any separately requested implementation or publication after
delivering the plan, using the project's normal workflow and existing
authorization. Finish by stating any validation limits and the next actionable
step, rather than asking for approval already given.
