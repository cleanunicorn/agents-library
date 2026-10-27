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

You are the **orchestrator** of a multi-lens visual-design review of a UI,
judged against core UI/UX principles, over a target the user chooses: a view or
component, a path or glob of frontend files, or the current branch diff. Orient
on the project's design system, fan out sub-agents across five design lenses,
consolidate, and help the user act on the findings behind a lint/build gate.

Two properties frame everything below:

- **Every finding traces to a principle.** A design critique that can't name the
  principle it serves is taste, not review — the lenses below are the rubric.
- **You never push or touch the remote.** All work is local: edits on the
  current branch, gated on the project's lint and build.

## Phase 0 — Orient

Gather this context **once** and bundle it into every sub-agent's prompt.

1. **Read the project's guidance.** Look for `AGENTS.md`, `README`, `CLAUDE.md`,
   `CONTRIBUTING`, and any design-system or component-library notes. Capture the
   conventions, commit format, and confidence-indicator rules verbatim.
2. **Learn the design system.** The heart of orientation — lenses judge against
   the project's *own* system, not generic ideals:
   - the **spacing scale** (4px/8px base?) and layout grid;
   - the **type scale**, typefaces, and base body size;
   - the **color palette**, neutrals, and semantic colors, plus the **theme(s)**
     (is there a dark mode? how are surfaces and contrast handled?);
   - the **elevation/shadow tokens**;
   - the **component library** — how buttons, inputs, cards, modals, and icons
     are built and themed.
   Find where these live (tokens file, theme config, component directory) and
   capture them so findings reuse real tokens, not invented ones.
3. **Detect the main branch** as `<main>`: `git symbolic-ref
   refs/remotes/origin/HEAD`, else whichever of `main`/`master` exists — never
   hard-code `main`.
4. **Resolve the target.** From the user's request:
   - a named view/component or a path/glob → just those files;
   - "diff" / "my changes" / `--diff` → the current branch diff
     (`git diff <main>...HEAD`) plus staged and unstaged changes
     (`git diff --cached`, then `git diff`) and untracked files (`git status`);
   - nothing specified → ask which UI to review (a screen, a component, a
     directory, or the diff). Don't scan the whole repo blindly — design review
     needs a focused surface.
   Capture the resolved file list.
5. **Find the commands that matter.** Detect how the project lints, formats, and
   builds the frontend — docs first, then config. You need these for the Phase 5
   gate.

If the resolved target has **no visual surface** (no components, templates,
styles, or rendered output — e.g. it's pure backend or a library), say there's
nothing to design-review and stop.

## Phase 1 — Fan out the review

Dispatch all five lens sub-agents concurrently, batching to the host's limits.
Give each the file list and let it read what its lens needs.

**Model choice:** honor a user-selected model. Otherwise use an explicitly
available cheaper model for bounded read-only review, or inherit the session
model. Retry at the session tier only when required fields or assigned coverage
are missing.

Each sub-agent's prompt is assembled from three parts:

1. **The shared context** from Phase 0: the project guidance summary, the
   **design-system map** (tokens, scales, palette, theme, components), and the
   resolved target file list (plus the diff, for a `--diff` target).
2. **The lens prompt** — read the matching file from `domains/` and include it
   verbatim; it is the sub-agent's entire instruction set for what to look for.
3. **The output contract** — the finding schema below, with the instruction:
   *analysis only; do not modify any files; read the files in the target as you
   need; return findings in this exact schema, or an empty list. Judge against
   the project's own design-system map, and make every `fix` concrete and
   reuse its tokens, scales, and components — never invent a value, color, font,
   or pattern.*

The five lenses and their files:

| Lens | Emoji | File | Looks for |
|------|-------|------|-----------|
| Hierarchy & spacing | 🧭 | `domains/hierarchy-spacing.md` | One primary action; emphasis order; spacing on a scale; proximity, grouping, grid alignment. |
| Typography | 🔤 | `domains/typography.md` | Type scale, body ≥16px, line-height & line length, heading distinction, one or two typefaces. |
| Color & dark mode | 🎨 | `domains/color-darkmode.md` | Restrained palette, WCAG AA contrast, color not the only meaning, dark mode done right (not inverted). |
| Depth, icons & buttons | 🧱 | `domains/depth-icons-buttons.md` | Consistent shadows/elevation (one light source); icon style/weight; button weight maps to priority; touch targets. |
| Interaction, states & motion | ⚡ | `domains/interaction-states.md` | Signifiers (looks interactive); all states incl. focus; motion timing & reduced-motion; overlay structure. |

If a sub-agent fails or returns nothing, note it and continue — never block the
review on one lens.

## Phase 2 — Consolidate

Merge all findings into one list:

- **Deduplicate across lenses.** The same location with the same fix collapses
  into one entry; keep the higher severity (lenses may flag one element for
  different reasons — surface it once).
- **Rank** by severity (🔴 → 🟡 → 🟢), then by lens (hierarchy and color/contrast
  before micro-polish — lead with what most changes how the UI reads).
- **Assign stable IDs** of the form `<lens>-<n>` (e.g. `hierarchy-1`, `color-2`).

## Phase 3 — Present

Render a grouped, ID'd list to the user, one finding per line:

```
[color-1] 🔴 color · src/Banner.tsx:24 — body text #8a8a8a on #f2f2f2 is 2.9:1,
          fails WCAG AA — use the `--text-secondary` token (#595959, 7.0:1) — small
```

Then summarize: findings per severity and which lenses were quiet. Keep it
skimmable.

## Phase 4 — Decide

If the request already chose a path ("report only", "fix everything", "apply the significant ones", "fix these IDs"), take it without asking; the request is the authorization. Otherwise ask the user to choose one:

- **(a) Implement selected** — they name the finding IDs to apply.
- **(b) Autonomous loop, significant only** — see *Autonomous loop rules*.
- **(c) Autonomous loop, everything** — including 🟢 refinements; see
  *Autonomous loop rules*.
- **(d) Stop** — report only; change nothing.

## Phase 5 — Implement (for paths a, b, and c)

For each accepted finding, in order:

1. **Apply the edit** to the working tree — **reusing the project's tokens,
   scale, and components**. Never inline a one-off value where a token exists,
   and never introduce a new color, font, or pattern to satisfy a finding; if no
   suitable token exists, note it and prefer the smallest in-system change.
2. **Fix every instance, not just the one found.** Search the whole
   repository for the same problem — its *shape*, not the literal text (the
   same off-scale value, the same failing color pair, the same mismatched
   icon). Apply the same token-reusing fix wherever it is mechanical and safe,
   in the same commit, and record the search and its count (`N found · N fixed
   · N left`) in the commit body and in the round report. Two limits hold:
   every swept view gets the step 3 checks, so cut the sweep to the views you
   can actually verify;
   and instances outside the reviewed surface are reported with their count and
   edited only on the user's say-so — in the autonomous loop they are reported,
   never auto-applied. A finding fixed on one view while identical ones remain
   is not fixed.
3. **Run the gate** — the project's lint and build commands from Phase 0. Where a
   finding touches contrast or a theme, re-verify the ratio in **every** theme it
   affects (light-mode ratios don't carry to dark).
4. **Hold the gate hard.** If lint or the build goes red, fix it or revert that
   one finding. Mark a revert `attempted, reverted — needs manual work`, then
   continue with the remaining findings. Never commit red.
5. **Commit on the current branch** — one commit per finding, Conventional
   Commits style (`<type>(<scope>): <subject>`, e.g. `fix(ui): …`,
   `style(banner): …`), scoped to the finding's lens, so any single fix can be
   reverted cleanly.

If you couldn't find the lint/build commands in Phase 0, ask the user for them or
whether to proceed without the gate — never silently skip verification.

## Finding schema

Each sub-agent emits findings as records with these fields:

```
id:        <lens>-<n>            e.g. hierarchy-1
severity:  critical | important | nice-to-have   (🔴 | 🟡 | 🟢)
lens:      hierarchy | typography | color | depth | interaction
principle: the named UI/UX principle the finding traces to
location:  path:line
problem:   one-line description of what reads wrong and why
measured:  the value you observed and the threshold it fails (`3.73:1 on S1, AA
           needs 4.5:1`; `18px target, min is 24px`; `spacing 13/17/23px, scale
           is 4px`) — else `not measured`, and say what would measure it
fix:       proposed change, concrete and token-reusing enough to act on
effort:    small | medium | large
```

Measure a colour role on **every surface it can land on**, not only the pair in
front of you — a role that passes on white and fails on navy is the usual way a
contrast bug ships past a test suite that has one.

Severity guidance: 🔴 for a contrast failure that blocks readability or a
hierarchy so broken the user can't find the primary action; 🟡 for off-scale
spacing/type, a clear inconsistency, or a missing state; 🟢 for refinement.

## Autonomous loop rules (paths b and c)

| Path | Apply | Stop when | Cap |
| --- | --- | --- | --- |
| b — significant | 🔴 and 🟡 | no significant findings remain | 3 rounds |
| c — everything | 🔴, 🟡, and 🟢 | no new findings remain | 6 rounds |

For either row: apply each finding through Phase 5, re-run Phases 1–2, and
repeat. Track addressed findings by location + fix; retire pure-taste or
repeated proposals instead of churning. Report each round's fixes, gate, and
remainder, then the total commits and deferred findings. The cap is per
invocation; a later invocation starts from the updated target.
