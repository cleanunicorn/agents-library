# Project test gate

## Discover

From the repository root, run `bash <skill>/scripts/test-commands.sh`:

- `SOURCE <path>`: guidance or CI prose to read.
- `CANDIDATE <source> <command>`: commands from CI `run:` lines or manifests
  (package.json, Makefile/justfile, pytest, cargo, go).
- `CAUTION <path>:<line> <text>`: possible live/shared resources, credentials,
  or authorization requirements; a hint to inspect, not a verdict.
- `NONE`: no sources found.

Read every `SOURCE` and `CAUTION`. Resolve commands in priority order:
AGENTS.md/CLAUDE.md project section → CONTRIBUTING → CI → manifests. Run
what the project requires before a change like this batch merges, including
lint and type checks. Install only documented testing setup (`npm ci`,
`uv sync`), never an inferred dependency.

No commands or contradictory sources → ask; unattended, report `untested`
and why. Do not guess a gate.

## Authorize and run

Live/shared suites (staging databases, real APIs, paid services, deploys) need
authorization because they affect external resources. A request naming the
suite or explicitly including live suites authorizes it; otherwise record
`skipped — needs authorization (<path>:<line>)`.

With the batch tip checked out, run each authorized command sequentially
from the repository root; suites may share build output:

```
bash <skill>/scripts/run-gate.sh <label> <run-dir>/<label>.log '<command>'
```

Use unique labels and a scratch directory outside the repository. The ledger
is `GATE <label> exit=<status> log=<path>`. Use the Herdr test pane when
available. Record command, source, exit status, and counts from the log;
write `counts not printed` when absent.

## Attribute failures

After the reviewer finishes, for each failed command pass **every** `MERGED`
entry in merge order:

```
bash <skill>/scripts/attribute-failure.sh <run-dir> <remote>/<main> '<command>' <n>=<merge-sha>...
```

The script tests `BASELINE`, then each `AT` merge commit until failure,
returns to the batch branch, and prints `CULPRIT <n>`, `CULPRIT pre-existing`,
or `CULPRIT none`. An attributed failure may be an interaction with earlier
PRs; name both when the failing test touches an earlier change. For `none`,
re-run once and report a flaky or environment-dependent failure.

If the culprit is clear but the cause isn't, start at most one read-only
investigator per culprit to inspect the log and diff. It uses the same agent
transport and never fixes code: the user decides what to change.

A `FATAL` indicating tracked files changed stops attribution for that
command; report it rather than cleaning up the user's files.
