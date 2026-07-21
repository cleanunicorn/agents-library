# Changelog (archive)

**The changelog now lives in
[GitHub Releases](https://github.com/cleanunicorn/agents-library/releases).**
Releases are cut automatically when a PR merges to main, sized by the
Conventional-Commit prefix of the PR title, and their notes are generated from
the merged PRs — see [Releasing](README.md#releasing) in the README and
[.github/workflows/auto-release.yml](.github/workflows/auto-release.yml).

This file is a frozen archive of the history from before release automation
was adopted (2026-07-21). It is not updated by hand anymore.

## 2026-07-21 — adopted release automation

Ships as the first tagged release; entries below were in flight when the
automation landed.

### Added

- Earheart-style release automation: `.github/workflows/auto-release.yml`
  (auto-release on PR merge — Conventional-Commit PR title decides the bump,
  version lands in `.codex-plugin/plugin.json`, tag `v<version>`, GitHub
  release with generated notes) and `.github/workflows/pr-title.yml`
  (CI check enforcing the load-bearing PR-title format). Release notes replace
  this file as the changelog.

### Added

- Eval suites for all seven skills (`skills/<name>/evals/cases.json`): 10
  outcome-based cases each — 5 happy-path, 5 negative, with cross-triggering
  negatives tagged with the sibling skill that should fire instead. Assertions
  are cheap regex/file/shell checks on outcomes; no LLM-as-judge.
- `run_evals.py`, the shared eval runner at the repo root: isolated per-trial
  workspaces, offline fixtures with fake `gh` shims, 3 trials per case,
  outcome-based grading with separate skill-trigger telemetry, and
  `--ablation` / `--without-skill` arms for retirement detection.
  **Manual-only by policy** — never wired to CI, hooks, or push automation.
- `skills/batch-merge-prs/scripts/merge-prs.sh`: the deterministic local
  batch-merge procedure (dirty-tree refusal, fork-safe `pull/<n>/head`
  fetches, `--no-ff` merges, abort-on-conflict, `MERGED`/`SKIPPED` ledger),
  extracted from Phase 4 prose into an invokable script.
- `docs/evals.md` (how the eval system works and how to run it) and
  `docs/skill-audit-2026-07.md` (the full audit record).

### Changed

- Rewrote all seven skill frontmatter descriptions: cut internal mechanics,
  kept trigger phrases, added explicit "Do NOT use … (use \<sibling\>)"
  exclusions. Always-loaded frontmatter roughly halved (~1,400 → ~700 words).
- Sharpened cross-triggering boundaries between review-pr / simplify-sweep
  (removed "clean up a diff" from review-pr), review-design /
  review-ux-psychology (looks vs conversion), describe-codebase / the review
  skills (explain vs judge), and batch-merge-prs / triage-issues / review-pr
  (PR queue vs issue backlog vs current branch).
- Compressed the "Why this shape" rationale essays in all seven SKILL.md
  bodies to short directive paragraphs keeping only the load-bearing
  invariants.
- `batch-merge-prs` Phase 4 now invokes `scripts/merge-prs.sh` and interprets
  its ledger instead of narrating git commands.
- README: added a "Skill Evals" section. AGENTS.md project section: layout now
  lists `evals/` and `scripts/`, and the commands bullet documents
  `run_evals.py` as the (manual-only) test entry point.
- `.gitignore`: added `eval-results/`.

## 2026-07-16

### Added

- `templates/AGENTS.md` scaffold: prerequisites, golden rules, GitHub flow,
  Communication section with confidence indicator, Conventional Commits, and
  release automation guidance.

## 2026-07-12

### Added

- Codex plugin metadata (`.codex-plugin/plugin.json`) — the repo installs as a
  Codex plugin as well as a Claude Code plugin.

## 2026-07-09

### Added

- `review-ux-psychology` skill: behavioral-design review of a flow's decision
  architecture across six lenses (decision fatigue & defaults, goal-gradient,
  reciprocity, endowment/IKEA, loss aversion, anchoring), each finding tied to
  a named principle and a target product metric, with a verification pass and
  gated apply loops.

### Fixed

- review-ux-psychology: loop-convergence gap closed, lens→ID mapping
  clarified, and merged multi-principle entries defined to expand into
  per-lens fixes at apply time.

## 2026-07-08

### Added

- `review-pr` verification stage: every finding is independently re-checked by
  a fresh skeptical agent before being presented or auto-applied; refuted
  findings are dropped into a visible filtered-out tally.

## 2026-06-19

### Added

- `UIDesigner` agent, the `review-pr` visual-design domain, and the
  `review-design` skill (five design lenses judged against the project's own
  design tokens).

## 2026-06-13

### Added

- `review-pr` path (c): thorough autonomous loop that also applies verified
  nice-to-haves and runs until a round surfaces nothing new (six-round cap).

### Fixed

- Marketplace manifest source-path format.

## 2026-06-10

### Added

- `triage-issues` skill: per-issue assessment sub-agents that read the thread
  *and the codebase* (validity, completeness, classification, duplicate
  detection, code-grounded effort), duplicate clustering, a ranked decision
  table, per-action approval before any GitHub write, and approved easy-win
  fixes as one PR per issue from isolated worktrees.

### Fixed

- triage-issues hardening: issue content treated as untrusted data (including
  by fix sub-agents), shell-safe comment bodies, closures aborted when their
  approved comment fails to post, duplicate closures via `--duplicate-of`,
  incomplete verdicts treated as failed assessments, label-creation failures
  skipped gracefully, remote branches cleaned up on post-push bail-outs.

## 2026-06-08

### Added

- `simplify-sweep` skill: whole-repo/path/diff survey across four
  behavior-preserving simplification lenses, with sharding, ranked findings,
  and a gated apply loop.
- `describe-codebase` skill: read-only orientation briefs across three
  explorer lenses, plus flow-trace scope; optional ARCHITECTURE.md persistence
  on explicit confirmation.
- Skill-creator enabled for this repo.

## 2026-06-06

### Added

- `batch-merge-prs` skill: per-PR triage sub-agents, ranked include/skip
  table, user-confirmed local `--no-ff` batch merges; never pushes or closes
  PRs on GitHub.

## 2026-06-05

### Added

- Initial release: seven single-purpose coding agents (Architect, DeadWood,
  DocBot, Refactor, Sentinel, TestForge, UXPolish), the generic AGENTS.md
  working guide, the `review-pr` skill, and packaging as a Claude Code plugin
  marketplace.

### Changed

- Dropped the plugin version field in favor of commit-SHA versioning.
