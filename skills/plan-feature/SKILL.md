---
name: plan-feature
description: >-
  Turn a feature request into a repository-grounded implementation plan:
  acceptance criteria, integration points, ordered changes, test strategy.
  Use when asked to plan, design, or scope a feature before coding. Not a
  substitute for a direct implementation request; describe-codebase explains
  existing code, review-pr reviews a diff, simplify-sweep tidies existing
  code.
---

# plan-feature

## Overview

Turn the intended behavior into a plan another developer can implement
without rediscovering the repository. Keep it proportional: a small feature
gets a short checklist, not an architecture document.

## When to use

- Asked to plan, design, or scope a feature before coding.
- Not when the user asked for a direct implementation ("add X"): do not
  reduce that to a plan-only result. If they asked for both, finish the plan
  and continue.
- Not for explaining code (describe-codebase), reviewing a diff (review-pr),
  or tidying code (simplify-sweep).

## What good looks like

- **Outcome first.** State the user-visible outcome, constraints, and
  non-goals, and write observable acceptance criteria (AC1, AC2, ...): the
  action, the expected result, and the relevant failure behavior. Preserve
  the user's product choices. If no feature is named, ask for one.
- **Grounded in the repo.** Read project guidance, relevant source, and
  existing local changes in the current checkout. Find an analogous feature
  and trace its entry, logic, data, and registration. Cite existing
  `path:line`; label proposed files, symbols, and commands as proposed. A
  citation proves current behavior, not that the proposal works.
- **Reuse over invention.** Follow the project's patterns and dependencies.
  Explain any departure, compare alternatives only when a real tradeoff
  changes the decision, and add nothing for hypothetical future needs.
- **Verifiable.** Map each AC to a test (existing or proposed), a failure or
  boundary case, and the exact command found in the config. Inspect whether
  a command truly runs assertions or is a syntax check or placeholder. If no
  useful loop exists, the first step is the smallest assertion-based one.
  Never call an unrun test passing.
- **Complete.** An ordered checklist of concrete paths and symbols covering
  behavior, wiring, config, tests, and docs, each step with its completion
  evidence. One cohesive feature is one PR; steps are milestones. Propose a
  split only when a piece ships independently, with the reason in one line.
  When the plan fixes a defect or pattern, apply it to every instance found
  by searching the repo for its shape (report N found / N fixed / N left).
- **Honest about compatibility.** Cover only boundaries the change touches:
  stored data, public contracts, migration order, what a rollback cannot
  restore. Omit deployment machinery the project lacks.
- **Open decisions.** List what is unknown, how to resolve it, and what it
  blocks. Ask only about decisions that materially change the plan; when
  nobody can answer, proceed under labelled assumptions and mark the plan
  provisional. An empty repository is valid: say nothing exists to inspect
  and propose the smallest runnable scaffold.

Investigate in parallel where the host supports delegation, otherwise
locally. Two angles are worth covering: integration (reuse points, necessary
changes, wiring, coexistence with old clients or records) and verification
(AC-to-test mapping, failure cases, feedback-loop gaps). Check what any
helper reports against the source yourself.

## Boundaries

- Read-only. Do not install, run test suites, paid evals, or stateful
  services just to write a plan; leave the working tree as found. Do not
  reset changes or switch branches.
- The only file ever written is a plan the user asked for: use their path,
  else the repo's plan convention, else `docs/plans/<feature-slug>.md`. Read
  an existing target first and preserve unrelated content.
- No issues, commits, PRs, or production changes as a side effect.
- Before presenting, check every AC has a step and a way to verify it.

## Output

Outcome and scope; current behavior and proposed approach; acceptance and
verification; the ordered checklist; compatibility; open decisions. Combine
sections when small. End with validation limits and the next actionable step.
