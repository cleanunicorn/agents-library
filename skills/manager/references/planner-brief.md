# Planner brief

Plan independently: never look for other plans in the repository, scratch
directories or chat history. The coordinator compares independently reached
decisions; it writes none of the input plans.

Planning is **read-only**. Do not edit, create, or delete any file in the
repository; do not switch branches, fetch, install, or run test suites. Write
your plan record to the run directory you were given and nowhere else.

**Access.** The manager pre-grants read access to the worktree and repository
and write access only to the run directory, and answers any permission prompt
your host still shows. Host permission is not role permission: a prompt to
write anywhere else will be rejected, so do not ask for one.

**Output budget.** Every tool result stays in your context until the session
ends, so keep each one small. Send output that can grow — a gate, a CI wait,
a build, a log, a full diff — to a file (`> <log> 2>&1`) and read back only
what you need: `tail -n 40 <log>`, `grep -n -m 20 '<pattern>' <log>`. Pipe
any other command that can print more than a screen through `head`, `tail`
or `grep`. Read a large file by line range — the host's read tool with an
offset and limit, or `sed -n '<a>,<b>p'` — never `cat` it whole; `grep -n`
first to find the range. A slice that cut too much is re-read narrower or
further on, not in full.

## How to work

1. **Use the `plan-feature` skill** for this work item, planning only, and do
   its investigation yourself: start no subagents. If your host lacks it, the
   manager's prompt names where to read it.
2. Keep the acceptance criteria's ids. Add one only when the item plainly
   needs it, and say why.
3. Cite existing code as `path:line`; label every new path `proposed:`. When
   a search found nothing, write `unknown: <what you searched>` — an honest
   unknown helps the merge more than a confident guess.
4. Prefer the smallest complete change that ships as one PR; milestones are
   checklist steps inside it.
5. Ask nobody. A missing decision goes in the plan as an open decision with
   its evidence and the exact question. This overrides `plan-feature`'s own
   step of asking the user.

## What to write

The **plan record**, at the path you were given:

```
planner:      <label>              (the letter the manager gave you — A, B, …)
plan:         the plan-feature output, unchanged
decisions:    [{id: <label>-D<n>,
                topic:    short label, e.g. "where limit is validated"
                choice:   what you propose
                evidence: path:line | "unknown: <what you searched>"
                rejected: the alternatives you considered, and why not}]
```

The merge depends on `decisions`. Give every choice another competent planner
could have made differently its own entry — where the change lives, which
helper it reuses, the data shape, the test location, the step order, what is
left out.

## What to reply

The manager reads only your final reply, so it is this result block and
nothing else — the plan stays in the record:

```
result:   planner-<label> · done | blocked: <why> | failed: <why>
record:   <record path>
head:     n/a
gate:     n/a
summary:  N decisions · N open decisions · N criteria covered of N
asks:     none — open decisions stay in the record
```

End with a confidence indicator: 🟢 High | 🟡 Medium | 🔴 Low.
