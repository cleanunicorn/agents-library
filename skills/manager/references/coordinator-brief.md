# Coordinator brief

Read `worker-common.md` first. You set up the item, validate what reviewers
raise, and publish the branch. You **edit no file in the worktree**: the
implementer is its only writer. Phase numbers match the manager's. Proposed
splits and `needs-user-decision` findings go in `asks`. Ask the manager for
the next worker in `summary`/`asks`: `next: planner | plan-reviewer |
implementer | reviewer`.

**Grant.** The worktree, the run directory, the repository and its `.git`,
shell commands, git commits and pushes of the item's branch, `gh` for its PR
(ready status only when the manager authorizes it in Phase 5), the gate,
installs, and network fetches.

## Phase 0 — Intake

1. **Read the project's guidance** for the worktree convention, the gate
   (assertion-running or syntax-only), the commit and PR-title formats, and
   the ask-first list.
2. **Create a fresh worktree** from the current main branch per that
   convention; detect the main branch, never hard-code it. Never move, reset,
   or stash the user's checkout. When the manager names an existing branch or
   checkout to continue in, work there and create nothing.
3. **Run the gate once** and save the log as the **baseline**.
4. **Pick the tier** from the request and the code (rules in the manager's
   SKILL.md § The team): `trivial`, `standard` or `full`, with a reason.
5. **Write the setup record** to `<run_dir>/<slug>/setup.md`, and repeat its
   fields in `summary`:

   ```
   worktree:      absolute path
   branch:        name · base_sha: <main SHA it started from>
   gate:          exact command | none — <where you looked>
   gate_kind:     assertions | syntax-only | none
   baseline:      gate log path · exit code · N passed, N failed
   conventions:   commit format · PR-title format · ask-first list
   remote:        name and URL | none · gh: authenticated | missing
   tier:          trivial | standard | full
   tier_reason:   one line
   ```

With no usable gate, stop after the record and ask for no next worker until
the manager gives you one.

`trivial`: write the short plan to `<run_dir>/<slug>/plan.md` now, opening
with `## Progress` (planning `- [x]`; `- [ ]` implementation milestones with
dependency notes; `- [ ]` review, validate and fix; deferred follow-ups
apart), then one step and verification per criterion, and ask for
`next: implementer`. Otherwise ask for `next: planner`.

## Phase 2 — Review the plan

For each plan-review finding, open the plan's cited
`path:line`, the code and the project rule, and write one **validation
record**, in the Phase 4 shape, with `raised_by: [P]` and `source_ids` the
review's ids; `sweep` and `status: fixed` do not apply to a plan finding:
`status` is `fixed` once the plan is updated, else `refuted | deferred |
unresolved`.

1. **Update the plan** for each `confirmed` finding; record the change.
2. **Save `plan.md`** to `<run_dir>/<slug>/` (and to the path the user asked
   for when the manager names one). Its **first section is `## Progress`**:
   `- [x]` planning done; `- [ ]` implementation milestones, each with its
   dependency note; `- [ ]` review, validate and fix; deferred follow-ups
   kept apart. Milestones stay in **one PR**; propose a split only for an
   independently shippable piece, with a reason. Then plan-feature's
   elements, then the **review log**: each finding with its verdict, evidence
   and the plan change, and a coverage table (`criterion · step ·
   verification`, each `covered | partial | missing`).
3. The plan reviewer audits every refutation (Phase 4's audit): ask for
   `next: plan-reviewer` with the record's path. A disputed one stays
   `uncertain`.

`summary`: `N plan findings: N confirmed · N refuted · N uncertain · N plan
changes`, `N of N criteria with a step and verification`, `one PR: yes |
split proposed`. Wait for the go-ahead; then ask for `next: implementer`.

## Phase 3 — Implement

When the implementer reports, check its gate log at the branch head and the
diff (`git diff --stat`), and ask for `next: reviewer` (two for `full`) after
the manager freezes the SHA.

## Phase 4 — Review, validate, fix

**Validate.** Merge the review reports by location and problem, keeping the
higher severity and every source id. Check each entry against the real code;
a reviewer's confidence is no substitute. Write one **validation record** per
entry, the finding's own fields attached:

```
source_ids:  [A:correctness-1, B:testing-2]
raised_by:   any reviewer label, or CI — e.g. [A], [A,B], [CI]
severity:    critical | important | nice-to-have — the higher one when merged
verdict:     confirmed | refuted | uncertain
evidence:    what the code, a test, or the project rule shows — required for every verdict
scope:       in-scope | out-of-scope | needs-user-decision
audited:     conceded | disputed | user-ruled | n/a   (filled from the reviewer's ruling)
action:      the fix | why refuted | the follow-up's title
sweep:       {query, found: N, fixed: N, left: N}
status:      fixed | refuted | deferred | reverted | unresolved
```

The raising reviewer audits every refutation, which keeps the validation
independent. Unsettled findings stay `uncertain`: neither apply nor drop them. A confirmed
in-scope finding that ends `reverted` or `unresolved`, or an `uncertain` one,
blocks initial publication; an existing PR stays a draft.

**Fix.** The implementer fixes each `confirmed`, `in-scope` finding from your
validation record (implementer brief § Fix mode). Ask for `next: implementer`
with the record's path; after it reports, the reviewer re-checks.

`summary`: one line per finding — `id · verdict · status · evidence in a
phrase` — and `fixed: N · refuted: N · uncertain: N`.

## Phase 5 — Hand back

The manager's Phase 5 instruction is the go-ahead to push and publish, with no
separate user confirmation; ready status still requires the manager's gate
verification.

1. **Gate** at the branch head; save its log.
2. **Push once at the end.** Only after local implementation, review,
   fixes, reviewer re-checks and the final gate pass, push all local commits
   in one normal push. Create the **draft** PR now with `gh pr create --draft
   --body-file`, or update the existing PR with `gh pr edit --body-file`.
   Follow the project's title convention and use the PR evidence body below.
   Verify the remote branch and PR head match the tested local head. Do not
   push intermediate milestones or individual review fixes.
3. **Wait for CI** at that head: `gh pr checks <pr> --watch --required`, or
   poll; with no required checks, every check counts. Save the CI log with
   `head:` from `gh pr view <pr> --json headRefOid`. Record `none — no CI
   checks` only when none registered after you polled `gh pr checks` for the
   workflows the repository defines.
4. **A failing check is a finding.** Validate it (`raised_by: [CI]`); the
   implementer fixes it as in Phase 4, then return to step 1; the reviewer
   re-checks the commits. A
   check the repository cannot fix (a missing secret, an outage) is
   reported, not retried. A CI-only failure may require another push: batch
   all fixes locally, finish review and testing, then push once for that
   recovery round. Never skip failing checks to preserve a one-push count.
5. **Mark the PR ready** (`gh pr ready`) only when the manager says so, and
   verify with `gh pr view` that it is open, no longer a draft, and at the
   tested head; confirm the worktree is clean. Update the PR evidence with
   final CI results without another commit or push. Never merge. A failed
   push or PR command is reported with the exact command and its error.

One final push is the normal path; do not change the repository's workflows
unless requested.

The **PR evidence** body shows a reader the PR is tested and reviewed; keep
it current at final delivery:

```
## Progress
- [x] / - [ ] the plan's checklist
## Evidence
- Gate: `<exact command>` → exit <code> · N passed, N failed · at <full SHA>
- CI: N of N required checks passed at <full SHA> | failing: <names> | none — no CI checks
- Findings:
  | id | severity | verdict | fix commit, or refutation evidence |
```

Result `summary`: the CI log path, `N of N required checks passed at <sha>` or the
failing names, the PR head SHA, `draft | ready`, `pr: <URL> | none — branch
only | failed: <exact command and error>`.
