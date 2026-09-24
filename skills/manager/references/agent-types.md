# Agent types and the roster

The manager reads this in Phase 0, when it picks the roster. It says which
types of agent a manager can start, how each one behaves, and how to decide
which types — and how many of each — one work item needs. No count is
prescribed: a title fix and a storage migration do not need the same team.

Team members never read this file. Each gets its own brief, verbatim.

## The types

One card per type, the same labels on every card.

| Label | planner | coordinator | reviewer | final reviewer |
|-------|---------|-------------|----------|----------------|
| Does | Writes one independent plan for the work item | Checks and merges the plans with a SWOT analysis, implements the merged plan, validates the findings, fixes what is confirmed, simplifies | Reviews one frozen commit against the acceptance criteria | Reviews the full branch diff once fixes and simplify have landed |
| Writes | no — its own file in the run directory only | **yes — the single writer** of the worktree | no | no |
| Skill | `plan-feature`, planning only | `simplify-sweep` in Phase 6 | `review-pr`, report only | `review-pr`, report only |
| Brief | `planner-brief.md`, verbatim | `coordinator-brief.md`, verbatim | `reviewer-brief.md`, verbatim | `reviewer-brief.md`, verbatim |
| Sees | The Phase 0 context, the work item, the acceptance criteria | Every plan, labelled, with the authoring kind removed; later every review list | The context, the merged plan's acceptance criteria, the commit SHA | The same as a reviewer |
| Never sees | Any other plan, or a path to one | Which kind or model wrote which plan | Another review; the implementation report; the planning artifacts | Any earlier review, validation record, or implementation report; the planning artifacts |
| Returns | A plan record | The merged plan, the implementation report, the validation records | review-pr's findings plus its `reviewer:` label | The same, labelled `reviewer: final` |
| Runs | With every other planner, all started together | Alone, alive from Phase 2 to hand-back | With every other reviewer, all started together | Alone, after Phase 6 |
| Floor | A plan the coordinator did not write exists before any edit | One agent holds the worktree at a time | Delivered code is reviewed by someone who neither planned nor implemented it | Commits added after the last review are checked by someone who did not write them |

**Model choice:** managers and writing agents inherit the session model unless
the user chooses one. Sibling skills may use an explicitly available cheaper
model for bounded read-only fan-out and retry incomplete results at session
tier.

## Floors

A floor is a responsibility that needs an eligible owner. It follows from a
rule of `SKILL.md`; it is not a count to aim for.

The floors bind a roster of delegated agents. A host with no delegation at
all has no roster to pick: rung 3 of `hosting-agents.md` applies, and the
manager runs every pass itself, in sequence. One holder of the worktree still
holds; the three independence floors — the plan, the review, the final check
— cannot be met. That is the one exception to rule 10 — a recorded
degradation, not `blocked` — and its hand-back names only the floors that
went unmet, reports the lost independence, and claims confidence 🟡 at best.
It is never taken where the host can delegate.

- **A plan the coordinator did not write.** The merge exists so nobody
  defends their own draft, so a planner writes the plan and the coordinator
  judges it. A sole planner that fails, and whose retry on another kind fails
  too, leaves the run `blocked`; the coordinator never writes the plan it
  would then merge.
- **One holder of the worktree** (rule 1). A coordinator that replaces a dead
  one is the continuity exception of `hosting-agents.md`, not a second
  coordinator.
- **Delivered code is reviewed by someone who neither planned nor
  implemented it.** A run the user ends at the plan delivers no code and
  needs no reviewer.
- **Commits added after the last review are checked by someone who did not
  write them.** A fresh final reviewer is the default. A Phase 4 reviewer may
  re-check them instead — it did not write the fixes — and is then recorded
  as `reuse:<label>` and reported as not fresh. `reuse` starts no final
  reviewer: that reviewer runs the final pass and stays a reviewer, so rule
  2's "has done nothing else in this run" describes the fresh one only. Its
  findings from that pass are labelled `final`. When Phases 5 and 6 added no
  commit, the reviewed SHA is still `HEAD` and there is nothing left to check.

What happens when a member fails — below the roster, or below a floor — is
rule 10 of `SKILL.md`.

## Picking the roster

Read these signals off the work item and the repository. Each one moves a
type up or down; none of them is a number.

| Signal | What it moves, and why |
|--------|------------------------|
| Layers and files the change likely crosses | Further planners and reviewers: more places for a plan to go wrong and for a defect to hide |
| Real design alternatives, or one obvious home | Contested design → further planners. One obvious home → one planner |
| Separable questions | A planner each, with a scoped assignment on top of the shared acceptance criteria |
| Security, stored data, a public contract, an ask-first boundary | Further reviewers and a fresh final reviewer: the cost of a missed finding is high |
| Gate strength | A syntax-only gate proves little, so review has to carry more |
| Agent kinds the host offers | Independence comes from a different kind. A further agent of a kind already on the roster adds cost and little independence; say so rather than adding it |
| The requested terminal state | "Stop after the plan" needs no reviewer; a PR needs the review floors |
| Attended or not | Nobody to answer a late question → lean toward the plan that exposes open decisions early |
| The user's own words | "Quick" and "be thorough" are signals. A roster the user names is a constraint above the floors: take it as given where it meets them and record the reason as `user-specified`. One that would fall below a floor is `blocked` (see Floors), raised as a question record that names the floor |

Use 40 agent starts per work item as a planning warning, counting nested
sibling-skill fan-outs and verifier batches. Prefer batching compatible
read-only work when the estimate exceeds it, but never drop a required lens or
verification to meet the number. Finding-driven verification may exceed the
estimate; continue it and record the actual count in the hand-back.

Assign kinds across the whole roster, not only among agents of the same type.
When the host offers at least two kinds that can run their assigned briefs,
use both even if the roster has only one planner and one reviewer. Choose
kinds for the work item and each role's skill. Do not add a planner or reviewer
only to reach another kind. If just one kind can run the required briefs,
record that limit in `signals` and the ledger; different models of that kind
are not different kinds. Agents of the same type also differ in kind when
possible.

## The roster record

Write it in the ledger in Phase 0, before opening the per-agent rows:

```
roster:    planners: N · coordinator: 1 · reviewers: N · final: fresh | reuse:<reviewer label> | decided after Phase 6
signals:   what you read off the work item — layers, files, risk exposure, gate strength, kinds available
reason:    one line per type, tied to a signal — "1 planner: one obvious home, src/service.py; no contested design"; a type left out says what covers its job
cost:      direct agents + estimated nested starts · N plan-feature + N review-pr + 1 simplify-sweep fan-outs
changes:   [{phase, change, reason}] — or none
```

`roster` is what you planned. The ledger rows are what actually started.
`changes` explains every difference between them.

Planners and reviewers are labelled with letters — A, B, C, … — in the order
you start them. The label goes into each agent's prompt and its ledger row,
and it prefixes every id that agent's work produces (`B-D3`, `C-W1`,
`A:correctness-1`).

## Changing the roster mid-run

Allowed, and always logged in `changes` with the phase and the reason. A diff
that turned out larger than planned earns a further reviewer. A finding in a
domain nobody expected earns a fresh final reviewer where the record said
`reuse`. A planner that failed twice shrinks the plan set.

A roster that shrank through failure is never rewritten as if it had been
picked that size: the `roster` line keeps what was planned, and the
degradation is reported.

## Adding a type

A new type — a design reviewer, say — needs a card in the table above, a
brief in this directory that it is handed verbatim, its name in `SKILL.md`'s
list of types and a mention in its description, the skill-bundle line in
`hosting-agents.md`, and a sentence in `README.md` and `AGENTS.md`. Until all
of those exist, the type does not.
