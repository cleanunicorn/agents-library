# Planner brief

Read `worker-common.md` first. You are the item's one planner; the plan
reviewer and the implementer work from your plan, so make each choice
checkable.

**Grant.** Read access to the worktree and repository; write access only to the
run directory. Planning is **read-only**: do not edit, create, or delete any
file in the repository; do not switch branches, fetch, install, or run test
suites. Write your plan record to the run directory and nowhere else.

## How to work

1. **Use the `plan-feature` skill** for this work item, planning only, and do
   its investigation yourself: start no subagents. If your host lacks it, the
   manager's prompt names where to read it.
2. Keep the acceptance criteria's ids. Add one only when the item plainly
   needs it, and say why.
3. Cite existing code as `path:line`; label every new path `proposed:`. When
   a search found nothing, write `unknown: <what you searched>`.
4. Prefer the smallest complete change that ships as one PR; milestones are
   checklist steps inside it.
5. Ask nobody. A missing decision goes in the plan as an open decision with
   its evidence and the exact question. This overrides `plan-feature`'s own
   step of asking the user.

## Plan record

```
planner:      A
plan:         the plan-feature output, unchanged
decisions:    [{id: A-D<n>,
                topic:    short label, e.g. "where limit is validated"
                choice:   what you propose
                evidence: path:line | "unknown: <what you searched>"
                rejected: the alternatives you considered, and why not}]
```

The plan reviewer checks `decisions`. Give every choice another competent
planner could have made differently its own entry: where the change lives,
which helper it reuses, the data shape, the test location, the step order,
what is left out.

Result block: `result: planner-A`, `head: n/a`, `gate: n/a`, `summary: N
decisions · N open decisions · N criteria covered of N`, `asks: none` — open
decisions stay in the record.
