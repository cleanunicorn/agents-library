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
automation, and must not be — a full sweep is 210 real agent runs. Run it by
hand, scoped, when you change a skill or update the model.

## Layout

```
run_evals.py                      # the shared runner (stdlib Python 3)
skills/<name>/evals/cases.json    # 10 cases per skill: 5 positive, 5 negative
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
skills each trial invoked).

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
```

**Cost note:** the full suite is 7 skills × 10 cases × 3 trials = 210 agent
runs, several of them multi-sub-agent orchestrations — hours of wall clock and
meaningful token spend. Ramp up: `--dry-run` → `--trials 1` → full runs per
skill → ablation.

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
`expect_skill` naming a real repo skill. Negatives should include prompts that
belong to *sibling* skills (tagged `expect_skill`) to catch cross-triggering.

Assertions are deliberately cheap — regex/string/file/shell checks on the
outcome, no LLM-as-judge. Prefer asserting on planted defects by name (a
duplicated `parse_config`, a `#999999` contrast failure, an off-by-one the
README's spec contradicts) and on guardrails (clean `git status` for
report-only prompts, `.gh-calls.log` free of `issue close` without approval).

## What each suite covers

| Suite | Fixture | Signature assertions |
|-------|---------|----------------------|
| review-pr | feature branch with a spec-violating boundary bug (`> 8` vs "at least 8"), a dead function, a test gap | review names the bug/dead code; fix case leaves `>= 8` and `make test` green |
| describe-codebase | small layered service (app → handlers → db → config) | brief cites real layers; flow trace hits all hops; tree stays clean; `ARCHITECTURE.md` written only on explicit approval |
| review-design | tokens file + component with `#999` on white, 13px body text, off-scale spacing, two primary buttons | findings name contrast/scale issues; fix case removes `#999` in favor of a token |
| review-ux-psychology | signup flow: blank 7-field form, 0% progress, gated report, unanchored price | findings name the matching principle per screen; report-only leaves tree clean |
| simplify-sweep | duplicated `parse_config`, unused export, 4-deep nesting, stale `--fast` doc | each planted item surfaced by name; apply case keeps `make test` green |
| batch-merge-prs | fake `gh` shim + local bare remote with real `refs/pull/N/head` (one trivial PR, one conflicting) | batch branch exists with a `Merge PR #…` commit; conflict reported, never half-resolved; no-remote fixture exercises the Phase 0 guardrail |
| triage-issues | `gh` shim serving 3 issues (easy win matching a planted bug, duplicate pair, needs-info), logging all calls to `.gh-calls.log` | duplicates clustered; easy win grounded in `src/export.py`; report-only prompts produce **zero** `issue edit/close/comment` calls; labels-only produces `issue edit` and nothing else |

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
