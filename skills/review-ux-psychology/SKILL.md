---
name: review-ux-psychology
description: >-
  Review a UI or flow against the psychology of how people actually decide, to
  move a specific product metric — for a target you choose: a single screen or
  flow (onboarding, signup, checkout, pricing, a form), a path/glob of frontend
  files, or the current branch diff. Orients on the product goal and the metric
  the flow is being optimized for, best-effort renders the flow to screenshots or
  a short screen capture so findings are grounded in what the user actually sees,
  then fans out parallel sub-agents across six behavioral-design lenses (decision
  fatigue & smart defaults, goal-gradient progress, reciprocity & value-first,
  endowment & the IKEA effect, loss aversion & framing, anchoring & the contrast
  effect). Every finding traces to a named principle and names the metric it is
  meant to move. It then independently verifies each finding against the real
  code/flow to screen out false positives, consolidates and ranks the survivors
  by expected impact, presents them for you to pick from, and either applies a
  chosen subset or runs an autonomous improve-until-converged loop behind the
  project's lint/build gate. Use this whenever the user wants to review the UX or
  conversion of a flow, lift a metric (activation, signup, trial-to-paid,
  checkout completion, retention), critique onboarding / signup / checkout /
  pricing, reduce friction or drop-off, audit a form for decision fatigue, or
  find where a UI fights how users think — even if they don't say the word
  "skill". It's the behavior-and-conversion counterpart to `review-design`'s
  visual-craft review. No `gh` or remote required.
---

# review-ux-psychology

You are the **orchestrator** of a multi-lens UX-psychology review. The user wants
a UI or flow judged not against how it *looks* but against how people actually
think and decide — in the service of moving a **specific product metric**. Your
job is to orient on the product goal and that metric, fan out specialized
sub-agents across six behavioral-design lenses, independently verify what they
report, consolidate the survivors, and help the user act on it behind a
lint/build gate.

This is the behavior-and-conversion counterpart to `review-design`. Where
`review-design` reviews the *visual craft* of a UI (hierarchy, spacing,
typography, color, depth), `review-ux-psychology` reviews the *decision
architecture* — the defaults, progress, framing, and reference points that decide
whether a user finishes a flow. The two are complementary: a screen can be
beautifully laid out and still leak users because it starts them at 0%, gates
value behind a signup wall, or shows a price in isolation.

Three properties frame everything below:

- **Every finding traces to a named principle.** A UX critique that can't name the
  psychology it serves is opinion, not review — the six lenses below are the
  rubric (decision fatigue, goal gradient, reciprocity, endowment/IKEA, loss
  aversion, anchoring/contrast). Each finding names its principle.
- **Every finding names the metric it moves.** This skill exists to move a
  specific target metric (activation, signup conversion, trial-to-paid, checkout
  completion, feature adoption, retention). Each finding states which metric it is
  meant to move and in which direction, so findings can be ranked by leverage and
  validated afterward. A corollary keeps fixes real: a fabricated signal — fake
  progress, a phantom reference price, invented urgency — does not durably move a
  real metric (users learn, and the effect evaporates), so the fix must rest on a
  *true* signal (real progress the user made, a real reference number, a real
  stake). This is optimization discipline, not a compliance checkbox.
- **You never push or touch the remote.** All work is local: edits on the current
  branch, gated on the project's lint and build. No `gh`, no remote required.

## Why this shape

A single reviewer scanning a flow for "what hurts the metric" misses things,
because "is the user forced to make too many decisions?", "does the flow start
them at zero?", "did we give value before asking?", "have they built something
they'd hate to lose?", "is inaction framed as free?", and "is this price shown in
isolation?" are six different mental modes that compete for attention. Six focused
sub-agents, each holding exactly one principle and the same shared product
context, find more and find it more sharply. You then merge their findings into
one ranked list so the user sees signal, not six separate reports.

The sub-agents **only analyze** — they never edit. Implementation happens later,
under your control, behind a lint/build gate. Keeping review and implementation
separate is what makes the findings trustworthy and the applied changes safe.

But the finders are not infallible. Each is primed to see its one principle
everywhere, so some of what it returns is a false positive — a "blank form" that's
prefilled a component deeper, a "0% start" that's actually a deliberate reset, an
"isolated price" that sits next to an anchor the finder didn't scroll to. Trusting
those blindly wastes the user's attention, and in the autonomous loop it gets a
pointless change committed. So between finding and presenting there is a dedicated
**verification** stage: every finding is independently re-checked against the real
code/flow by a fresh, skeptical agent, and only what survives reaches the user.

## Phase 0 — Orient (do this once, yourself)

Before dispatching anything, build an accurate map of the project, the flow, and
what it's being optimized for. You gather this **once** and bundle it into every
sub-agent's prompt, so the six agents don't each re-derive the same context.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and any product/design notes. Capture the conventions, commit
   format, and confidence-indicator rules verbatim.
2. **Pin the target metric.** UX-psychology findings are only as useful as the
   metric they move, so establish it up front: which metric is this flow being
   optimized for — signup conversion, activation, trial-to-paid, checkout
   completion, feature adoption, retention? If the user hasn't said, **ask** (and
   offer the likely candidates for the flow). Every finding will be framed and
   ranked by its expected effect on this metric.
3. **Learn the product and the flow.** Capture:
   - **what the flow is trying to get the user to do**, and where in it the target
     metric is won or lost;
   - **where value is delivered vs. where the ask happens** — does the user get
     something useful before, or only after, giving up email / payment / effort?
   - **the friction surface** — forms and their fields, choice points, gates,
     paywalls, progress indicators, pricing displays, and CTA copy;
   - **the existing component/state patterns** — how defaults, progress bars,
     empty states, modals, and buttons are already built, so fixes reuse them.
4. **See the flow as the user sees it (best effort).** Static code is a thin
   substrate for judging decision architecture, so try to render the flow:
   - start the project's dev server and drive the flow, capturing **screenshots**
     (or a short **screen recording / video**) of each step, using whatever
     preview/screenshot tooling the project or this harness offers;
   - if you can't drive it yourself, **ask the user** for screenshots or a short
     recording of the flow.
   Pass the rendered frames to the sub-agents so findings anchor to what's
   actually on screen. If you genuinely cannot render it, fall back to reading the
   source — and **say so**, so the user knows the review is code-only.
5. **Detect the main branch.** Don't hard-code `main` — detect it
   (`git symbolic-ref refs/remotes/origin/HEAD`, or fall back to whichever of
   `main`/`master` exists). Call it `<main>`.
6. **Resolve the target.** From the user's request:
   - a named screen/flow or a path/glob → just those files;
   - "diff" / "my changes" / `--diff` → the current branch diff
     (`git diff <main>...HEAD`) plus working-tree changes (`git diff`,
     `git status`);
   - nothing specified → ask which flow to review. Don't scan the whole repo
     blindly — a psychology review needs a focused flow to reason about.
   Capture the resolved file list and the **user-journey order** (the sequence of
   screens/steps), because several lenses reason about sequence.
7. **Find the commands that matter.** Detect how the project lints, formats, and
   builds the frontend — docs first, then config (package.json scripts, etc.).
   You'll need these for the gate in Phase 5.

If the resolved target has **no user-facing decision surface** (pure backend, a
library, or a purely presentational screen with no forms, choices, gates,
pricing, or CTAs), say there's nothing to UX-psychology-review and stop — suggest
`review-design` if they wanted a visual pass.

## Phase 1 — Fan out the review

Dispatch all six lens sub-agents **in parallel** — issue all the Agent/Task calls
in a single message so they run concurrently. (This is the
`superpowers:dispatching-parallel-agents` pattern.)

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** you gathered in Phase 0: the project guidance summary,
   the **target metric**, the product/flow map (goal, value-vs-ask, friction
   surface, journey order), the **rendered screenshots/video** (or a note that the
   review is code-only), and the resolved target file list (plus the diff, for a
   `--diff` target).
2. **The lens prompt** — read the matching file from `domains/` and include it
   verbatim. That file is the sub-agent's entire instruction set for what to look
   for.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; read the files (and look at the
   provided frames) as you need; every fix must rest on a true signal so it
   durably moves the metric; name the metric each finding targets; return findings
   in this exact schema, or an empty list if you find nothing worth raising.*

The six lenses and their files:

| Lens | Emoji | File | ID prefix | Principle & what it looks for |
|------|-------|------|-----------|-------------------------------|
| Decision fatigue & smart defaults | 🎯 | `domains/decision-defaults.md` | `defaults` | Choice overload; blank forms; no preselected common choice; buttons that don't preview the outcome. |
| Goal-gradient progress | 📈 | `domains/goal-gradient.md` | `progress` | Starting the user at 0%; empty onboarding; no credit for what's already done; distance emphasized over momentum. |
| Reciprocity & value-first | 🎁 | `domains/reciprocity.md` | `reciprocity` | Asking before giving; signup walls before any value; results held hostage; email/payment demanded up front. |
| Endowment & the IKEA effect | 🔨 | `domains/endowment-ikea.md` | `endowment` | Commitment asked before the user builds/owns anything; nothing to lose by leaving; "Sign up" where "Continue" fits. |
| Loss aversion & framing | ⚖️ | `domains/loss-aversion.md` | `loss-aversion` | CTAs framed as gains not losses; no stakes for inaction; abstract benefits over concrete things at risk; frictionless "maybe later". |
| Anchoring & the contrast effect | ⚓ | `domains/anchoring-contrast.md` | `anchoring` | Prices/costs shown in isolation; no reference anchor; absolute where relative lands; ordering that sets a bad comparison. |

The **ID prefix** column is the `<lens>` value each finding's `id` uses (e.g.
`progress-1` comes from `domains/goal-gradient.md`) — the mapping isn't always the
filename's leading token, so this column is the lookup.

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole review on one lens.

## Phase 2 — Verify findings (don't trust the finders blindly)

The finders are optimistic: each is primed to see its principle everywhere, so the
raw pile they return contains false positives. Never present a finding — and
never, in the autonomous loop, apply one — on a finder's word alone.

Dispatch verification sub-agents **in parallel**, the same way you fanned out the
review. Run one verifier per finding; when the finding count is large, batch
several low-severity findings into a single verifier. A verifier is a **fresh,
skeptical** agent that did **not** produce the finding. Its prompt is:

1. **The shared Phase 0 context** — project guidance, target metric, flow map, and
   the rendered frames.
2. **The single finding** to check — its location, problem, proposed fix, and the
   metric it claims to move.
3. **The verifier instruction:** *You are a skeptical verifier. Do not assume the
   finding is correct. Open the actual file at the given location (and look at the
   rendered frame) and read enough of the surrounding code/flow to judge the claim
   on its merits — not just the snippet the finder saw. Decide three things: is the
   anti-pattern actually present (e.g. is the field really blank, or prefilled
   deeper in a component?), is the named principle correctly applied, and would the
   proposed fix plausibly move the stated metric on a true signal? Default to
   `refuted` when the evidence does not clearly support the finding. Return the
   verdict schema below.*

Reading the **real code/flow**, not the finder's snippet, is the point — a finder
reasoning from a partial view is exactly where false positives come from.

Each verifier returns:

```
verdict:     confirmed | refuted | uncertain
confidence:  high | medium | low
rationale:   one line — what the code/flow actually shows
correction:  (optional) a better fix, when the problem is real but the finder's fix was wrong
```

Fold the verdicts back into the findings:

- **confirmed** → carries through to Phase 3, tagged ✓ verified.
- **uncertain** → carries through, tagged ⚠ unverified, so the user knows it's a
  judgment call — and so the autonomous loop leaves it for the user instead of
  auto-applying it.
- **refuted** → dropped from the main list. Keep a short **filtered-out tally**
  (count, plus each dropped finding's ID and one-line reason) so the user can see
  what was screened and push back. Never silently discard.
- If a verifier itself fails or is inconclusive, treat the finding as **uncertain**
  rather than dropping it.

When a verifier supplies a `correction`, replace the finder's `fix` with it before
moving on.

## Phase 3 — Consolidate & present

Merge all **verified** findings (confirmed and uncertain) into one list:

- **Deduplicate across lenses.** The same location with the same fix collapses
  into one entry; keep the higher severity. Several lenses will legitimately flag
  the same moment for different reasons — a signup screen can be both a reciprocity
  failure (no value given) and an endowment failure (nothing built). Surface it
  once, noting both principles and carrying both proposed fixes (the lenses often
  prescribe different changes for the same moment).
- **Rank** by severity (🔴 → 🟡 → 🟢), then by **expected impact on the target
  metric** — lead with what most changes whether the user finishes the flow.
- **Assign stable IDs** of the form `<lens>-<n>` (e.g. `defaults-1`,
  `reciprocity-2`).

Present a grouped, ID'd list to the user. Each finding renders on one line, with
its verification tag and the metric it targets:

```
[reciprocity-1] ✓ 🔴 reciprocity · src/Report.tsx:40 — scan result is blurred
        behind "Create an account to see your report"; the user ran a scan and got
        nothing back → likely abandons here — show the real score + top issues,
        gate only the full breakdown behind signup — ↑ signup conversion — medium
```

Then summarize: how many findings at each severity, which lenses were quiet, how
many candidates verification filtered out (list those with one-line reasons), and
whether the review was rendered or code-only. Note which findings are **structural
product decisions** vs. **mechanical edits** (see Phase 4). Keep it skimmable.

## Phase 4 — Decide

Ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop (significant only)** — apply all verified 🔴/🟡 findings,
  re-review, repeat until convergence or the round cap. Skips 🟢 refinements
  (see loop rules).
- **(c) Autonomous loop (everything, including refinements)** — apply *all*
  verified findings including 🟢, re-review, fix again, until a round surfaces
  nothing new (see loop rules).
- **(d) Stop** — report only; change nothing.

Note for the user: some findings are **mechanical** (a clean, in-pattern code
edit — prefill a default, reorder a step, change button copy) and some are
**structural product decisions** (restructure onboarding, ungate a paywall) that
change behavior and may want product judgment. The loop will *attempt* structural
findings too, but if one can't be made as a clean change behind the gate, it
reverts and reports it rather than forcing it (see loop rules).

## Phase 5 — Implement (for paths a, b, and c)

For each accepted finding, in order:

1. **Apply the edit** to the working tree — **reusing the project's existing
   patterns and components** (its progress bar, its default-value mechanism, its
   pricing component, its CTA button). Never invent a new pattern where one
   exists, and rest the change on a **true signal** (real progress, a real
   reference number, a real stake) — a fabricated one won't hold the metric.
2. **Run the gate** — the project's lint and build commands from Phase 0. This is
   a *doesn't-break-the-build* gate; it confirms the change is safe to ship. It
   **does not** prove the metric moved — that needs a real measurement. Carry each
   finding's `hypothesis` (metric + expected direction) into the commit so the
   change is set up to be validated (e.g. by an experiment) afterward.
3. **Hold the gate hard.** If lint or the build goes red, fix it or revert that one
   finding. Never commit red.
4. **Commit on the current branch** — one commit per finding, Conventional Commits
   style (`<type>(<scope>): <subject>`, e.g. `feat(onboarding): …`), scoped to the
   finding's lens, and mention the target metric in the body. One commit per
   finding keeps the history reviewable and lets any single change be reverted —
   which also makes each change cleanly A/B-testable in isolation.

If a finding is a structural product decision that can't be made as a clean
in-pattern change, don't force it into a commit — surface it as a recommendation
with a concrete proposed approach and let the user drive it. If you couldn't find
the lint/build commands in Phase 0, ask the user for them or whether to proceed
without the gate — don't silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:         <lens>-<n>            e.g. defaults-1
severity:   critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
lens:       defaults | progress | reciprocity | endowment | loss-aversion | anchoring
principle:  the named psychology principle the finding traces to
            (e.g. "decision fatigue", "goal-gradient effect", "reciprocity",
             "endowment/IKEA effect", "loss aversion / status-quo bias",
             "anchoring / contrast effect")
location:   path:line, or the screen/step name when it's about flow sequence
problem:    what in the UX works against how the user thinks, and the moment it
            costs on the target metric (drop-off, abandonment)
fix:        concrete change that applies the principle on a true signal, reusing
            existing patterns
hypothesis: the metric this targets and the expected direction, plus how to
            measure it (e.g. "↑ signup completion; watch signup-step drop-off")
effort:     small | medium | large
```

Phase 2 verification then annotates each surviving finding with two more fields
(refuted findings are dropped, not annotated):

```
verdict:    confirmed | uncertain
confidence: high | medium | low
```

Severity guidance: 🔴 for a hard blocker on the target metric (a signup wall
before any value, a blank high-stakes form that drives abandonment); 🟡 for a clear
missed opportunity (starting at 0%, gain-framing where loss lands, a price shown
in isolation, no smart defaults); 🟢 for refinement.

## Autonomous loop rules (paths b and c)

Both loop paths repeat the same cycle — apply findings, re-run the full review
(fan-out → verify → consolidate, Phases 1–3) on the now-updated target, then apply
again — until they converge. Because verification runs every round, the loop only
ever applies findings that survived it. The paths differ only in **which findings
they apply** and **when they stop**.

### Path b — significant only

1. Apply every **verified significant** finding — a 🔴 or 🟡 that Phase 2 returned
   as `confirmed`. 🟢 findings and any left `uncertain` are reported but not
   auto-applied. Each fix follows the Phase 5 apply-and-gate steps. If a confirmed
   finding turns out to be a structural change that can't be made cleanly behind
   the gate, revert it and report it rather than forcing it.
2. Re-run the full review (fan-out → verify → consolidate) on the updated target.
3. Repeat. **Stop** when either a round produces no verified 🔴/🟡 findings
   (convergence) or three apply-then-re-review rounds have completed (cost bound),
   whichever comes first.

### Path c — everything, including refinements

1. Apply **every verified** finding the round produced — 🔴, 🟡, *and* 🟢 — that
   verification marked `confirmed`; `uncertain` ones are reported, and structural
   changes that can't be made cleanly are reverted and reported. Each fix follows
   the Phase 5 apply-and-gate steps.
2. Re-run the full review (fan-out → verify → consolidate) on the updated target.
3. Track findings already addressed across rounds (by location + fix) so you can
   tell genuinely **new** findings from ones that keep resurfacing. Repeat. **Stop**
   when either a round produces **no new findings** at any severity — every finding
   it raises is one already applied, or already attempted-and-reverted as an
   unfixable structural change in an earlier round (full convergence) — or **six**
   apply-then-re-review rounds have completed (safety bound), whichever comes
   first. This retirement clause matters here: because attempting a structural
   finding and reverting it is a first-class outcome (Phase 4), a reverted finding
   is never applied and would otherwise be re-detected every round, so without it
   the loop could never reach "no new findings".
4. If a 🟢 finding is pure taste with no clear improvement, or two rounds in a row
   re-propose the same change you already applied or already reverted as unfixable,
   treat it as addressed and don't churn — convergence, not perfection, is the
   target.

### Common to both paths

- Each round reports: findings applied, the gate result, what verification
  filtered out, and what remains (including structural findings deferred to the
  user). On stop, summarize total commits made and everything left for the user.
- The loop is **stateless across invocations**: hitting the round cap is not the
  end of the road. Because each run re-orients and re-reviews from the current
  state, the user can re-invoke this skill to run another set of rounds — a fresh
  run naturally continues where the last one stopped. Mention this in the stop
  summary.

## When to use this vs. `review-design` vs. the `uxpolish` agent

- **`review-ux-psychology`** (this skill) — judges the **decision architecture** of
  a flow to move a metric: defaults, progress, value-first, ownership, framing,
  anchoring. Reach for it for onboarding/signup/checkout/pricing conversion.
- **`review-design`** — judges how the UI **looks**: hierarchy, spacing,
  typography, color/contrast, dark mode, depth. Reach for it for a visual pass.
- **`uxpolish` agent** — fixes **interaction friction** in a diff: missing
  loading/empty/error states, keyboard handling, labels. Reach for it for
  state/affordance gaps rather than persuasion or visual craft.

They compose: a full UX audit is often `review-ux-psychology` for the flow's
conversion logic plus `review-design` for its visual craft.

## Error handling

- **No decision surface** (target is pure backend/library or purely
  presentational, or empty after resolving): report nothing and stop; suggest
  `review-design` for a visual pass.
- **No target metric given:** ask which metric the flow is optimized for before
  fanning out — findings are ranked by impact on it.
- **Can't render the flow:** fall back to a code-only review and say so; don't
  silently present a code-only review as if it were grounded in the rendered UI.
- **Ambiguous target** (nothing specified): ask which flow to review before
  scanning — don't default to the whole repo.
- **Lint/build command not found:** warn and ask whether to proceed without the
  gate or supply the command. Never silently skip verification.
- **A sub-agent or verifier fails:** note it; for a failed verifier, treat the
  finding as `uncertain` (surface it, don't auto-apply). Continue with the others.
- **A fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it "attempted, reverted — needs manual work," and continue with the rest.
- **A finding is a structural product decision:** the loop attempts it, but if it
  can't be made as a clean in-pattern change, revert and present it as a
  recommendation with a proposed approach rather than forcing it.
