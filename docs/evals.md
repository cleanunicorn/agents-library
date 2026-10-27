# Skill evals

Every skill in `skills/` carries an eval suite, and a single runner at the repo
root executes them. The evals exist for two reasons:

- **Regression protection** — the skills encode team workflows (guardrails,
  output contracts, gates). A model update or a skill edit that degrades them
  should be caught by re-running the suite.
- **Retirement detection** — the runner can run a skill's cases *without* that
  skill loaded. If the bare model passes anyway, the skill is a retirement
  candidate; its evals stay in the repo as regression tests either way.

**Evals are manual-only.** The runner is never wired to CI, git hooks, or push
automation, and must not be — a full sweep launches hundreds of real agent
runs. Run it by hand, scoped, when you change a skill or update the model.

## Layout

```
run_evals.py                      # the shared runner (stdlib Python 3)
scripts/test-run-evals.py         # offline tests of its transcript parsing
skills/<name>/evals/cases.json    # at least 5 positive and 5 negative cases per skill
eval-results/                     # JSON results per run (gitignored)
```

## How a trial works

For each trial the runner:

1. creates a fresh temp workspace **outside the repo** (no access to prior
   context or this repo's files);
2. materializes the case's fixture — files first, then setup shell commands
   (git repos, branches, fake remotes); anything under `bin/` is made
   executable and prepended to `PATH`, which is how the fake `gh` shims work,
   so **no network or real GitHub access is needed**;
3. copies every repo skill into the workspace's `.claude/skills/` — minus each
   skill's `evals/` directory, so the agent can never read the expected
   assertions;
4. runs `claude -p "<prompt>"` in the workspace with
   `--dangerously-skip-permissions` and (when the CLI supports it)
   `--setting-sources project`, so user-level skills and settings don't leak
   into the eval;
5. grades the **outcome**: every assertion must pass. Whether/which skill
   loaded is parsed from the transcript and reported separately as
   `trigger-ok` telemetry — a case never passes or fails on triggering alone.

A case passes a trial iff all its assertions pass. Default is 3 trials per
case; per-case and per-skill pass rates are printed and written to
`eval-results/<timestamp>.json` (which also records per-trial failures and the
skills each trial invoked, plus a delegation trace per trial with `--trace` —
see [Delegation traces](#delegation-traces)).

## Running

Prerequisites: `python3`, `git`, and an authenticated `claude` CLI. The real
`gh` CLI is *not* needed — fixtures ship their own shim.

```sh
python3 run_evals.py --dry-run                # validate case files, run nothing
python3 run_evals.py --skill review-pr        # one skill, 3 trials/case
python3 run_evals.py --skill review-pr --case rp-h1
python3 run_evals.py --trials 1               # cheap first-signal pass, all skills
python3 run_evals.py --trials 1 --model haiku # cheaper still
python3 run_evals.py                          # the full sweep (see cost note)
```

Ablation / retirement:

```sh
# happy-path cases WITH vs WITHOUT the skill loaded; prints
# "RETIREMENT CANDIDATE" when the without-arm matches the with-arm
python3 run_evals.py --ablation --skill describe-codebase

# a single arm, manually
python3 run_evals.py --skill review-pr --without-skill review-pr
```

Debugging:

```sh
# materialize fixtures without invoking the agent; prints workspace paths
python3 run_evals.py --build-only --keep-workspaces --case bm-h1 --skill batch-merge-prs

# keep workspaces after a real run to inspect what the agent did
python3 run_evals.py --skill triage-issues --case ti-h5 --trials 1 --keep-workspaces

# also record which sub-agents each trial launched (telemetry, never graded)
python3 run_evals.py --skill manager --case mg-h3 --trials 1 --trace
```

The transcript parser and the trace are tested offline, on synthetic
transcripts, by `scripts/test-run-evals.py` in the local gate — no agent runs.

**Cost note:** for a normal sweep, multiply the case counts printed by
`--dry-run` by `--trials` (default 3) to get the number of agent runs. Ablation
runs only positive cases, twice per trial (with and without the skill). Several
cases orchestrate multiple subagents, so a full sweep can take hours and spend
meaningful tokens. Ramp up: `--dry-run` → `--trials 1` → full runs per skill →
ablation.

## Reading the output

```
== review-pr ==
  rp-h1      pass 3/3  trigger-ok 3/3  skills-used: review-pr
  rp-n2      pass 2/3  trigger-ok 3/3  skills-used: simplify-sweep  <-- FLAKY
             ! output_regex: (?i)(simpl|dead code|duplic|nothing)
  -- review-pr: 29/30 trials passed (96%)
```

- `pass` — trials where every assertion passed (the only pass/fail signal).
- `trigger-ok` — for positive cases, the expected skill was invoked; for
  negative cases, the skill under test was *not* invoked. Telemetry only.
- `skills-used` — every repo skill any trial invoked; a negative case invoking
  the skill under test is a cross-triggering signal even when the trial passed.
- `!` lines — the assertion (or agent error) that failed, per trial.
- `FLAKY` = some trials passed; `FAIL` = none did.

### Delegation traces

With `--trace`, each trial in the results JSON gains a `trace` object built
from the agent's stream-json transcript. It is telemetry only: no assertion,
pass rate, or `trigger-ok` reads it, and without the flag the report is
unchanged.

```jsonc
"trace": {
  "version": 1,
  "verdict": "delegated",          // | "self-executed" | "unknown"
  "launches": [                    // one per sub-agent tool call, in order
    {"name": "Agent", "message": 0, "tool_use_id": "toolu_…",
     "subagent_type": "Plan", "run_in_background": true, "error": false}
  ],
  "max_launch_batch": 2,           // most launches in one assistant message
  "subagent_events": 14,           // events sub-agents emitted
  "tool_counts": {"Agent": 3, "Read": 2}   // top-level agent's tool calls
}
```

`subagent_type`, `run_in_background`, and `error` appear only when the
transcript carries them with the expected type.

**Host events read** (Claude Code `--output-format stream-json`, checked
against CLI 2.1.310); everything else is ignored, as are lines that are not
JSON objects:

- assistant `tool_use` blocks — every name is counted; `Agent` (and `Task`,
  its earlier name) is recorded as a launch;
- user `tool_result` blocks whose `tool_use_id` matches a launch — their
  `is_error` becomes the launch's `error`;
- any event whose `parent_tool_use_id` is set — a sub-agent's own traffic,
  counted in `subagent_events` and kept out of `tool_counts`.

**Verdict.** `delegated`: a launch that did not report an error, or any
sub-agent event. `self-executed`: the agent called tools, and no launch
succeeded. `unknown`: no tool call and no sub-agent event — an empty,
text-only, or unparseable transcript, a timeout, or a missing CLI. Prose that
*says* it delegated is never evidence.

**What it does not prove.** A launch shows the sub-agent was started, not
that its work was good. `max_launch_batch` shows launches issued together,
not that they ran concurrently; isolation between workers is not observable
in the transcript at all.

**Retention.** The trace keeps no prompt, description, tool input, text, or
result body — only the fields above. It lives in the gitignored
`eval-results/<timestamp>.json` beside the rest of the report, for as long as
you keep that file (no automatic expiry); `--keep-workspaces` does not
affect it, and the raw transcript is never saved.

## Case file schema

`skills/<name>/evals/cases.json`:

```jsonc
{
  "skill": "<name>",
  "fixtures": {
    "<fixture-name>": {
      "steps": [                       // applied in order; each step may have:
        { "files": { "path": "content" } },   // files written (bin/* → chmod +x)
        { "run": ["shell command"] }          // commands run in the workspace
      ]
    }
  },
  "cases": [
    {
      "id": "xx-h1",                   // unique; h=happy-path, n=negative
      "prompt": "…",
      "should_trigger": true,          // false for negatives
      "expect_skill": "other-skill",   // optional; which sibling should fire
                                       // (defaults: suite skill when
                                       // should_trigger, else null)
      "fixture": "<fixture-name>",
      "timeout": 3600,                 // optional; seconds, for a case that
                                       // cannot fit the 900 s default. An
                                       // explicit --timeout overrides it
      "assertions": [
        { "type": "output_regex",     "pattern": "…" },
        { "type": "output_not_regex", "pattern": "…" },
        { "type": "file_exists",      "path": "…" },
        { "type": "file_absent",      "path": "…" },
        { "type": "file_regex",       "path": "…", "pattern": "…" },
        { "type": "file_not_regex",   "path": "…", "pattern": "…" },
        { "type": "shell",            "cmd": "…" }   // pass = exit 0, cwd = workspace
      ]
    }
  ]
}
```

Suite rules (enforced by `--dry-run`): ≥ 10 cases, ≥ 5 positive, ≥ 5 negative,
unique ids, known assertion types, compilable regexes, fixtures resolvable,
`expect_skill` naming a real repo skill, and any `timeout` a positive whole
number of seconds. Negatives should include prompts that
belong to *sibling* skills (tagged `expect_skill`) to catch cross-triggering.

Assertions are deliberately cheap — regex/string/file/shell checks on the
outcome, no LLM-as-judge. Prefer asserting on planted defects by name (a
duplicated `parse_config`, a `#999999` contrast failure, an off-by-one the
README's spec contradicts) and on guardrails (clean `git status` for
report-only prompts, `.gh-calls.log` free of `issue close` without approval).

## What each suite covers

| Suite | Fixture | Signature assertions |
|-------|---------|----------------------|
| plan-feature | layered task app with behavioral tests, a missing-harness variant, and a roadmap doc to update in place | plans cite real integration points and observable tests; report-only leaves the baseline intact; requested plan updates preserve unrelated content |
| review-pr | feature branch with a spec-violating boundary bug (`> 8` vs "at least 8"), a dead function, a test gap | review names the bug/dead code; fix case leaves `>= 8` and `make test` green |
| describe-codebase | small layered service (app → handlers → db → config) | brief cites real layers; flow trace hits all hops; tree stays clean; `ARCHITECTURE.md` written only on explicit approval |
| review-design | tokens file + component with `#999` on white, 13px body text, off-scale spacing, two primary buttons | findings name contrast/scale issues; fix case removes `#999` in favor of a token |
| review-ux-psychology | signup flow: blank 7-field form, 0% progress, gated report, unanchored price | findings name the matching principle per screen; report-only leaves tree clean |
| simplify-sweep | duplicated `parse_config`, unused export, 4-deep nesting, stale `--fast` doc | each planted item surfaced by name; apply case keeps `make test` green |
| batch-merge-prs | fake `gh` shim + local bare remote with real `refs/pull/N/head`: a clean PR, one that conflicts with it, one already merged into main, one that breaks `make test`, one with an off-by-one against the README | listed PRs land as `Merge PR #…` commits; the already-merged PR is skipped with evidence; the conflict is resolved keeping both PRs' edits and reported; the test failure is attributed to its PR; the review names the off-by-one; no list means ask, not pick; nothing pushed or written to GitHub; no-remote fixture exercises the Phase 0 guardrail |
| manager | layered task app; an implemented branch with a zero-limit bug; the same branch pushed to a local bare remote behind a `gh` shim serving draft PR #12 with a required check that fails on a missing secret; a variant whose required gate is absent; the coordinator-only plan-review cases `mg-h16` and `mg-h17` carry their planted plan (it breaks layering and the one-PR rule) and the plan reviewer's findings in the prompt, so live planners never see them | the reviewed `plan.md` opens with Progress and ends in a review log, and the plan-only run saves it with no SWOT sections; a wrong plan-review finding (`P-2`) is refuted with evidence and the right one (`P-1`) confirmed, with the plan updated and the run directory's `plan.md` the only file written; an empty findings list yields 0 plan changes and no invented `P-` ids; a false code-review finding is refuted with evidence; the hand-back block reports the tier, the team (planner, plan reviewer, coordinator, implementer, code reviewers), plan findings and changes, and findings; a missing gate blocks; a failing CI check keeps the PR a draft (no `gh pr ready` call) and the item not `done`, with a `CI:` line naming the check; routine worker approvals are answered with the persistent option and logged on the board, a planner's source edit is rejected, a merge or an outside `rm -rf` is relayed tagged and never run while a routine fetch beside them is still answered, and an unattended force-push is rejected as `assumed`; asked to do the work itself, the manager delegates anyway and worker records appear in the run directory; main never touched |
| triage-issues | `gh` shim serving 3 issues (easy win matching a planted bug, duplicate pair, needs-info), logging all calls to `.gh-calls.log` | duplicates clustered; easy win grounded in `src/export.py`; report-only prompts produce **zero** `issue edit/close/comment` calls; labels-only produces `issue edit` and nothing else |
| file-issues | `gh` shim serving an open bug (#7, last row dropped), a closed feature (#3, `--header`), the label vocabulary, and recording what `issue create` would file under `.fixture/created-*`; an unauthenticated variant | a new bug is filed with a convention title, existing labels only, and the five body sections citing `src/export.py`; an open or closed match is linked instead of filed; a fix-it-too request leaves source, branch and HEAD untouched with no PR call; planted secrets never reach the issue; unauthenticated `gh` stops with no create |

The condensed suites retain 11 batch-merge cases (6 positive / 5 negative)
and 19 manager cases (14 positive / 5 negative). `bm-h1` covers numeric and URL
inputs together, including a conflict to resolve and an already-merged PR; `bm-h4`
checks attribution and branch restoration, and `bm-h6` checks review without
fixing. Manager implementation and review delegation cases stay separate
because they guard different forbidden actions.

The manager suite is mostly slices of the pipeline, sized to the default
900-second trial. Its one end-to-end case, `mg-h3`, nests a `plan-feature`
run for the planner and a `review-pr` run per code reviewer, so it carries its own
`"timeout": 3600` and a full sweep gives it that without a flag. It is also
the most expensive case in the repo — scope it in with `--case mg-h3` on
purpose.

`mg-h1` stops at the reviewed plan; `mg-h16` is the coordinator's plan-review step with one correct and one wrong reviewer finding, and `mg-h17` the same step with an empty findings list, where nothing may be invented. Neither prompt gives the planted plan to a live planner. `mg-h4` shows the status
board and team for two concurrent work items and starts nothing; `mg-h5`
validates two reviewer findings, one false; `mg-h6` blocks on a missing gate.
`mg-h7` and `mg-h8` tell the manager to do the work itself — a one-line
limit change, then a review — and pass only when it hands the work to a
worker anyway (`mg-h7` carries `"timeout": 1800`). `mg-h18` takes a
draft PR through hand-back: the finding is fixed, pushed and re-checked,
but the shim's `integration` check fails on a secret no commit can supply,
so the case passes only when `.gh-calls.log` shows `gh pr checks` and no
`gh pr ready`, a CI log exists in the run directory, and the hand-back is
`blocked` or `in progress`, never `done` (`"timeout": 1800`).

`mg-h3` is an **outcome** test, not an orchestration test. The runner keeps
the agent's text and the names of the skills it invoked, and saves only the
last 4,000 characters of that text; sub-agent launches, their order, and
their prompts are discarded. The delegation cases narrow that gap without
closing it: their prompts set the run directory to `.worktrees/manager-run`
(gitignored in every fixture), and they assert the board, the coordinator's
setup record, the review and re-check records, and a gate log ending
`exit: 0` exist there. A manager that did the work alone would have to forge
every one of those files to pass. Nothing proves planners and reviewers ran
in parallel and in isolation. `--trace` now records, per trial, which
sub-agents were launched, how many in one message, and whether sub-agent
events appeared ([Delegation traces](#delegation-traces)) — evidence a solo
manager cannot produce by writing files. It stays telemetry: no case asserts
on it yet, and concurrency and isolation remain unobservable.

The approval cases `mg-h19`–`mg-h21` have the same limit. The runner starts
the manager with `--dangerously-skip-permissions`, so no real host dialog
ever appears: the prompts are planted in the case prompt, and the cases grade
the manager's classification, its board rows, and that nothing forbidden
ran. Whether a host's launch args actually pre-grant what `references/herdr.md`
says is checked by hand in a Herdr session, and the wording by
`scripts/test-manager-approval.py` in the local gate.

## Adding evals for a new skill

1. Create `skills/<name>/evals/cases.json` following the schema above.
2. Build a fixture with *planted, named defects* the happy paths must surface,
   and shims for any external CLI (`bin/gh` pattern) so the suite runs offline.
3. Write 5 positive cases (include at least one report-only and, where the
   skill edits, one pre-approved apply case) and 5 negatives (most tagged with
   the sibling `expect_skill` they should route to).
4. `python3 run_evals.py --dry-run` until clean, then
   `--build-only --keep-workspaces` to verify the fixture, then a
   `--trials 1` smoke of one case.
