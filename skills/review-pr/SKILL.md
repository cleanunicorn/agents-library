---
name: review-pr
description: >-
  Review the current branch's local diff across ten quality domains, verify
  every finding, and optionally apply fixes behind the lint and test gate.
  Use to review a PR, a branch, or "check what I just built" before merging.
  Not for whole-repo cleanup (simplify-sweep), a visual-only design pass
  (review-design), conversion psychology (review-ux-psychology), or
  explaining a codebase (describe-codebase).
---

# review-pr

You are the **orchestrator** of a multi-domain review of the current branch:
orient on the project, fan out ten review sub-agents, independently verify what
they report, consolidate the findings that survive, and help the user act on
them. The target is always the **local branch diff** — everything not yet in
the main branch, plus uncommitted and untracked work — so it works before a PR
exists, without `gh` or a remote.

## Phase 0 — Orient

Gather this context **once** and bundle it into every sub-agent's prompt.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and any architecture notes. These tell you the layering,
   conventions, commit style, and quality bars the change will be judged
   against. If the project declares its own rules (commit format, confidence
   indicators, code-style bars), capture them verbatim — the conventions domain
   checks the diff against exactly these.
2. **Compute the review target.** Run `bash scripts/diff-target.sh` — it
   detects the main branch deterministically (call it `<main>`; never
   hard-code `main`) and prints the changed-file list: committed vs `<main>`,
   uncommitted, and untracked. `bash scripts/diff-target.sh diff` prints the
   combined diff. The review target is that union; capture the file list and
   the diff. If the script exits `FATAL` (no main branch detectable), ask the
   user which branch to diff against instead of guessing.
3. **Find the commands that matter.** Detect how the project lints, formats,
   tests, and builds — from the docs first, then config files (package.json
   scripts, Makefile, pyproject, etc.). You'll need these for the gate in
   Phase 5.

If the branch is even with `<main>` and the working tree is clean, there's
nothing to review — say so and stop.

## Phase 1 — Fan out the review

Dispatch all ten independent domain sub-agents concurrently, batching to the
host's limits.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only review, or inherit the session
model. Retry at the session tier only when required fields or assigned coverage
are missing.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** you gathered in Phase 0: the project guidance summary,
   the detected conventions, the changed-file list, and the diff (or, for a
   large diff, the changed-file list plus instructions to read what it needs).
2. **The domain prompt** — read the matching file from `domains/` and include it
   verbatim. That file is the sub-agent's entire instruction set for what to
   look for.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; return findings in this exact
   schema, or an empty list if you find nothing worth raising.*

The ten domains and their files:

| Domain | Emoji | File | Looks for |
|--------|-------|------|-----------|
| Correctness | 🐛 | `domains/correctness.md` | Logic bugs, edge-case crashes, races, wrong behavior. **The only bug-hunting domain.** |
| Architecture | 🏗️ | `domains/architecture.md` | Does the change fit the project's structure, and is it coherent in itself. |
| Dead code | 🌲 | `domains/deadcode.md` | Code the diff leaves unused/unreachable; removable without behavior change. |
| Docs | 📝 | `domains/docs.md` | Missing or stale documentation the project expects for the changed surface. |
| Refactor | 🔧 | `domains/refactor.md` | Simplification, readability, DRY — without changing behavior. |
| Testing | 🧪 | `domains/testing.md` | Coverage gaps: happy paths, failure paths, edge cases. |
| UX polish | 🎨 | `domains/ux-polish.md` | Interaction friction and missing states (frontend projects; no-op otherwise). |
| Visual design | 🖌️ | `domains/design.md` | Visual-design principles: hierarchy, spacing, type, color/contrast, dark mode, depth (frontend; no-op otherwise). |
| Security | 🛡️ | `domains/security.md` | Auth guards, error/info leakage, secrets, input validation. |
| Conventions | 📐 | `domains/conventions.md` | The diff vs the project's own declared rules (AGENTS.md/CLAUDE.md). |

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole review on one domain.

## Phase 2 — Verify findings (don't trust the finders blindly)

The finders are optimistic: each is primed to raise problems in its lens, so the
raw pile they return contains false positives. Never present a finding — and
never, in the autonomous loop, apply one — on a finder's word alone. Every
finding is independently re-checked here first.

Dispatch at most four verification batches concurrently, grouped by domain and
severity. A fresh, skeptical verifier that produced none of its batch's findings
returns a separate verdict for every finding. Use the Phase 1 model rule.
Each verifier's prompt is:

1. **The shared Phase 0 context** — project guidance, conventions, changed-file
   list.
2. **The findings in its batch** — each location, problem, and proposed fix.
3. **The verifier instruction:** *You are a skeptical verifier. Do not assume the
   finding is correct. Open the actual file at the given location and read enough
   of the surrounding code to judge the claim on its merits — not just the diff
   hunk the finder saw. Decide three things: is the problem real, is it actually
   caused by this change, and is the proposed fix correct and safe? Default to
   `refuted` when the evidence does not clearly support the finding. Return the
   verdict schema below.*

Reading the **real code**, not the truncated diff hunk, is the point — a finder
reasoning from a partial hunk is exactly where false positives come from.

Each verifier returns a list with one record per finding:

```
id:          <finding id>
verdict:     confirmed | refuted | uncertain
confidence:  high | medium | low
rationale:   one line — what the code actually shows
correction:  (optional) a better fix, when the problem is real but the finder's fix was wrong
```

Fold the verdicts back into the findings:

- **confirmed** → carries through to Phase 3, tagged ✓ verified.
- **uncertain** → carries through, tagged ⚠ unverified, so the user knows it's a
  judgment call — and so the autonomous loop leaves it for the user instead of
  auto-applying it.
- **refuted** → dropped from the main list. Keep a short **filtered-out tally**
  (count, plus each dropped finding's ID and one-line reason) so the user can see
  what was screened and push back if they disagree. Never silently discard.
- If a verifier itself fails or comes back inconclusive, treat the finding as
  **uncertain** rather than dropping it — surface it, don't auto-apply it.

When a verifier supplies a `correction`, replace the finder's `fix` with it
before moving on — the problem was real, the fix wasn't.

## Phase 3 — Consolidate & present

Merge all **surviving** findings (confirmed and uncertain) into one list:

- **Deduplicate across domains.** The same location with the same fix collapses
  into one entry; keep the higher severity. (Several domains will legitimately
  flag the same line for different reasons — surface that once.)
- **Rank** by severity (🔴 → 🟡 → 🟢), then by domain.
- **Assign stable IDs** of the form `<domain>-<n>` (e.g. `correctness-1`).

Present a grouped, ID'd list to the user. Each finding renders on one line, with
its verification tag:

```
[correctness-1] ✓ 🔴 correctness · src/auth.ts:42 — token expiry uses `<` not
                `<=`, off-by-one lets expired tokens through — change to `<=` — small
                measured: 1 token accepted at exactly expiry
                gap: auth.spec.ts tests expiry−1s and expiry+1s, never the boundary
```

Render `measured` and `gap` on their own indented lines under any finding that
has them.

Then summarize: how many findings at each severity, which domains were quiet,
and how many candidate findings verification filtered out — list those with
their one-line reasons so the user can challenge the screening. Keep it
skimmable — the user is choosing what to act on, not reading ten essays.

## Phase 4 — Decide

If the original request already chose a path — "report only", "fix everything", "apply the significant ones", "fix these IDs" — take that path without asking; the request is the authorization. Otherwise ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop, significant only** — see *Autonomous loop rules*.
- **(c) Autonomous loop, everything** — including 🟢 nice-to-haves, which are
  often refactors worth doing; see *Autonomous loop rules*.
- **(d) Stop** — report only; change nothing.

## Phase 5 — Implement (for paths a, b, and c)

For each accepted finding, in order:

1. **Apply the edit** to the working tree.
2. **Fix every instance, not just the one found.** Search the whole
   repository for the same problem — its *shape*, not the literal text. This is
   a grep, not a second review fan-out. Apply the same fix wherever it is
   mechanical and safe, in the same commit, and record the search and its count
   (`N found · N fixed · N left`) in the commit body and in the round report.
   Two limits hold: a swept site earns the same scrutiny Phase 2 gave the
   original — open it and confirm the problem is really there and the fix is
   safe *there*, because a verdict confirmed at one location does not carry to
   forty; and instances outside the review target (the branch diff) are
   reported with their count and edited only on the user's say-so — in the
   autonomous loop they are reported, never auto-applied. An instance needing
   judgement is listed for the user instead of forced. A finding fixed at one
   site while identical ones remain is not fixed.
3. **Close the finding's `gap` in the same commit** — widen the test, add the
   lint rule, extend the check to the shape that slipped through. A defect fix
   that leaves the thing which missed it untouched will be needed again. If the
   gap genuinely can't be closed here, say so in the commit body.
4. **Run the gate** — the project's lint and test commands from Phase 0.
5. **Hold the gate hard.** If lint or tests go red, fix it or revert that one
   finding. Mark a revert `attempted, reverted — needs manual work`, then
   continue with the remaining findings. Never commit red.
6. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`), scoped to the finding's domain.
   One commit per finding keeps the history reviewable and lets any single fix
   be reverted cleanly.

If you couldn't find the lint/test commands in Phase 0, ask the user for them
or whether to proceed without the gate — don't silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:        <domain>-<n>            e.g. correctness-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
domain:    <one of the ten>
location:  path:line
problem:   one-line description of what's wrong or missing
measured:  the value you observed and what it is judged against, when the
           finding is measurable (`3.73:1, AA needs 4.5:1`; `buffers the whole
           stream, no cap`; `4 call sites, 3 shapes`) — else `not measured`
gap:       for a defect: what was supposed to catch this, and why it didn't
           (`contrast.test.ts covers only the pairs it lists`; `no test exercises
           a chunked body`) — else `n/a`
fix:       proposed change, concrete enough to act on
effort:    small | medium | large
```

`measured` and `gap` are what separate a finding a maintainer acts on from one
they argue with. A finding whose `measured` is an adjective isn't ready; a
defect whose `gap` is `n/a` should say why nothing could have caught it.

Phase 2 annotates each surviving finding with `verdict` (confirmed |
uncertain) and `confidence` (high | medium | low); refuted findings are dropped.

## Autonomous loop rules (paths b and c)

| Path | Apply | Stop when | Cap |
| --- | --- | --- | --- |
| b — significant | confirmed 🔴 and 🟡 | no confirmed significant findings remain | 3 rounds |
| c — everything | every confirmed severity | no new surviving findings remain | 6 rounds |

For either row: apply each finding through Phase 5, re-run Phases 1–3, and
repeat. Never auto-apply `uncertain` findings. Track addressed findings by
location + fix; retire repeated or declined-as-unfixable proposals instead of
churning. Report each round's fixes, gate, filtered findings, and remainder,
then the total commits and deferred findings. The cap is per invocation; a
later invocation starts from the updated diff.
