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

Why these types, and not one agent asked to do it all:

- Planners who cannot see each other produce real alternatives; one asked for
  "options" produces a plan and a strawman.
- The implementer is the worst judge of its own diff, so agents of different
  kinds that saw none of the planning review it.
- Every planner gets the same brief, and so does every reviewer; the
  difference comes from the agent kind.

**Model choice:** managers, planners, reviewers, and the coordinator run at
session tier; the fan-outs inside the sibling skills keep their lesser-tier
default.

## Floors

A floor is a responsibility that needs an eligible owner. It follows from a
rule of `SKILL.md`; it is not a count to aim for.

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

Falling below the **roster** — a member failed, and so did its retry on
another kind — is a recorded degradation, confidence 🟡 at best. Falling below
a **floor** is `blocked`.

## Picking the roster

Read these signals off the work item and the repository. Each one moves a
type up or down; none of them is a number.

| Signal | What it moves, and why |
|--------|------------------------|
| Layers and files the change likely crosses | Further planners and reviewers: more places for a plan to go wrong and for a defect to hide |
| Real design alternatives, or one obvious home | Contested design → further planners, because planners who cannot see each other produce real alternatives. One obvious home → one planner |
| Separable questions | A planner each, with a scoped assignment on top of the shared acceptance criteria |
| Security, stored data, a public contract, an ask-first boundary | Further reviewers and a fresh final reviewer: the cost of a missed finding is high |
| Gate strength | A syntax-only gate proves little, so review has to carry more |
| Agent kinds the host offers | Independence comes from a different kind. A further agent of a kind already on the roster adds cost and little independence; say so rather than adding it |
| The requested terminal state | "Stop after the plan" needs no reviewer; a PR needs the review floors |
| Attended or not | Nobody to answer a late question → lean toward the plan that exposes open decisions early |
| The user's own words | "Quick" and "be thorough" are signals. A roster the user names is a constraint above the floors: take it as given where it meets them and record the reason as `user-specified`. One that would fall below a floor is `blocked` (see Floors), raised as a question record that names the floor |

There is no upper bound and no size-to-count table. The check on a large
roster is its stated cost and its reasons, which the user sees in the team
block.

Agents of the same type differ in kind where the host has kinds to offer;
where it does not, they differ in model and the ledger records that they are
not different kinds. A type with one agent needs no partner for diversity's
sake.

## The roster record

Write it in the ledger in Phase 0, before opening the per-agent rows:

```
roster:    planners: N · coordinator: 1 · reviewers: N · final: fresh | reuse:<reviewer label> | decided after Phase 6
signals:   what you read off the work item — layers, files, risk exposure, gate strength, kinds available
reason:    one line per type, tied to a signal — "1 planner: one obvious home, src/service.py; no contested design"; a type left out says what covers its job
cost:      1 manager + N team agents · N plan-feature + N review-pr + 1 simplify-sweep fan-outs
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
brief in this directory that it is handed verbatim, the skill-bundle line in
`hosting-agents.md`, and a sentence in `README.md` and `AGENTS.md`. Until all
of those exist, the type does not.
