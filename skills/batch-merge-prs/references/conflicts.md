# Resolving merge conflicts

`merge-prs.sh` exits `3` when a PR conflicts with main or with a PR merged
earlier in the batch. The merge is left in progress on the batch branch, and
the ledger names what to resolve:

```
CONFLICT <n> <pr-head-sha> <path>     one line per conflicted path
PENDING <n>...                        the PRs still queued, in order
```

You resolve it; the script commits, aborts, and resumes. Work only in this
checkout, on the batch branch the run created: never on main, a PR branch,
or the remote. Never `git commit`, `git merge --abort`, or `git reset`
yourself — the script's checks are what keep the ledger true.
Inside Herdr this stays the invoking session's work: workers only read.

## Resolve

For each conflicted path:

1. **Read all three versions**: `git show :1:<path>` (common base),
   `:2:<path>` (the batch branch so far), `:3:<path>` (the PR). A missing
   stage means that side deleted the file.
2. **Learn each side's intent**: `gh pr view <n>` for the PR's title and
   body, `git log --oneline <base>..<head> -- <path>` for both sides, and the
   code and tests around the hunk.
3. **Combine them** so both intents hold: keep both edits when they touch
   different concerns; merge them into one when they change the same thing
   compatibly. Never pick a side wholesale (`-X ours/theirs`,
   `checkout --ours/--theirs`) unless one side's change is genuinely already
   contained in the other — say so in the record.
4. **Stage only the reviewed result** with `git add <path>` (or `git rm`
   for a deletion you mean), then read the whole staged diff:
   `git diff --cached` against both parents. No conflict markers, no
   unstaged edits, nothing unrelated.

A resolution that stages cleanly is not yet proven correct: the Phase 2 test
gate and the Phase 3 review still run over every merge.

## Record

Write one record per PR to `<run-dir>/resolution-<n>.md`, outside the
checkout. Name **every** conflicted path exactly as the `CONFLICT` lines
print it — `--continue` refuses a record that omits one — and say for each
what the branch side did, what the PR did, and what you kept.

```
bash <skill>/scripts/merge-prs.sh --continue <remote> <target> <n> <run-dir>/resolution-<n>.md <pending>...
```

It prints `MERGED <n> <sha>` and `RESOLVED <n> <sha> <record>`, then merges
the `PENDING` PRs; another conflict pauses again the same way.

## Skip instead of guessing

Skip the PR when you cannot resolve it with confidence:

- the two intents contradict and nothing in the PRs, issues, or project
  guidance says which one wins;
- the file is binary, generated, or a lockfile you cannot regenerate with
  the project's own documented command;
- a structural change (rename, move, delete) collides with edits and no
  combination keeps both working.

```
bash <skill>/scripts/merge-prs.sh --skip <remote> <target> <n> '<reason>' <pending>...
```

The reason is concrete — which paths, and what contradicts — and lands in the
ledger as `SKIPPED <n> unresolved <reason>`. A dependent PR that then fails
the test gate is attributed as usual.

## Errors

`FATAL` stops the run with the merge state intact: relay it, never reset or
clean to force progress. `PR #<n> moved since the pause` means its head
changed upstream: `--skip` it, finish the queue, and tell the user to rerun
it.
