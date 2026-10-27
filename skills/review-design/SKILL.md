---
name: review-design
description: >-
  Review a UI's visual design — hierarchy, spacing, typography, color and
  contrast, dark mode, depth, interaction states — against the project's own
  tokens, for a component, path, or the branch diff, and optionally apply
  fixes. Use for a design pass, an audit, or a critique of how a screen
  looks. Not for conversion flows (review-ux-psychology) or code quality
  (review-pr).
---

# review-design

## Overview

Judge a UI's visual design against core design principles and the project's own design system. Every finding names the principle behind it, not taste.

## When to use

- A view, component, path or glob, or the branch diff. If none is named, ask; do not scan the whole repo.
- Nothing to review if the target has no visual surface (pure backend, a library). Say so and stop.
- Conversion and decision flows are `review-ux-psychology`; code quality is `review-pr`.

## What good looks like

Learn the project's system first (guidance files, tokens file or theme config, component library): spacing scale and grid, type scale and typefaces, palette and semantic colors, themes, elevation tokens. Judge against those, not generic ideals. Investigate the lenses in parallel where the host supports delegation, otherwise locally.

Lenses:

- **Hierarchy and spacing:** one primary action, clear emphasis order, spacing on the scale, proximity and grouping, grid alignment.
- **Typography:** a type scale, body at least 16px, sane line-height and line length, distinct headings, one or two typefaces.
- **Color and dark mode:** a restrained palette with reserved semantics and the accent kept for the primary action; WCAG AA (4.5:1 body text, 3:1 large text and UI components); color never the only carrier of meaning; dark mode designed, not inverted (no pure black or white, desaturated hues, raised surfaces lighter rather than shadowed).
- **Depth, icons and buttons:** consistent shadows and elevation from one light source, consistent icon style and weight, button weight matching priority, adequate touch targets.
- **Interaction, states and motion:** things that look interactive are, every state exists including focus, motion timing and reduced-motion, sound overlay structure.

Principles:

- Measure rather than assert: `3.73:1 on S1, AA needs 4.5:1`; `spacing 13/17/23px, scale is 4px`. If you could not measure, say what would.
- Measure a color role on every surface it can land on, and in every theme; a pair that passes on white can fail on navy or in dark mode.
- Fixes are concrete and reuse existing tokens and components; never invent a color, font or pattern. If no suitable token exists, note it and prefer the smallest in-system change.
- Several lenses may flag one element; report it once. Rank by severity (contrast failures and a lost primary action first), then by what most changes how the UI reads.

## Boundaries

- Read-only unless the user asks for fixes; a request that already says "fix" or "apply" is that authorization. Otherwise offer: apply selected IDs, apply the significant ones, apply everything, or stop.
- Never pushes or touches the remote; all work is local on the current branch.
- Find the project's lint and build commands; if you cannot, ask rather than skip the gate. Run the gate before each commit, never commit red (fix or revert that finding and say it needs manual work), one fix per commit, Conventional Commits.
- Search the repo for the shape of each problem (the same off-scale value, failing color pair, mismatched icon) and apply the same fix to every mechanical, safe instance in the same commit, reporting N found / N fixed / N left. Cut the sweep to views you can verify; re-check contrast in every affected theme. Instances outside the reviewed surface are reported, not edited, without the user's say-so.

## Output

A ranked list, one line per finding: location, principle, what reads wrong with the measured value, and the token-reusing fix. Then counts by severity and which lenses were quiet. If fixes were applied, list commits, gate results, and swept counts.
