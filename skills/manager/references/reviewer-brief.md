# Reviewer brief

Read `worker-common.md` first. Review independently: you did not plan or
implement this change. Never seek another review, the plan review or the
implementation report before filing your own; judge the code, or for a plan
review the plan against the code.

**Grant.** Read access to the worktree and repository, the gate command, and
write access only to the run directory. You **report only**: do not edit,
create, or delete any file outside the run directory; do not commit, push, or
open, close, or comment on a pull request.

## Code review

1. **Check the target first.** `review-pr` reviews `HEAD` and the working
   tree, so compare `git rev-parse HEAD` with the commit you were given. If
   they differ or the tree is dirty, stop and tell the manager you need a
   detached read-only checkout of that commit; check nothing out yourself.
2. **Use the `review-pr` skill** on the branch diff against the main branch,
   on its report-only path (d), verification pass included. If your host
   lacks it, the manager's prompt names where to read it.
3. **Check the diff against each acceptance criterion.** A criterion with no
   code, or no test that would fail without the code, is a finding in the
   testing or correctness domain.
4. Check the change against the project's own rules — commit format, one
   feature one PR, expected documentation and wiring.

Write review-pr's findings **in its own schema, unchanged** — `measured`,
`gap`, `verdict` and `confidence` included — plus `reviewer: <label>` on each,
then its summary and any domain or verifier that failed, to the record path
you were given. An empty list is valid; say which domains produced it.

## Reviewing a plan

When the manager asks for a plan review, you are the **plan reviewer**. Use
none of `review-pr`.

1. **Read `plan.md`'s source plan record** and the numbered acceptance
   criteria you were given.
2. **Check it against the real code.** Open each load-bearing `path:line`;
   a decision resting on a wrong citation is a finding.
3. **Check** that every criterion has a step and a test or verification that
   would fail without the change; that the change is one PR, milestones as
   checklist steps; that wiring and docs the project expects are in the
   plan; and that nothing crosses an ask-first boundary or a public contract
   unflagged.

Write findings to the record path you were given, an empty list valid:

```
id:        P-<n>
severity:  critical | important | nice-to-have
location:  plan section or decision id, and path:line
problem:   one line
evidence:  what the code or a project rule shows
fix:       the plan change
```

Later, you get the coordinator's validation record for the plan. Rule on
each of your refuted findings as in § Later, `concede` or `dispute` with
evidence. There is no gate and no re-check round: `head: n/a`, `gate: n/a`.

## Later: rule on refutations, re-check the fixes

Continue as the same reviewer:

1. **Refutations.** You get the path of the coordinator's validation record.
   For each of your findings it refuted, open the evidence it cites and the
   code, and answer `concede` or `dispute` with your own evidence. Concede
   when the evidence holds; do not drop a finding because the coordinator
   or the implementer disagrees.
2. **Re-check.** You get the commits since the SHA you reviewed. For each of
   your findings marked fixed, check that they fix it — every instance the
   sweep claims, the gap it says it closed — and change nothing else. Then
   run the gate at the new head, logging it as `gate-reviewer-<label>-<short-sha>.log`.
   Send any output or cache the gate lets you place to the run directory; a
   gate that must write into the repository is reported to the manager, not
   run. Write a **re-check record** to the path you were given:

```
reviewer:    <label>
head:        full SHA you checked
gate:        log path → exit code · N passed, N failed — or not run — <reason> → <coordinator's log>
findings:    [{id, status: fixed | not-fixed | partial, evidence: path:line or the log}]
new:         problems the fix commits introduced — same schema as a finding — or none
```

The re-check judges the fix commits against your findings, not the whole
branch again. A fix for a failing CI check comes the same way; re-check it
against that check's record from the head you last checked. Mark nothing
`fixed` you could not verify: the PR stays a draft while any finding is
`not-fixed` or `partial`.

## Result block

`result: reviewer-<label>`, `head:` the full SHA you reviewed or re-checked,
`gate:` the log path or `n/a — not run: <reason>`, and `summary`:

```
N findings: N critical · N important · N nice-to-have, by id
| N conceded · N disputed, by id | N fixed · N not-fixed · N partial · N new, by id
```

`asks`: a target mismatch or a gate you may not run | none.
