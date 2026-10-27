# Implementer brief

Read `worker-common.md` first. You are the item's **single writer**: you edit
files and commit in the item's worktree and branch, and nobody else does.
Phase numbers match the manager's.

**Grant.** The worktree, the run directory, the repository and its `.git`,
shell commands, git commits to the item's branch, the gate, and installs. Never
push, create a PR, or mark one ready.

## Phase 3 — Implement

Read `plan.md` at the path you were given.

1. Work in checklist order, smallest feedback loop first; for a bug, the
   failing test before the fix.
2. Gate after each milestone, adding no failure to the baseline; commit in
   the project's format, never red; tick the Progress box.
3. When the plan proves wrong, change it and log the deviation with a reason.
4. Stay local: the coordinator publishes once in Phase 5.

Write the **implementation record** to `<run_dir>/<slug>/implementation.md`,
one row per milestone: `milestone`, `status: done | blocked:<why>`,
`commits`, `gate`, `deviations`.

`summary`: `N of M milestones done`, deviations by name.

## Phase 4 — Fix mode

You get the coordinator's validation record. Fix each `confirmed`,
`in-scope` finding, in severity order — review-pr's own Phase 5 steps:

1. **Apply the edit** to the worktree.
2. **Fix every instance, not just the one found.** Search the whole
   repository for the problem's *shape*, not its literal text. Open each
   match and confirm it before changing it. Apply the same fix wherever it is
   mechanical and safe, in the same commit, and record `N found · N fixed ·
   N left` with the exact query. Instances outside the branch diff are
   reported with their count, not auto-applied; one that needs a judgement
   call is listed, not forced.
3. **Close the finding's `gap`** in the same commit — widen the test or check
   to the shape that slipped through, or say why nothing local can.
4. **Run the gate** and hold it: fix it, or revert that finding and mark it
   `reverted`.
5. **One commit per finding**, in the project's format.

Update the validation record's `sweep` and `status` per finding. A fix the
manager sends back is corrected once, the same way. A failing CI check comes
the same way. `summary`: one line per finding — `id · status · commit` — and
`fixed: N · reverted: N`.
