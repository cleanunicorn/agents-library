---
name: review-ux-psychology
description: >-
  Review a flow's decision architecture — defaults, progress, framing,
  anchoring — with behavioral psychology to move a named metric (signup,
  activation, checkout), and optionally apply fixes. Use to lift conversion
  or trial-to-paid, reduce drop-off, audit a form for decision fatigue, or
  critique onboarding, signup, checkout, or pricing. Not for how the UI
  looks (review-design) or code review (review-pr).
---

# review-ux-psychology

You are the **orchestrator** of a multi-lens UX-psychology review. The user wants
a UI or flow judged not against how it *looks* but against how people actually
think and decide — in the service of moving a **specific product metric**. Your
job is to orient on the product goal and that metric, fan out specialized
sub-agents across six behavioral-design lenses, independently verify what they
report, consolidate the survivors, and help the user act on it behind a
lint/build gate. Missing loading/empty/error states and keyboard handling in a
diff are the `uxpolish` agent's, not this skill's.

Three properties frame everything below:

- **Every finding traces to a named principle.** A UX critique that can't name the
  psychology it serves is opinion, not review — the six lenses below are the
  rubric (decision fatigue, goal gradient, reciprocity, endowment/IKEA, loss
  aversion, anchoring/contrast). Each finding names its principle.
- **Every finding names the metric it moves.** This skill exists to move a
  specific target metric (activation, signup conversion, trial-to-paid, checkout
  completion, feature adoption, retention). Each finding states which metric it is
  meant to move and in which direction, so findings can be ranked by leverage and
  validated afterward. Every fix rests on a *true* signal — real progress the
  user made, a real reference number, a real stake: a fabricated one (fake
  progress, a phantom reference price, invented urgency) does not durably move a
  real metric, because users learn and the effect evaporates.
- **You never push or touch the remote.** All work is local: edits on the current
  branch, gated on the project's lint and build. No `gh`, no remote required.

## Phase 0 — Orient

Gather this context **once** and bundle it into every sub-agent's prompt.

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
5. **Detect the main branch** as `<main>`: `git symbolic-ref
   refs/remotes/origin/HEAD`, else whichever of `main`/`master` exists — never
   hard-code `main`.
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

Dispatch all six independent lens sub-agents concurrently, batching to the
host's limits.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only review, or inherit the session
model. Retry at the session tier only when required fields or assigned coverage
are missing.

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

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole review on one lens.

## Phase 2 — Verify findings (don't trust the finders blindly)

The finders are optimistic: each is primed to see its principle everywhere, so the
raw pile they return contains false positives. Never present a finding — and
never, in the autonomous loop, apply one — on a finder's word alone.

Dispatch at most four verification batches concurrently, grouped by lens and
severity. A fresh, skeptical verifier that produced none of its batch's findings
returns a separate verdict for every finding. Use the Phase 1 model rule.
Each verifier's prompt is:

1. **The shared Phase 0 context** — project guidance, target metric, flow map, and
   the rendered frames.
2. **The findings in its batch** — each location, problem, proposed fix, and the
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

Each verifier returns a list with one record per finding:

```
id:          <finding id>
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

Merge all **surviving** findings (confirmed and uncertain) into one list:

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
product decisions** vs. **mechanical edits** (see Phase 5). Keep it skimmable.

## Phase 4 — Decide

If the original request already chose a path — "report only", "fix everything", "apply the significant ones", "fix these IDs" — take that path without asking; the request is the authorization. Otherwise ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop, significant only** — see *Autonomous loop rules*.
- **(c) Autonomous loop, everything** — including 🟢 refinements; see
  *Autonomous loop rules*.
- **(d) Stop** — report only; change nothing.

## Phase 5 — Implement (for paths a, b, and c)

For each accepted finding, in order:

1. **Apply the edit** to the working tree — **reusing the project's existing
   patterns and components** (its progress bar, its default-value mechanism, its
   pricing component, its CTA button). Never invent a new pattern where one
   exists, and rest the change on a **true signal**.
2. **Fix every instance, not just the one found.** Search the whole
   repository for the same anti-pattern — its *shape*, not the literal text
   (the same blank default in other forms, the same "Submit" CTA on other
   steps). Apply the same fix wherever it is a mechanical, in-pattern edit, in
   the same commit as its finding so each change stays revertible and
   A/B-testable, and record the search and its count (`N found · N fixed · N
   left`) in the commit body and in the round report. Three limits hold: each
   swept instance must rest on a **true signal in its own flow** — a default
   that is right for checkout may be wrong for an admin form, and a destructive
   or payment field is never swept blind; structural instances follow the rule
   below, surfaced and not forced; and instances outside the reviewed flow are
   reported with their count and edited only on the user's say-so — in the
   autonomous loop they are reported, never auto-applied. A finding fixed in
   one flow while identical ones remain is not fixed.
3. **Run the gate** — the project's lint and build commands from Phase 0. This is
   a *doesn't-break-the-build* gate; it confirms the change is safe to ship. It
   **does not** prove the metric moved — that needs a real measurement. Carry each
   finding's `hypothesis` (metric + expected direction) into the commit so the
   change is set up to be validated (e.g. by an experiment) afterward.
4. **Hold the gate hard.** If lint or the build goes red, fix it or revert that one
   finding. Mark a revert `attempted, reverted — needs manual work`, then
   continue with the remaining findings. Never commit red.
5. **Commit on the current branch** — one commit per finding, Conventional Commits
   style (`<type>(<scope>): <subject>`, e.g. `feat(onboarding): …`), scoped to the
   finding's lens, and mention the target metric in the body. One commit per
   finding keeps the history reviewable and lets any single change be reverted —
   which also makes each change cleanly A/B-testable in isolation.

A Phase 3 entry merged across lenses expands here into its per-lens fixes:
apply and commit each as its own finding, scoped to its lens.

Some findings are **mechanical** in-pattern edits (prefill a default, reorder a
step, change button copy); others are **structural product decisions**
(restructure onboarding, ungate a paywall) that may want product judgment.
Attempt structural ones too, but one that can't be made as a clean in-pattern
change behind the gate is not forced into a commit — surface it as a
recommendation with a concrete proposed approach and let the user drive it. If you couldn't find
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

Phase 2 annotates each surviving finding with `verdict` (confirmed |
uncertain) and `confidence` (high | medium | low); refuted findings are dropped.

Severity guidance: 🔴 for a hard blocker on the target metric (a signup wall
before any value, a blank high-stakes form that drives abandonment); 🟡 for a clear
missed opportunity (starting at 0%, gain-framing where loss lands, a price shown
in isolation, no smart defaults); 🟢 for refinement.

## Autonomous loop rules (paths b and c)

| Path | Apply | Stop when | Cap |
| --- | --- | --- | --- |
| b — significant | confirmed 🔴 and 🟡 | no confirmed significant findings remain | 3 rounds |
| c — everything | every confirmed severity | no new surviving findings remain | 6 rounds |

For either row: apply each finding through Phase 5, re-run Phases 1–3, and
repeat. Never auto-apply `uncertain` findings. Revert and retire structural
changes that cannot pass the gate. Track addressed findings by location + fix;
retire repeated or pure-taste proposals instead of churning. Report each
round's fixes, gate, filtered findings, and remainder, then the total commits
and deferred findings. The cap is per invocation; a later invocation starts
from the updated target.
