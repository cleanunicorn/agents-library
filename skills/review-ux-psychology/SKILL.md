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

## Overview

Judge a UI flow by how people actually think and decide, not how it looks, in service of one named product metric. Every finding names the psychology principle behind it and the metric it should move.

## When to use

- A named screen or flow, a path, or the branch diff, with a metric to move (signup conversion, activation, trial-to-paid, checkout completion, adoption, retention).
- If the user has not named the metric, ask, offering likely candidates. If no flow is named, ask which one; do not scan the whole repo.
- Nothing to review if the target has no decision surface (pure backend, a library, a purely presentational screen). Say so and stop. Visual quality is `review-design`; missing loading, empty and error states are the `uxpolish` agent's.

## What good looks like

Read the project's guidance and the flow: what it wants the user to do, where value is delivered versus where the ask happens, and the friction surface (forms, choices, gates, paywalls, progress, pricing, CTA copy). Render the flow and look at screenshots if you can; if you can only read source, say the review is code-only. Investigate the lenses in parallel where the host supports delegation, otherwise locally, and have a fresh, skeptical agent re-check each finding against the real code and flow before you report it. Drop what it refutes, and list dropped findings with a one-line reason so the user can push back.

Lenses:

- **Decision fatigue and defaults:** choice overload, blank forms, no preselected common choice, buttons that do not preview the outcome.
- **Goal gradient:** starting at 0%, empty onboarding, no credit for what is already done, distance emphasized over momentum.
- **Reciprocity:** asking before giving; signup walls before value; results held hostage; email or payment demanded up front.
- **Endowment and IKEA effect:** commitment asked before the user builds or owns anything; nothing to lose by leaving; "Sign up" where "Continue" fits.
- **Loss aversion and framing:** gain-framed CTAs where a real loss exists, no stakes for inaction, abstract benefits over concrete things at risk, a weightless "maybe later".
- **Anchoring and contrast:** prices shown in isolation, no reference anchor, ordering that sets a bad comparison.

Principles:

- Every fix rests on a true signal: real progress, a real reference price, a real stake. Fake progress, phantom prices and invented urgency spike the metric once and then decay. If there is no real stake, say so rather than manufacture one.
- Several lenses may flag one moment; report it once with every principle and fix.
- Rank by expected effect on the target metric, then severity.
- Separate mechanical edits (a default, a step order, button copy) from structural product decisions (restructuring onboarding, ungating a paywall).

## Boundaries

- Read-only unless the user asks for fixes; a request that already says "fix" or "apply" is that authorization. Otherwise offer: apply selected IDs, apply the significant ones, apply everything, or stop.
- Never pushes or touches the remote; all work is local on the current branch.
- Fixes reuse the project's existing components and patterns. Search the repo for the shape of each problem and fix every in-pattern instance in the same commit, reporting N found / N fixed / N left. Each swept instance must rest on a true signal in its own flow; never sweep destructive or payment fields blindly. Instances outside the reviewed flow are reported, not edited, without the user's say-so.
- Find the project's lint and build commands; if you cannot, ask rather than skip the gate. Run the gate before each commit, never commit red (fix or revert that finding and say it needs manual work), one fix per commit, Conventional Commits, with the target metric and expected direction in the body. The gate proves the build is safe, not that the metric moved; say that measuring it needs an experiment.
- Structural changes that cannot be made as a clean in-pattern change behind the gate are recommended with a proposed approach, not forced.
- Do not auto-apply findings the re-check left uncertain.

## Output

A ranked list, one line per finding: location, principle, what the user experiences and where it costs the metric, the fix, and the metric with direction. Then counts by severity, quiet lenses, what verification filtered out, and whether the review was rendered or code-only. If fixes were applied, list commits, gate results, and the swept counts.
