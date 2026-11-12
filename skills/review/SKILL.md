---
name: review
description: >-
  Review the current branch's local diff for correctness, readability,
  architecture, security, performance, dead code, and docs currency;
  verify each finding, fix the trivial ones behind the lint and test gate,
  and report the rest by severity. Use before `ship` or to "check what I just built". Not for visual
  design or UX (review-ux-psychology) or merging PRs (batch-merge-prs).
---

# review

Read the branch's changes the way a careful senior reviewer would, check every finding against the code before reporting it, fix only what is trivial and safe, and report the rest.

## 1. Scope

- The diff: `git diff <main>...HEAD`, plus uncommitted changes. Detect the main branch; don't assume its name.
- Read enough surrounding code to judge each change: callers, callees, tests, and the docs that describe it.
- The user named dimensions ("readability only", "performance"): review only those. Otherwise use all of them.
- Note the mode: **report only** (the user said "report only" or "change nothing"), **default**, or **pre-approved fixes** (the user asked you to fix and commit).

## 2. Look for

| Dimension | Look for |
|---|---|
| correctness | wrong logic, off-by-one and boundary errors, unhandled errors and edge cases, broken contracts, callers left behind |
| readability | vague names, deep nesting, functions doing several things, misleading comments |
| architecture | layer violations, duplicated helpers, inconsistent shapes, logic in the wrong module |
| security | missing auth or validation, injection, secrets in code, sensitive data in logs or errors |
| performance | queries or I/O in loops (N+1), repeated work, needless allocation on hot paths |
| deadcode | unused functions, imports, parameters, branches; commented-out code |
| docs | README, docstrings, or comments the change made stale |
| tests | changed behavior with no test; tests that assert too little |

## 3. Verify each finding

Before reporting a finding, confirm it against the code: trace the input that triggers it, or run it. Drop what you cannot confirm, or mark it *uncertain* with what would settle it. Dead code means nothing references it, dynamic dispatch included.

## 4. Fix the trivial ones

Trivial means behavior-neutral and obvious: removing dead code, an unused import, a stale comment or docstring, a typo, a clearly local rename.

- **Report only**: change nothing.
- **Default**: apply trivial fixes only. Anything that changes behavior, including a confirmed correctness bug, is reported, not fixed: the author decides.
- **Pre-approved fixes**: also fix the confirmed findings the user approved, one commit per finding.

Every fix stays behind the gate: run the project's lint and tests after it. If the gate breaks, revert that fix and report it instead. Commit fixes as Conventional Commits (`refactor:`, `fix:`, `docs:`).

## 5. Report

Findings by severity, each with an ID, its location, the evidence, and the fix:

```
🔴 [correctness-1] src/auth.py:42 — `len(pw) > 8` rejects 8-character passwords; the spec says at least 8.
   Evidence: validate_password("abcdefgh") → False. Fix: use `>= 8`.
🟡 [performance-1] src/report.py:17 — one query per user inside the loop. Fix: batch with fetch_orders_for(ids).
🟢 [readability-1] src/util.py:8 — `d` → `deadline`.
```

- 🔴 critical: wrong behavior, security hole, data loss. 🟡 important: should fix before merge. 🟢 nice-to-have.
- List what you fixed (with commits) apart from what remains.
- No findings: say so plainly, with what you checked.
