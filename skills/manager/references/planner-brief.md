# Planner brief

You are one planner on this work item; others may be planning it at the same
moment. You cannot see them and must not look for another plan — not in the
repository, not in scratch directories, not in chat history. An agent that
wrote no plan will compare whatever plans exist decision by decision, and the
comparison is only worth something if each plan was reached alone.

Planning is **read-only**. Do not edit, create, or delete any file in the
repository; do not switch branches, fetch, install, or run test suites. If you
were given a run directory, write your plan there and nowhere else; otherwise
return it as text.

## How to work

1. **Use the `plan-feature` skill** for this work item, planning only. If your
   host does not have it, the manager's prompt names where to read it or
   includes the whole skill — its `SKILL.md` and both lens prompts; follow it
   as written.
2. Work from the acceptance criteria you were given. Keep their ids. Add one
   only when the work item plainly needs it, and say why.
3. Cite existing code as `path:line`. Label every new path as `proposed:`.
   When you searched and found nothing, write `unknown: <what you searched>` —
   an honest unknown is more useful to the merge than a confident guess.
4. Prefer the smallest complete change that ships as one PR. Milestones are
   checklist steps inside that PR.
5. Ask nobody. A missing decision goes in your plan as an open decision, with
   its evidence and the exact question; the manager relays what matters. This
   overrides `plan-feature`'s own step of asking the user.

## What to return

Return a **plan record**:

```
planner:      <label>              (the letter the manager gave you — A, B, …)
plan:         the plan-feature output, unchanged
decisions:    [{id: <label>-D<n>,
                topic:    short label, e.g. "where limit is validated"
                choice:   what you propose
                evidence: path:line | "unknown: <what you searched>"
                rejected: the alternatives you considered, and why not}]
```

The `decisions` list is the part the merge depends on. Give every choice that
another competent planner could reasonably have made differently its own
entry: where the change lives, which existing helper it reuses, the data
shape, the test location, the order of steps, what is left out. A plan with
three decisions and a plan with thirty cannot be compared; aim for the choices
that would change the diff.

End with a confidence indicator: 🟢 High | 🟡 Medium | 🔴 Low.
