#!/usr/bin/env python3
"""Eval runner for the skills in this repository.

Each skill directory carries an evals/cases.json describing prompts, fixture
workspaces, and cheap outcome assertions. This runner materializes a clean,
isolated workspace per trial (temp dir outside the repo, fixture files + setup
commands, all repo skills copied into .claude/skills/ minus their evals/), runs
the prompt through `claude -p`, and grades the *outcome* — assertions on the
final output and workspace state — not whether the skill loaded on the first
turn. Skill-trigger telemetry is recorded separately from pass/fail.

Usage:
  python3 run_evals.py                          # all skills, 3 trials/case
  python3 run_evals.py --skill review-pr        # one skill
  python3 run_evals.py --skill review-pr --case rp-h1
  python3 run_evals.py --trials 1 --model haiku # cheaper smoke run
  python3 run_evals.py --ablation --skill describe-codebase
                                                # happy-path cases WITH vs
                                                # WITHOUT the skill loaded;
                                                # flags retirement candidates
  python3 run_evals.py --without-skill review-pr --skill review-pr
                                                # single ablation arm
  python3 run_evals.py --dry-run                # validate case files only
  python3 run_evals.py --build-only --case bm-h1 --keep-workspaces
                                                # materialize fixtures, no agent

Case file schema (skills/<name>/evals/cases.json):
  {
    "skill": "<name>",
    "fixtures": { "<fx>": { "steps": [ {"files": {path: content}},
                                       {"run": [shell cmd, ...]} ... ] } },
    "cases": [ { "id", "prompt", "should_trigger", "fixture",
                 "expect_skill" (optional; defaults to the suite skill when
                                 should_trigger, else null),
                 "assertions": [ {"type": "output_regex"|"output_not_regex",
                                  "pattern": ...},
                                 {"type": "file_exists"|"file_absent",
                                  "path": ...},
                                 {"type": "file_regex"|"file_not_regex",
                                  "path": ..., "pattern": ...},
                                 {"type": "shell", "cmd": ...} ] } ]
  }

A trial passes iff every assertion passes. `shell` assertions pass on exit 0
and run inside the workspace. Fixture `bin/` files are made executable and
prepended to PATH (for CLI shims like a fake `gh`). Results are printed and
written as JSON under eval-results/.

Cost note: the full suite is 7 skills x 10+ cases x 3 trials of a real agent.
Use --skill/--case/--trials to scope, and --model to pick a cheaper model.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILLS_DIR = REPO / "skills"
RESULTS_DIR = REPO / "eval-results"

ASSERTION_TYPES = {
    "output_regex", "output_not_regex",
    "file_exists", "file_absent",
    "file_regex", "file_not_regex",
    "shell",
}


def all_skills():
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))


def load_suite(skill):
    path = SKILLS_DIR / skill / "evals" / "cases.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def validate_suite(skill, suite):
    """Return a list of problems (empty list = valid)."""
    problems = []
    if suite.get("skill") != skill:
        problems.append(f"suite 'skill' is {suite.get('skill')!r}, expected {skill!r}")
    cases = suite.get("cases", [])
    if len(cases) < 10:
        problems.append(f"only {len(cases)} cases; need >= 10")
    n_pos = sum(1 for c in cases if c.get("should_trigger"))
    n_neg = len(cases) - n_pos
    if n_pos < 5:
        problems.append(f"only {n_pos} should_trigger cases; need >= 5")
    if n_neg < 5:
        problems.append(f"only {n_neg} negative cases; need >= 5")
    seen_ids = set()
    for c in cases:
        cid = c.get("id", "<missing id>")
        if cid in seen_ids:
            problems.append(f"{cid}: duplicate id")
        seen_ids.add(cid)
        if not c.get("prompt"):
            problems.append(f"{cid}: missing prompt")
        if "should_trigger" not in c:
            problems.append(f"{cid}: missing should_trigger")
        fx = c.get("fixture")
        if fx and fx not in suite.get("fixtures", {}):
            problems.append(f"{cid}: unknown fixture {fx!r}")
        if not c.get("assertions"):
            problems.append(f"{cid}: no assertions")
        for a in c.get("assertions", []):
            t = a.get("type")
            if t not in ASSERTION_TYPES:
                problems.append(f"{cid}: unknown assertion type {t!r}")
                continue
            if "regex" in t:
                try:
                    re.compile(a.get("pattern", ""))
                except re.error as e:
                    problems.append(f"{cid}: bad regex {a.get('pattern')!r}: {e}")
        exp = c.get("expect_skill")
        if exp and exp not in all_skills():
            problems.append(f"{cid}: expect_skill {exp!r} is not a repo skill")
    return problems


def base_env(ws):
    env = dict(os.environ)
    ws_bin = ws / "bin"
    env["PATH"] = str(ws_bin) + os.pathsep + env["PATH"]
    env.setdefault("GIT_AUTHOR_NAME", "eval-runner")
    env.setdefault("GIT_AUTHOR_EMAIL", "eval@example.invalid")
    env.setdefault("GIT_COMMITTER_NAME", "eval-runner")
    env.setdefault("GIT_COMMITTER_EMAIL", "eval@example.invalid")
    return env


def build_workspace(tmp_root, suite, case, loaded_skills):
    ws = Path(tempfile.mkdtemp(prefix=f"{case['id']}-", dir=tmp_root))
    for s in loaded_skills:
        shutil.copytree(
            SKILLS_DIR / s,
            ws / ".claude" / "skills" / s,
            ignore=shutil.ignore_patterns("evals"),
        )
    fixture = suite.get("fixtures", {}).get(case.get("fixture", ""))
    env = base_env(ws)
    if fixture:
        for step in fixture.get("steps", []):
            for rel, content in step.get("files", {}).items():
                p = ws / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
                if rel.startswith("bin/"):
                    p.chmod(p.stat().st_mode | 0o755)
            for cmd in step.get("run", []):
                r = subprocess.run(
                    cmd, shell=True, cwd=ws, env=env,
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    raise RuntimeError(
                        f"fixture command failed in {ws}:\n  $ {cmd}\n{r.stderr}"
                    )
    return ws


def claude_supports(flag):
    try:
        helptext = subprocess.run(
            ["claude", "--help"], capture_output=True, text=True, timeout=30
        ).stdout
    except Exception:
        return False
    return flag in helptext


def run_agent(ws, prompt, model, timeout, isolate_settings):
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--dangerously-skip-permissions",
    ]
    if isolate_settings:
        cmd += ["--setting-sources", "project"]
    if model:
        cmd += ["--model", model]
    try:
        r = subprocess.run(
            cmd, cwd=ws, env=base_env(ws),
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "", set(), "timeout"
    except FileNotFoundError:
        return "", set(), "claude CLI not found on PATH"
    texts, skills_used = [], set()
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "tool_use" and block.get("name") == "Skill":
                    name = str(block.get("input", {}).get("skill", ""))
                    skills_used.add(name.split(":")[-1])
        elif ev.get("type") == "result" and ev.get("result"):
            texts.append(str(ev["result"]))
    err = "" if r.returncode == 0 else f"claude exited {r.returncode}: {r.stderr[-500:]}"
    return "\n".join(texts), skills_used, err


def check_assertion(a, output, ws):
    t = a["type"]
    if t == "output_regex":
        return bool(re.search(a["pattern"], output, re.S))
    if t == "output_not_regex":
        return not re.search(a["pattern"], output, re.S)
    if t == "file_exists":
        return (ws / a["path"]).exists()
    if t == "file_absent":
        return not (ws / a["path"]).exists()
    if t == "file_regex":
        p = ws / a["path"]
        return p.exists() and bool(re.search(a["pattern"], p.read_text(), re.S))
    if t == "file_not_regex":
        p = ws / a["path"]
        return (not p.exists()) or not re.search(a["pattern"], p.read_text(), re.S)
    if t == "shell":
        r = subprocess.run(
            a["cmd"], shell=True, cwd=ws, env=base_env(ws),
            capture_output=True, text=True,
        )
        return r.returncode == 0
    raise ValueError(f"unknown assertion type {t!r}")


def expected_skill(suite, case):
    if "expect_skill" in case:
        return case["expect_skill"]
    return suite["skill"] if case.get("should_trigger") else None


def run_case(args, tmp_root, suite, case, loaded_skills, isolate_settings):
    trials = []
    for i in range(args.trials):
        ws = build_workspace(tmp_root, suite, case, loaded_skills)
        if args.build_only:
            print(f"  built {case['id']} trial {i + 1}: {ws}")
            trials.append({"workspace": str(ws), "built": True})
            continue
        output, skills_used, err = run_agent(
            ws, case["prompt"], args.model, args.timeout, isolate_settings
        )
        failures = []
        if err:
            failures.append(f"agent-error: {err}")
        for a in case.get("assertions", []):
            try:
                ok = check_assertion(a, output, ws)
            except Exception as e:  # bad assertion should fail loudly, not pass
                ok, e_note = False, str(e)
                failures.append(f"assertion-error {a['type']}: {e_note}")
                continue
            if not ok:
                failures.append(f"{a['type']}: {a.get('pattern', a.get('path', a.get('cmd', '')))}")
        exp = expected_skill(suite, case)
        under_test = suite["skill"]
        if case.get("should_trigger"):
            trigger_ok = exp in skills_used
        else:
            trigger_ok = under_test not in skills_used
        trials.append({
            "workspace": str(ws),
            "passed": not failures,
            "failures": failures,
            "skills_used": sorted(skills_used),
            "trigger_ok": trigger_ok,
            # tail of the agent's output, for debugging failed assertions
            "output_tail": output[-4000:],
        })
        if not args.keep_workspaces:
            shutil.rmtree(ws, ignore_errors=True)
    return trials


def summarize_case(case, trials):
    n = len(trials)
    passes = sum(1 for t in trials if t.get("passed"))
    trig = sum(1 for t in trials if t.get("trigger_ok"))
    used = sorted({s for t in trials for s in t.get("skills_used", [])})
    return passes, trig, n, used


def run_suite(args, tmp_root, skill, suite, loaded_skills, isolate_settings, label=""):
    cases = suite["cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"  (no case {args.case!r} in {skill})")
            return {}
    if args.ablation:
        cases = [c for c in cases if c.get("should_trigger")]
    results = {}
    tag = f" [{label}]" if label else ""
    print(f"\n== {skill}{tag} ==")
    for case in cases:
        trials = run_case(args, tmp_root, suite, case, loaded_skills, isolate_settings)
        results[case["id"]] = trials
        if args.build_only:
            continue
        passes, trig, n, used = summarize_case(case, trials)
        flag = "" if passes == n else "  <-- FAIL" if passes == 0 else "  <-- FLAKY"
        extra = f"  skills-used: {','.join(used)}" if used else ""
        print(f"  {case['id']:<10} pass {passes}/{n}  trigger-ok {trig}/{n}{extra}{flag}")
        for t in trials:
            for f in t.get("failures", []):
                print(f"             ! {f}")
    if not args.build_only and results:
        total = sum(len(t) for t in results.values())
        passed = sum(1 for ts in results.values() for t in ts if t.get("passed"))
        print(f"  -- {skill}{tag}: {passed}/{total} trials passed "
              f"({100 * passed // max(total, 1)}%)")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", action="append",
                    help="skill(s) to run; default all with an evals/cases.json")
    ap.add_argument("--case", help="run a single case id")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--model", help="model override passed to claude")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per trial")
    ap.add_argument("--without-skill", metavar="SKILL",
                    help="load every repo skill except this one (single ablation arm)")
    ap.add_argument("--ablation", action="store_true",
                    help="run happy-path cases WITH and WITHOUT each selected "
                         "skill and compare (retirement-candidate detection)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate case files and exit")
    ap.add_argument("--build-only", action="store_true",
                    help="materialize fixtures without invoking the agent")
    ap.add_argument("--keep-workspaces", action="store_true")
    args = ap.parse_args()

    skills = args.skill or all_skills()
    suites = {}
    problems_all = {}
    for s in skills:
        suite = load_suite(s)
        if suite is None:
            print(f"note: {s} has no evals/cases.json; skipping")
            continue
        problems = validate_suite(s, suite)
        if problems:
            problems_all[s] = problems
        suites[s] = suite

    if problems_all:
        print("case-file problems:")
        for s, ps in problems_all.items():
            for p in ps:
                print(f"  {s}: {p}")
        if args.dry_run:
            sys.exit(1)
    if args.dry_run:
        for s, suite in suites.items():
            n = len(suite["cases"])
            n_pos = sum(1 for c in suite["cases"] if c.get("should_trigger"))
            print(f"  {s}: {n} cases ({n_pos} positive / {n - n_pos} negative) — OK")
        print("dry run: all case files valid")
        return

    isolate_settings = claude_supports("--setting-sources")
    if not isolate_settings and not args.build_only:
        print("warning: this claude CLI lacks --setting-sources; user-level "
              "skills/settings will also be loaded in eval workspaces")

    tmp_root = tempfile.mkdtemp(prefix="agents-library-evals-")
    print(f"workspaces under: {tmp_root}")
    started = time.strftime("%Y%m%d-%H%M%S")
    report = {"started": started, "trials": args.trials, "model": args.model,
              "skills": {}}

    for s, suite in suites.items():
        if args.ablation:
            with_arm = run_suite(args, tmp_root, s, suite, all_skills(),
                                 isolate_settings, label="with")
            without = [x for x in all_skills() if x != s]
            without_arm = run_suite(args, tmp_root, s, suite, without,
                                    isolate_settings, label="without")
            report["skills"][s] = {"with": with_arm, "without": without_arm}
            if not args.build_only:
                def rate(res):
                    total = sum(len(t) for t in res.values())
                    ok = sum(1 for ts in res.values() for t in ts if t.get("passed"))
                    return ok, total
                wp, wt = rate(with_arm)
                op, ot = rate(without_arm)
                verdict = ("RETIREMENT CANDIDATE — passes without the skill"
                           if ot and op >= wp else "keep — skill still earns its pass rate")
                print(f"  == ablation {s}: with {wp}/{wt} vs without {op}/{ot} -> {verdict}")
        else:
            loaded = all_skills()
            if args.without_skill:
                loaded = [x for x in loaded if x != args.without_skill]
            report["skills"][s] = run_suite(args, tmp_root, s, suite, loaded,
                                            isolate_settings)

    if not args.build_only:
        RESULTS_DIR.mkdir(exist_ok=True)
        out = RESULTS_DIR / f"{started}.json"
        out.write_text(json.dumps(report, indent=2))
        print(f"\nresults written to {out}")
    if not args.keep_workspaces and not args.build_only:
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
