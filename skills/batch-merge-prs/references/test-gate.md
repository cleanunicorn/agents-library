# Testing the merged branch

The batch branch is tested the way the target project says to test a change —
not the way you would. Every command, safety rule, and setup step comes from
the project's own sources.

## 1. Find the commands

Run `bash scripts/test-commands.sh` from the repository root. It prints, in
priority order:

- `SOURCE <path>` — prose to read: the `AGENTS.md`/`CLAUDE.md` project
  section, `CONTRIBUTING`, and CI configs it can't parse line by line.
- `CANDIDATE <source> <command>` — commands lifted from CI workflow `run:`
  lines and build manifests (`package.json` scripts, `Makefile`/`justfile`
  targets, pytest, cargo, go).
- `CAUTION <path>:<line> <text>` — a guide line that ties a suite to live,
  shared, or production resources, credentials, or authorization.
- `NONE` — nothing anywhere.

Read every `SOURCE`. An earlier source overrules a later one: a command the
project's agent guide names wins over a CI line, which wins over a manifest
script. The final list is what the project expects to pass before a change
like this batch merges — usually its lint, type-check, and test commands, the
same set its CI runs on a pull request. Include a documented setup step
(`npm ci`, `uv sync`) only when the project names it as part of testing;
never install anything it doesn't name.

On `NONE`, or when the sources contradict each other, ask the user for the
commands; unattended, report that the branch is untested and why. Never
report a branch as tested on a guess.

## 2. Respect the project's safety rules

A suite the project marks as touching a shared or live resource — a staging
database, a real API, paid services, a deploy — needs authorization. The
request is that authorization only when it names the suite or says to run
everything including live suites. Without it, skip that suite and list it in
the report as `skipped — needs authorization (<path>:<line>)`. Read every
`CAUTION` line before deciding; it is a hint, not a verdict.

## 3. Run each command

Run each command from the repository root with the batch branch checked out:

```
bash <skill>/scripts/run-gate.sh <label> <run-dir>/<label>.log '<command>'
```

`<label>` is short and unique (`lint`, `test`, `test-e2e`); `<run-dir>` is a
scratch directory outside the repository. The last line is `GATE <label>
exit=<status> log=<path>`. In Herdr, run it in the test pane
(`references/herdr.md`) so the user watches it live; otherwise run it in your
own shell. Run commands one after another — suites often share build output.

For each command record: the command, its source, the exit status, and the
passed and failed counts read from the log. When the runner prints no counts,
write `counts not printed`, not a guess.

## 4. Attribute each failure

For each command that exits non-zero, after the reviewer has finished:

```
bash <skill>/scripts/attribute-failure.sh <run-dir> <remote>/<main> '<command>' <n>=<merge-sha>...
```

Pass every `MERGED` ledger entry in merge order. It runs the command at
`<remote>/<main>` (`BASELINE`), then at each merge commit (`AT`), stops at the
first failure, returns to the batch branch, and prints `CULPRIT <n>`,
`CULPRIT pre-existing`, or `CULPRIT none`. Report it with the caveat it
carries: a culprit found with earlier PRs already merged may be an
interaction, so name both when the failing test touches what an earlier PR
changed. `CULPRIT none` means the failure didn't reproduce — re-run once and
report it as flaky or environment-dependent.

When the culprit is clear but the cause is not, you may start one
investigator agent (read-only; through Herdr when available) to read the log
and the PR's diff and explain the failure. It does not fix anything — fixing
a PR is the user's decision.

A `FATAL` from the script means a test run left tracked files changed; report
it and skip attribution for that command rather than cleaning up yourself.
