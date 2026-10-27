---
name: simplify-sweep
description: >-
  Survey the repository, a path, or the branch diff for behavior-preserving
  simplifications — duplication, dead code, deep nesting, unclear names, stale
  docs — and optionally apply them behind the lint and test gate. Use to
  simplify, declutter, tidy, or reduce complexity. Never fixes bugs. Not for
  a full diff review (review-pr), explaining code (describe-codebase), or
  planning an unbuilt feature (plan-feature).
---

# simplify-sweep

## Overview

Find code and docs that can be made simpler without changing what the code
does, across a target the user chooses, and optionally apply the changes behind
the project's lint and test gate.

## When to use

Use to simplify, declutter, tidy, or reduce complexity. Not for a diff review
(review-pr), explaining code (describe-codebase), or planning an unbuilt
feature (plan-feature). Never fixes bugs: a change that alters behavior is out
of scope, so note it and move on.

## What good looks like

Target: the whole repository by default, a path or glob if named, or the branch
diff (against the detected main branch, plus staged, unstaged, and untracked
work) for "diff" or "my changes". Ask if it is ambiguous. Skip generated code,
vendored dependencies, lockfiles, minified bundles, binaries, and gitignored
paths; if a large surface forces you to cap the scan, say what was left out.

Read the project's guidance first and simplify toward its own style, never
personal taste. Survey in parallel where the host supports delegation,
otherwise locally, sharding a large repo by module so related code stays
together. Merge duplicates, rank by severity, and report the net lines the
accepted changes would remove.

Lenses and what each looks for:

- **Redundancy and dead code**: duplicated logic extractable to a helper,
  copy-pasted variants, repeated magic values, redundant boolean logic, unused
  or unreachable code (confirm with a project-wide search; mind dynamic
  dispatch). Remove before extracting.
- **Complexity and structure**: deep nesting that early returns would flatten,
  mixed-responsibility functions with an obvious split, needless indirection,
  over-abstraction with a single user.
- **Clarity and idiom**: vague internal names, verbose constructs with an idiom
  the codebase already uses, over-broad types, double negatives.
- **Docs**: duplicated docs, docs drifted from code, over-long prose, comments
  that restate the code. Tighten; never strip a needed contract or the why.

Deletion is a finding: a whole capability nobody uses that way (an abstraction
with one implementation, a format nothing reads) is often the best result.
List these separately as removal candidates with the lines they would take
with them. Removing behavior is not this skill's to apply.

## Boundaries

- Behavior-preserving only; never change public API names, serialized fields,
  or anything an external contract depends on.
- Surveyors are read-only; only the apply step edits, and only when asked.
- Never push or touch the remote. All work is local on the current branch.
- If the request already chose a path ("report only", "apply the significant
  ones", "fix these"), take it. Otherwise ask whether to apply selected
  findings, run the loop, or stop; warn that a whole-repo loop can run long.
- One commit per fix (Conventional Commits, e.g. `refactor(auth): ...`).
  Apply each simplification to every instance of the same shape found by
  searching the repo, and report `N found / N fixed / N left`; instances
  outside the target are reported, not edited, without the user's say-so.
- Run the project's lint and test commands (docs checks for docs-only changes)
  before each commit and never commit red: fix it or revert that fix and note
  it needs manual work. If you cannot find the commands, ask rather than skip.

## Output

A ranked list with location, what is more complex than needed, the size in
numbers, and the behavior-preserving fix; then counts per severity, quiet
lenses, net lines removable, surface scanned or skipped, and removal
candidates. After applying, report commits, the gate result, and what remains.
