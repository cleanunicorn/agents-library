---
name: review-pr
description: >-
  Review the current branch's local diff across ten quality domains
  (correctness, architecture, dead code, docs, refactor, testing, UX polish,
  visual design, security, conventions), with every finding independently
  verified to screen out false positives; then optionally apply fixes behind
  the project's lint/test gate. Use when the user wants to review a PR, a
  branch, or their changes before merging — "review my changes", "check what I
  just built", a pre-merge / pre-PR review. Works on the local diff before a
  GitHub PR exists; no `gh` or remote required. Do NOT use for whole-repo
  cleanup (use simplify-sweep), a visual-only design pass (use review-design),
  conversion/flow psychology (use review-ux-psychology), or explaining a
  codebase (use describe-codebase).
---

# review-pr

You are the **orchestrator** of a multi-domain review of the current branch.
The user has implemented a change and wants a fresh, thorough review before it
is finalized. Your job is to orient on the project, fan out ten specialized
review sub-agents, independently verify what they report, consolidate the
findings that survive, and help the user act on it.

The review target is always the **local branch diff** — everything on the
current branch that isn't yet in the main branch, plus any uncommitted
working-tree changes. This works before a GitHub PR exists; you never need `gh`
or a remote.

## Why this shape

"Is this correct?", "does this fit the architecture?", and "is this tested?"
are different mental modes — one domain per sub-agent, all sharing the same
project context, finds more than one generalist pass, and you merge the results
into one ranked list. The sub-agents **only analyze**; edits happen later,
under your control, behind the lint/test gate.

The finders are not infallible: each is primed to see problems through its one
lens, so the raw pile contains false positives — a "bug" the surrounding code
already prevents, "dead code" reached by dynamic dispatch, a "missing" test
that exists elsewhere. So between finding and presenting sits a dedicated
**verification** stage: a fresh, skeptical agent re-checks every finding
against the real code, and only survivors reach the user — or, in the
autonomous loop, get applied.

## Phase 0 — Orient (do this once, yourself)

Before dispatching anything, build an accurate map of the project and the
change. You gather this **once** and bundle it into every sub-agent's prompt, so
the ten agents don't each re-derive the same context.

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
   Phase 5. If you can't find them, you'll ask the user later rather than
   silently skipping verification.

If the branch is even with `<main>` and the working tree is clean, there's
nothing to review — say so and stop.

## Phase 1 — Fan out the review

Dispatch all ten domain sub-agents **in parallel** — issue all the Agent/Task
calls in a single message so they run concurrently. (This is the
`superpowers:dispatching-parallel-agents` pattern.)

**Model choice:** unless the user specified a model, run the fan-out
sub-agents on a **lesser model** than your own session — one tier down (e.g.
`haiku` from a `sonnet` session, `sonnet` from an `opus` session), via the
Agent tool's model parameter. Each domain prompt is narrow and single-lens,
so the cheaper tier is normally enough, and ten session-tier agents is an
expensive default. If a domain comes back clearly degraded (e.g. empty on a
diff that plainly has issues in its lens), re-run that one domain on the
session model.

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

Dispatch verification sub-agents **in parallel**, the same way you fanned out the
review — including the Phase 1 model default (lesser tier unless the user
specified a model). Run one verifier per finding; when the finding count is
large, batch several low-severity findings into a single verifier. A verifier
is a **fresh, skeptical** agent that did **not** produce the finding. Its
prompt is:

1. **The shared Phase 0 context** — project guidance, conventions, changed-file
   list.
2. **The single finding** to check — its location, problem, and proposed fix.
3. **The verifier instruction:** *You are a skeptical verifier. Do not assume the
   finding is correct. Open the actual file at the given location and read enough
   of the surrounding code to judge the claim on its merits — not just the diff
   hunk the finder saw. Decide three things: is the problem real, is it actually
   caused by this change, and is the proposed fix correct and safe? Default to
   `refuted` when the evidence does not clearly support the finding. Return the
   verdict schema below.*

Reading the **real code**, not the truncated diff hunk, is the point — a finder
reasoning from a partial hunk is exactly where false positives come from.

Each verifier returns:

```
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

Merge all **verified** findings (confirmed and uncertain) into one list:

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
```

Then summarize: how many findings at each severity, which domains were quiet,
and how many candidate findings verification filtered out — list those with
their one-line reasons so the user can challenge the screening. Keep it
skimmable — the user is choosing what to act on, not reading ten essays.

## Phase 4 — Decide

Ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop (significant only)** — apply all verified 🔴/🟡 findings,
  re-review, repeat until convergence or the round cap. Skips 🟢 nice-to-haves
  (see loop rules).
- **(c) Autonomous loop (everything, including nice-to-haves)** — apply *all*
  verified findings including 🟢, re-review, fix again, and keep going until a
  round surfaces nothing new. Use this when nice-to-haves matter — a 🟢
  "nice-to-have" is often a refactor that's actually worth doing. The most
  thorough path (see loop rules).
- **(d) Stop** — report only; change nothing.

## Phase 5 — Implement (for paths a, b, and c)

For each accepted finding, in order:

1. **Apply the edit** to the working tree.
2. **Run the gate** — the project's lint and test commands from Phase 0.
3. **Hold the gate hard.** If lint or tests go red, fix it or revert that one
   finding. Never commit red. A review that breaks the build is worse than no
   review.
4. **Commit on the current branch** — one commit per finding, Conventional
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
fix:       proposed change, concrete enough to act on
effort:    small | medium | large
```

Phase 2 verification then annotates each surviving finding with two more fields
(refuted findings are dropped, not annotated):

```
verdict:     confirmed | uncertain
confidence:  high | medium | low
```

## Autonomous loop rules (paths b and c)

Both loop paths repeat the same cycle — apply findings, re-run the full review
(fan-out → verify → consolidate, Phases 1–3) on the now-updated diff, then apply
again — until they converge. Because verification runs every round, the loop only
ever applies findings that survived it. The paths differ only in **which findings
they apply** and **when they stop**.

### Path b — significant only

1. Apply every **verified significant** finding — a 🔴 or 🟡 that Phase 2 returned
   as `confirmed`. 🟢 findings, and any finding left `uncertain` by verification,
   are reported but not auto-applied (they're judgment calls the user should opt
   into). Each fix follows the Phase 5 apply-and-gate steps.
2. Re-run the full review (fan-out → verify → consolidate) on the now-updated
   diff.
3. Repeat. **Stop** when either:
   - a review round produces no verified 🔴/🟡 findings (convergence), **or**
   - three apply-then-re-review rounds have completed (cost bound),
   whichever comes first.

### Path c — everything, including nice-to-haves

This is the thorough path: it treats 🟢 nice-to-haves as first-class work,
because a nice-to-have is frequently a refactor that genuinely improves the
change. It keeps fixing and re-reviewing until the review surfaces **nothing
new**.

1. Apply **every verified** finding the round produced — 🔴, 🟡, *and* 🟢 — that
   verification marked `confirmed`. Findings left `uncertain` are reported for
   the user, not auto-applied. Each fix follows the Phase 5 apply-and-gate steps.
2. Re-run the full review (fan-out → verify → consolidate) on the now-updated
   diff.
3. Track findings already addressed across rounds (by location + fix) so you can
   tell genuinely **new** findings from ones that keep resurfacing. Repeat the
   apply-then-re-review cycle. **Stop** when either:
   - a review round produces **no new findings** at any severity — every finding
     it raises is one already applied or already declined-as-unfixable in an
     earlier round (full convergence), **or**
   - **six** apply-then-re-review rounds have completed (a safety bound to
     prevent an unbounded refactor-chasing loop — refactor findings can beget
     more refactor findings, so a hard cap matters here even though convergence
     is the goal),
   whichever comes first.
4. If a 🟢 finding is purely cosmetic taste with no clear improvement, or two
   rounds in a row keep re-proposing the same change you already applied, treat
   it as addressed and don't churn on it — convergence, not perfection, is the
   target.

### Common to both paths

- Each round reports: findings applied, the gate result, what verification
  filtered out, and what remains. On stop, summarize total commits made and (for
  path b) any 🟢 or uncertain findings left for the user.
- The loop is **stateless across invocations**: hitting the round cap is not the
  end of the road. Because each run re-orients and re-reviews from the current
  diff, the user can simply re-invoke this skill to run another set of rounds on
  the updated branch — a fresh run naturally continues where the last one
  stopped. Mention this in the stop summary so the user knows it's an option.

## Error handling

- **No diff** (branch even with main, clean tree): report nothing to review and
  stop.
- **Lint/test command not found:** warn and ask the user whether to proceed
  without the gate or supply the command. Never silently skip verification.
- **A sub-agent fails or returns nothing:** note it, continue with the others.
- **A verifier fails or is inconclusive:** treat the finding as `uncertain` —
  surface it for the user rather than dropping it or auto-applying it.
- **Verification refutes a finding:** drop it from the presented list but record
  it in the filtered-out tally with its one-line reason; never silently discard.
- **A fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it "attempted, reverted — needs manual work," and continue with the rest.
- **Two findings' edits conflict:** one-commit-per-finding already serializes
  them; apply sequentially and re-run the gate after each.
