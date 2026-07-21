# Skill audit — July 2026

A full audit-and-improve pass over the seven skills in `skills/`, followed by
the introduction of the eval infrastructure documented in [evals.md](evals.md).
This file is the record of what changed and why.

## Scope

All seven skills: `batch-merge-prs`, `describe-codebase`, `review-design`,
`review-pr`, `review-ux-psychology`, `simplify-sweep`, `triage-issues`.
No agent definitions (`agents/*.md`) were touched.

## Findings summary

| Skill | Lines before → after | Issues found | Type |
|-------|----------------------|--------------|------|
| batch-merge-prs | 210 → 195 | mechanics-heavy description; rationale essay; rigid git procedure in prose; no negative cases | preference |
| describe-codebase | 168 → 158 | mechanics-heavy description; essay; no negative cases | preference; **retirement candidate** (verify via ablation) |
| review-design | 264 → 255 | mechanics-heavy description; essay; fuzzy boundary vs review-ux-psychology and review-pr | preference |
| review-pr | 320 → 310 | mechanics-heavy description; essay; "clean up a diff" trigger collided with simplify-sweep | preference |
| review-ux-psychology | 439 → 423 | longest description in the repo (~250 words); essay | preference |
| simplify-sweep | 223 → 213 | mechanics-heavy description; essay; diff-scope overlap with review-pr | preference |
| triage-issues | 364 → 347 | mechanics-heavy description; essay | preference |

All skills were already under the 500-line bar, with reference files
(`domains/`, `lenses/`, `references/`) properly layered, so no content was
moved out of any SKILL.md body.

"Preference" = the skill encodes team workflow and guardrails (approval gates,
no-push rules, output contracts, named-principle rubrics) rather than a raw
capability the model lacks — durable, protected by the regression evals.

## Changes made

### 1. Frontmatter descriptions rewritten (all seven)

Descriptions are always in the model's context, so they were both the trigger
signal and a fixed token cost. Each was cut from ~140–250 words of internal
mechanics (fan-out counts, phase narration) to ~80–120 words of pure
trigger content: what the skill does, when to use it, and — new — explicit
**"Do NOT use … (use \<sibling\>)"** exclusions. The collection's total
always-loaded frontmatter roughly halved (~1,400 → ~700 words). The repeated
`even if they don't say the word "skill"` boilerplate was dropped from all
seven.

### 2. Cross-triggering boundaries sharpened

- **review-pr ↔ simplify-sweep** — "clean up a diff" removed from review-pr's
  triggers; verbs are now disjoint (*review/check* vs *simplify/declutter/
  tidy*), plus mutual exclusions by name.
- **review-design ↔ review-ux-psychology** — *how it looks* vs
  *conversion/metric*; mutual exclusions, plus a hand-off sentence in
  review-design's intro.
- **review-pr ↔ review-design** — the diff review keeps its lightweight design
  domain; review-design is the focused any-target design pass; both say so.
- **describe-codebase ↔ the review skills** — *explains, never judges or
  edits* vs review/cleanup; exclusions in both directions.
- **batch-merge-prs ↔ triage-issues ↔ review-pr** — PR queue vs issue backlog
  vs current branch; each excludes the other two by name.

### 3. "Why this shape" essays compressed (all seven)

Each skill carried a 12–23-line rationale essay. Compressed to 5–8 directive
lines keeping only the load-bearing invariants: sub-agents only
analyze/assess, verification screens false positives (review-pr,
review-ux-psychology), action happens later behind a gate/approval.

### 4. Rigid procedures converted to scripts

`batch-merge-prs` Phase 4 narrated a fully deterministic git sequence. It is
now [`skills/batch-merge-prs/scripts/merge-prs.sh`](../skills/batch-merge-prs/scripts/merge-prs.sh):
dirty-tree refusal, target-branch setup from `<remote>/<main>`,
`pull/<n>/head` fetch (fork-safe), `--no-ff` merge per PR, abort-on-conflict
(never half-resolves), temp-branch cleanup, and one `MERGED <n>` /
`SKIPPED <n> <reason>` ledger line per PR. Phase 4 of the SKILL.md now invokes
the script and interprets its ledger instead of narrating git commands. A
target of `auto` generates the branch name `batch/<YYYYMMDD-HHMM>` from the
current date/time — the default when the user doesn't name a branch.

The same treatment was applied to the other deterministic Phase 0 procedures:

- `review-pr` — [`scripts/diff-target.sh`](../skills/review-pr/scripts/diff-target.sh):
  main-branch detection plus the changed-file list (committed vs main,
  uncommitted, untracked) and combined diff.
- `batch-merge-prs` — [`scripts/list-prs.sh`](../skills/batch-merge-prs/scripts/list-prs.sh):
  gh auth check, main-branch detection, open-PR JSON work list.
- `triage-issues` — [`scripts/list-issues.sh`](../skills/triage-issues/scripts/list-issues.sh):
  gh auth check, repo slug, label vocabulary, open-issue JSON work list, with
  failure semantics matching the skill's error handling (issue list fatal;
  repo/labels degrade with a marker).

### 6. Eval-driven follow-ups

The first manual eval run (haiku, 1 trial/case, 67/70 passed) drove two fixes:

- `bm-h3` failed because Phase 3's "nothing merges until the user answers"
  could override an in-prompt pre-approval, stalling headless runs. Phase 3
  now treats a pre-approved selection/target in the original request as the
  answer and proceeds.
- `bm-n2`/`rd-n2` failed on an over-narrow "nothing to review" assertion; the
  regex was widened (`no commits`, `up to date`, `same as`) in all six case
  files that use it.
- Observed, no change made: haiku passes several report-only cases without
  loading the skill (all four triage report cases, two batch-merge report
  cases) — relevant input for future ablation runs.

### 5. Eval infrastructure added

- `skills/<name>/evals/cases.json` for all seven skills — 10 cases each
  (5 happy-path, 5 negative, with cross-triggering negatives tagged
  `expect_skill`), cheap outcome assertions only.
- `run_evals.py` at the repo root — isolated per-trial workspaces, fixture
  materialization with `gh` shims (fully offline), 3 trials/case,
  outcome-based grading with separate trigger telemetry, and
  `--ablation` / `--without-skill` arms for retirement detection.
- `eval-results/` added to `.gitignore`.
- **Manual-only by policy**: not wired to CI, hooks, or push automation.

See [evals.md](evals.md) for usage.

## Validation performed

- `run_evals.py --dry-run`: all 7 case files valid (schema, regexes, 5/5
  splits).
- All 8 fixtures materialize; `make test` green on the review-pr fixture
  branch; both `gh` shims serve data and log calls.
- `merge-prs.sh` run live against the pr-queue fixture: `MERGED 1` (shim title
  in the commit message), `SKIPPED 2 conflicts` with clean abort, exit 0.
- Two end-to-end agent smoke trials through the runner: `rp-n3` 1/1 and
  `dc-h1` 1/1, the latter with trigger telemetry correctly recording
  `skills-used: describe-codebase`.

The full 210-trial sweep and the ablation runs were **not** executed — they
are run manually (see the cost note in evals.md).

## Open items

- Run the full suite once to baseline pass rates
  (`python3 run_evals.py --trials 1`, then full).
- Run `python3 run_evals.py --ablation --skill describe-codebase`; if the
  without-arm matches, mark describe-codebase retired in the README but keep
  its evals as regression tests.
