---
name: review-design
description: >-
  Review the visual design of a UI — hierarchy, spacing, typography,
  color/contrast, dark mode, depth, interaction states — judged against the
  project's own design tokens, for a view/component, a path/glob, or the branch
  diff; then optionally apply fixes behind the project's lint/build gate. Use
  when the user wants a design pass, a critique of how a screen looks, or an
  audit of visual hierarchy / spacing / typography / color / dark mode. Do NOT
  use for conversion, persuasion, or metric-moving flow reviews (use
  review-ux-psychology) or a general code-quality review of the diff (use
  review-pr). No `gh` or remote required.
---

# review-design

You are the **orchestrator** of a multi-lens visual-design review. The user
wants a UI judged against core UI/UX design principles — across a target they
choose: a single view or component, a path or glob of frontend files, or the
current branch diff. Your job is to orient on the project's design system, fan
out specialized sub-agents across five design lenses, consolidate what they find,
and help the user act on it behind a lint/build gate.

This is the design-focused counterpart to `review-pr`. Where `review-pr` reviews
a diff across ten quality domains (correctness, architecture, tests, …),
`review-design` reviews the *visual craft* of a UI — hierarchy, spacing,
typography, color, depth, and interaction feel — across a target you pick, not
just the diff. If the user's real question is about conversion, drop-off, or a
product metric (defaults, framing, pricing psychology), that's
`review-ux-psychology`, not this skill.

Two properties frame everything below:

- **Every finding traces to a principle.** A design critique that can't name the
  principle it serves is taste, not review — the lenses below are the rubric.
- **You never push or touch the remote.** All work is local: edits on the current
  branch, gated on the project's lint and build. No `gh`, no remote required.

## Why this shape

"Is the hierarchy clear?", "is spacing on a scale?", "does the color pass
contrast?", and "do states feel right?" are different mental modes — one lens
per sub-agent, all sharing the same design-system context, finds more than one
generalist pass, and you merge the results into one ranked list. The sub-agents
**only analyze**; edits happen later, under your control, behind the lint/build
gate.

## Phase 0 — Orient (do this once, yourself)

Before dispatching anything, build an accurate map of the project's design
system and the review target. You gather this **once** and bundle it into every
sub-agent's prompt, so the five agents don't each re-derive the same context.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and any design-system or component-library notes. Capture the
   conventions, commit format, and confidence-indicator rules verbatim.
2. **Learn the design system.** This is the heart of orientation — the lenses are
   judged against the project's *own* system, not generic ideals:
   - the **spacing scale** (4px/8px base?) and layout grid;
   - the **type scale**, typefaces, and base body size;
   - the **color palette**, neutrals, and semantic colors, plus the **theme(s)**
     (is there a dark mode? how are surfaces and contrast handled?);
   - the **elevation/shadow tokens**;
   - the **component library** — how buttons, inputs, cards, modals, and icons
     are built and themed.
   Find where these live (a tokens file, a Tailwind/theme config, a component
   directory) and capture them so findings reuse real tokens, not invented ones.
3. **Detect the main branch.** Don't hard-code `main` — detect it
   (`git symbolic-ref refs/remotes/origin/HEAD`, or fall back to whichever of
   `main`/`master` exists). Call it `<main>`.
4. **Resolve the target.** From the user's request:
   - a named view/component or a path/glob → just those files;
   - "diff" / "my changes" / `--diff` → the current branch diff
     (`git diff <main>...HEAD`) plus working-tree changes (`git diff`,
     `git status`);
   - nothing specified → ask which UI to review (a screen, a component, a
     directory, or the diff). Don't scan the whole repo blindly — design review
     needs a focused surface.
   Capture the resolved file list.
5. **Find the commands that matter.** Detect how the project lints, formats, and
   builds the frontend — docs first, then config (package.json scripts, etc.).
   You'll need these for the gate in Phase 5. If you can't find them, you'll ask
   the user later rather than silently skipping verification.

If the resolved target has **no visual surface** (no components, templates,
styles, or rendered output — e.g. it's pure backend or a library), say there's
nothing to design-review and stop.

## Phase 1 — Fan out the review

Dispatch all five lens sub-agents **in parallel** — issue all the Agent/Task
calls in a single message so they run concurrently. (This is the
`superpowers:dispatching-parallel-agents` pattern.) If the target is large, give
each sub-agent the file list and let it read what its lens needs.

**Model choice:** unless the user specified a model, run the fan-out
sub-agents on a **lesser model** than your own session — one tier down (e.g.
`haiku` from a `sonnet` session, `sonnet` from an `opus` session), via the
Agent tool's model parameter. Each lens prompt is narrow and single-purpose,
so the cheaper tier is normally enough. If a lens comes back clearly
degraded, re-run that one lens on the session model.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** you gathered in Phase 0: the project guidance summary,
   the **design-system map** (tokens, scales, palette, theme, components), and
   the resolved target file list (plus the diff, for a `--diff` target).
2. **The lens prompt** — read the matching file from `domains/` and include it
   verbatim. That file is the sub-agent's entire instruction set for what to look
   for.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; read the files in the target as you
   need; return findings in this exact schema, or an empty list if you find
   nothing worth raising.*

The five lenses and their files:

| Lens | Emoji | File | Looks for |
|------|-------|------|-----------|
| Hierarchy & spacing | 🧭 | `domains/hierarchy-spacing.md` | One primary action; emphasis order; spacing on a scale; proximity, grouping, grid alignment. |
| Typography | 🔤 | `domains/typography.md` | Type scale, body ≥16px, line-height & line length, heading distinction, one or two typefaces. |
| Color & dark mode | 🎨 | `domains/color-darkmode.md` | Restrained palette, WCAG AA contrast, color not the only meaning, dark mode done right (not inverted). |
| Depth, icons & buttons | 🧱 | `domains/depth-icons-buttons.md` | Consistent shadows/elevation (one light source); icon style/weight; button weight maps to priority; touch targets. |
| Interaction, states & motion | ⚡ | `domains/interaction-states.md` | Signifiers (looks interactive); all states incl. focus; motion timing & reduced-motion; overlay structure. |

If a sub-agent fails or returns nothing, note it and continue with the others —
never block the whole review on one lens.

## Phase 2 — Consolidate

Merge all findings into one list:

- **Deduplicate across lenses.** The same location with the same fix collapses
  into one entry; keep the higher severity. (Several lenses will legitimately
  flag the same element for different reasons — surface that once.)
- **Rank** by severity (🔴 → 🟡 → 🟢), then by lens (hierarchy and color/contrast
  before micro-polish — lead with what most changes how the UI reads).
- **Assign stable IDs** of the form `<lens>-<n>` (e.g. `hierarchy-1`, `color-2`).

## Phase 3 — Present

Render a grouped, ID'd list to the user, one finding per line:

```
[color-1] 🔴 color · src/Banner.tsx:24 — body text #8a8a8a on #f2f2f2 is 2.9:1,
          fails WCAG AA — use the `--text-secondary` token (#595959, 7.0:1) — small
```

Then summarize: how many findings at each severity, and which lenses were quiet.
Keep it skimmable — the user is choosing what to act on, not reading five essays.

## Phase 4 — Decide

Ask the user to choose one path:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop (significant only)** — apply all 🔴/🟡 findings,
  re-review, repeat until convergence or the round cap. Skips 🟢 refinements
  (see loop rules).
- **(c) Autonomous loop (everything, including refinements)** — apply *all*
  findings including 🟢, re-review, fix again, and keep going until a round
  surfaces nothing new. The most thorough path (see loop rules).
- **(d) Stop** — report only; change nothing.

## Phase 5 — Implement (for paths a, b, and c)

For each accepted finding, in order:

1. **Apply the edit** to the working tree — **reusing the project's tokens,
   scale, and components**. Never inline a one-off value where a token exists,
   and never introduce a new color, font, or pattern to satisfy a finding; if no
   suitable token exists, note it and prefer the smallest in-system change.
2. **Run the gate** — the project's lint and build commands from Phase 0. Where a
   finding touches contrast or a theme, re-verify the ratio in **every** theme it
   affects (light-mode ratios don't carry to dark).
3. **Hold the gate hard.** If lint or the build goes red, fix it or revert that
   one finding. Never commit red.
4. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`, e.g. `fix(ui): …`,
   `style(banner): …`), scoped to the finding's lens. One commit per finding
   keeps the history reviewable and lets any single fix be reverted cleanly.

If you couldn't find the lint/build commands in Phase 0, ask the user for them or
whether to proceed without the gate — don't silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:        <lens>-<n>            e.g. hierarchy-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
lens:      hierarchy | typography | color | depth | interaction
principle: the named UI/UX principle the finding traces to
location:  path:line
problem:   one-line description of what reads wrong and why
fix:       proposed change, concrete and token-reusing enough to act on
effort:    small | medium | large
```

Severity guidance: 🔴 for a contrast failure that blocks readability or a
hierarchy so broken the user can't find the primary action; 🟡 for off-scale
spacing/type, a clear inconsistency, or a missing state; 🟢 for refinement.

## Autonomous loop rules (paths b and c)

Both loop paths repeat the same cycle — apply findings, re-run the full review
fan-out (Phases 1–2) on the now-updated target, then apply again — until they
converge. They differ only in **which findings they apply** and **when they
stop**.

### Path b — significant only

1. Apply every **significant** finding — severity 🔴 or 🟡. 🟢 findings are
   reported but not auto-applied (refinements the user should opt into). Each fix
   follows the Phase 5 apply-and-gate steps.
2. Re-run the full review fan-out on the now-updated target.
3. Repeat. **Stop** when either a review round produces no 🔴/🟡 findings
   (convergence) or three apply-then-re-review rounds have completed (cost
   bound), whichever comes first.

### Path c — everything, including refinements

1. Apply **every** finding the round produced — 🔴, 🟡, *and* 🟢. Each fix follows
   the Phase 5 apply-and-gate steps.
2. Re-run the full review fan-out on the now-updated target.
3. Track findings already addressed across rounds (by location + fix) so you can
   tell genuinely **new** findings from ones that keep resurfacing. Repeat.
   **Stop** when either a round produces **no new findings** at any severity (full
   convergence) or **six** apply-then-re-review rounds have completed (a safety
   bound — design refinements can beget more refinements), whichever comes first.
4. If a 🟢 finding is purely cosmetic taste with no clear improvement, or two
   rounds in a row keep re-proposing the same change you already applied, treat it
   as addressed and don't churn on it — convergence, not perfection, is the target.

### Common to both paths

- Each round reports: findings applied, the gate result, and what remains. On
  stop, summarize total commits made and (for path b) any 🟢 findings left for
  the user.
- The loop is **stateless across invocations**: hitting the round cap is not the
  end of the road. Because each run re-orients and re-reviews from the current
  state, the user can re-invoke this skill to run another set of rounds on the
  updated UI — a fresh run naturally continues where the last one stopped. Mention
  this in the stop summary.

## Error handling

- **No visual surface** (target is pure backend/library, or empty after
  resolving): report nothing to design-review and stop.
- **Ambiguous target** (nothing specified): ask which UI to review before
  scanning — don't default to the whole repo.
- **Lint/build command not found:** warn and ask whether to proceed without the
  gate or supply the command. Never silently skip verification.
- **A sub-agent fails or returns nothing:** note it, continue with the others.
- **A fix breaks the gate and can't be repaired quickly:** revert that finding,
  mark it "attempted, reverted — needs manual work," and continue with the rest.
- **A fix would need a token/pattern that doesn't exist:** don't invent a new
  design language to satisfy it — report it as a finding the user must decide on,
  and move on.
- **Two findings' edits conflict:** one-commit-per-finding already serializes
  them; apply sequentially and re-run the gate after each.
