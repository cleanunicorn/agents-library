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

Review the diff against the main branch for: correctness, readability, architecture, security, performance, dead code, docs currency.

Output findings with severity (🔴 critical, 🟡 important, 🟢 nice-to-have), each with location and fix. Fix trivial ones; report the rest.
