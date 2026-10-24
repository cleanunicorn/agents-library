#!/usr/bin/env python3
"""Exercise the manager's worker watcher against a stub `herdr` and a fake clock.

The manager used to see a worker waiting on a permission prompt only when a
turn happened to read live state, so a prompt raised between turns could sit
unanswered. The approval evals hand the manager a prompt directly, which
tests the decision and never the discovery. These tests run the real watcher
CLI as a subprocess against a stub `herdr` that serves scripted agent states
and logs every call, with `--now` standing in for the clock, so discovery,
deduplication, claims, backoff and the watcher's lifecycle are held without a
live Herdr, a model, or the network.

The prose-contract tests at the end hold the manager's side: the watcher
starts before the first worker, every resume drains it, and the approval
policy stays the manager's alone.
"""

import json
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANAGER = ROOT / "skills" / "manager"
WATCHER = MANAGER / "scripts" / "watch-workers.py"
SECRET = "SECRET-TOKEN-4f9a"
CLAUDE_PROMPT = f"""Bash command
  curl -H 'Authorization: {SECRET}' https://example.test
Do you want to proceed?
❯ 1. Yes
  2. Yes, and don't ask again for curl commands
  3. No, and tell Claude what to do differently (esc)
"""
CONFIRM_PROMPT = "Write ~/.claude/settings.json?\nDo you want to proceed?\n❯ 1. Yes\n  2. No\n"
WORKING_TEXT = "⏺ Reading skills/manager/SKILL.md\n✳ Thinking… (12s · esc to interrupt)\n"

# A stub `herdr`: serves `agent get` and `agent read` from a scenario file the
# test rewrites between sweeps, and logs every call so a test can prove the
# watcher never writes terminal input.
STUB = r'''#!/usr/bin/env python3
import json, os, sys, time
root = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(root, "calls.log"), "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\n")
scenario = json.load(open(os.path.join(root, "scenario.json")))
args = sys.argv[1:]
if args[:2] not in (["agent", "get"], ["agent", "read"]):
    print(json.dumps({"error": {"code": "unexpected", "message": " ".join(args)}}))
    sys.exit(9)
agent = scenario.get(args[2])
if agent is None:
    print(json.dumps({"error": {"code": "agent_not_found", "message": "not found"}, "id": "cli:agent:get"}))
    sys.exit(1)
time.sleep(agent.get("sleep", 0))
if "raw" in agent:
    print(agent["raw"])
    sys.exit(0)
if args[1] == "read":
    sys.stdout.write(agent.get("read", ""))
    sys.exit(0)
record = {"agent": "claude", "agent_status": agent["status"], "name": args[2],
          "pane_id": "w1:p9", "terminal_id": agent.get("terminal", "term_1")}
if agent.get("session"):
    record["agent_session"] = {"kind": "id", "value": agent["session"]}
print(json.dumps({"id": "cli:agent:get", "result": {"agent": record}}))
'''


class Run:
    """One manager run directory with its own stub Herdr."""

    def __init__(self, test):
        self.dir = Path(tempfile.mkdtemp(prefix="watcher-test-"))
        test.addCleanup(self.cleanup)
        self.processes = []
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        self.herdr = self.bin / "herdr"
        self.herdr.write_text(STUB, encoding="utf-8")
        self.herdr.chmod(0o755)
        self.agents = {}
        self.save()

    def cleanup(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
                process.wait()
        shutil.rmtree(self.dir, ignore_errors=True)

    def save(self):
        (self.bin / "scenario.json").write_text(json.dumps(self.agents), encoding="utf-8")

    def agent(self, name, status, read="", session="ses-1", sleep=0, terminal="term_1"):
        self.agents[name] = {"status": status, "read": read, "session": session, "sleep": sleep, "terminal": terminal}
        self.save()

    def reads(self, name=""):
        return [c for c in self.calls() if c.startswith(f"agent read {name}".rstrip())]

    def calls(self):
        log = self.bin / "calls.log"
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def cli(self, *args, now=None, timeout=30):
        command = [sys.executable, str(WATCHER), *args, "--run-dir", str(self.dir), "--herdr", str(self.herdr)]
        if now is not None:
            command += ["--now", str(now)]
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)

    def start(self, *args):
        command = [sys.executable, str(WATCHER), "run", "--run-dir", str(self.dir), "--herdr", str(self.herdr), *args]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.processes.append(process)
        return process

    def register(self, name, item="item-a", role="coordinator"):
        result = self.cli("register", "--name", name, "--item", item, "--role", role)
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    def sweep(self, now, timeout="2"):
        result = self.cli("sweep", "--timeout", timeout, now=now)
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    def status(self):
        result = self.cli("status")
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    def events(self, state=None):
        return [e for e in self.status()["events"] if state is None or e["state"] == state]

    def wait(self, now):
        return self.cli("wait", now=now)


def event_ids(output):
    return re.findall(r"(?m)^EVENT (\S+)", output)


class DetectionTests(unittest.TestCase):
    def test_a_blocked_worker_is_found_within_two_sweeps(self):
        run = Run(self)
        run.agent("coord", "working", WORKING_TEXT)
        run.register("coord")
        run.sweep(now=1000)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.sweep(now=1005)
        pending = run.events("pending")
        self.assertEqual(len(pending), 1, "a blocked worker produced no pending event")
        self.assertEqual((pending[0]["worker"], pending[0]["item"], pending[0]["kind"]), ("coord", "item-a", "blocked"))

    def test_a_prompt_behind_a_working_status_is_found_after_two_sweeps(self):
        run = Run(self)
        run.agent("coord", "working", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        self.assertEqual(run.events(), [], "one working observation already triggered inspection")
        self.assertFalse(run.reads(), "a fresh working status was read")
        run.sweep(now=1005)
        self.assertEqual([e["kind"] for e in run.events("pending")], ["suspected"],
                         "a prompt behind an unchanged working status was never found")

    def test_an_unknown_status_is_inspected_at_once(self):
        run = Run(self)
        run.agent("coord", "unknown", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        self.assertEqual([e["kind"] for e in run.events("pending")], ["suspected"])

    def test_each_hosts_prompt_wording_is_recognized(self):
        screens = {
            "claude": "Edit file\nDo you want to make this edit to app.py?\n❯ 1. Yes\n",
            "opencode-once": "Bash: rm build/\n  Allow once   Reject\n",
            "opencode-always": "Edit src/app.py\n  → Always allow until restart\n",
            "claude-session": "  2. Yes, don't ask again for this command\n",
            "kilo": "Permission required: write to /tmp/x\n",
            "codex": "Overwrite build/out.txt? [y/N]\n",
        }
        for host, screen in screens.items():
            with self.subTest(host=host):
                run = Run(self)
                run.agent("coord", "unknown", WORKING_TEXT + screen)
                run.register("coord")
                run.sweep(now=1000)
                self.assertEqual([e["kind"] for e in run.events("pending")], ["suspected"],
                                 f"{host}'s prompt wording is not recognized")

    def test_plain_work_and_finished_turns_raise_nothing(self):
        run = Run(self)
        run.agent("busy", "working", WORKING_TEXT)
        run.agent("idle", "idle", CLAUDE_PROMPT)
        run.register("busy")
        run.register("idle", item="item-b")
        for now in (1000, 1005, 1010):
            run.sweep(now=now)
        self.assertEqual(run.events(), [], "ordinary output or a finished turn raised an event")
        self.assertFalse(run.reads("idle"),
                         "a finished turn was inspected; its result file is the manager's signal")

    def test_the_same_prompt_is_one_event_and_a_new_one_supersedes_it(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        run.sweep(now=1005)
        first = run.events("pending")
        self.assertEqual(len(first), 1, "a prompt seen twice became two events")
        run.agent("coord", "blocked", CONFIRM_PROMPT)
        run.sweep(now=1010)
        states = {e["id"]: e["state"] for e in run.events()}
        self.assertEqual(states[first[0]["id"]], "superseded", "a follow-up dialog left the old event live")
        self.assertEqual(len(run.events("pending")), 1, "the follow-up dialog is not its own event")

    def test_a_spinner_or_timer_change_does_not_split_one_prompt(self):
        run = Run(self)
        run.agent("coord", "blocked", "\x1b[33m✳\x1b[0m waiting 3s\n" + CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        run.agent("coord", "blocked", "✶ waiting 41s\n" + CLAUDE_PROMPT)
        run.sweep(now=1005)
        self.assertEqual(len(run.events()), 1, "terminal noise changed the prompt identity")

    def test_a_prompt_that_differs_only_in_a_number_is_a_new_event(self):
        run = Run(self)
        run.agent("coord", "blocked", "Bash command\n  kill 1234\nDo you want to proceed?\n❯ 1. Yes\n")
        run.register("coord")
        run.sweep(now=1000)
        first = run.events("pending")[0]["id"]
        token = re.search(r"token=(\S+)", run.cli("claim", "--event", first, now=1001).stdout).group(1)
        run.cli("await-user", "--event", first, "--token", token, now=1002)
        run.agent("coord", "blocked", "Bash command\n  kill 5678\nDo you want to proceed?\n❯ 1. Yes\n")
        run.sweep(now=1005)
        states = {e["id"]: e["state"] for e in run.events()}
        self.assertEqual(states[first], "superseded", "a changed pid stayed hidden behind the parked event")
        self.assertEqual(len(run.events("pending")), 1, "a prompt for a different pid raised no event")

    def test_a_replacement_worker_does_not_inherit_old_events(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT, session="ses-old")
        run.register("coord")
        run.sweep(now=1000)
        old = run.events("pending")[0]["id"]
        run.agent("coord", "blocked", CLAUDE_PROMPT, session="ses-new")
        run.sweep(now=1005)
        states = {e["id"]: e["state"] for e in run.events()}
        self.assertEqual(states[old], "superseded", "a replacement worker inherited its predecessor's event")
        self.assertEqual(len(run.events("pending")), 1)

    def test_without_a_session_id_the_terminal_identifies_the_worker(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT, session=None, terminal="term_a")
        run.register("coord")
        run.sweep(now=1000)
        run.sweep(now=1005)
        self.assertEqual(len(run.events()), 1, "a session-less worker's prompt split into two events")
        old = run.events()[0]["id"]
        run.agent("coord", "blocked", CLAUDE_PROMPT, session=None, terminal="term_b")
        run.sweep(now=1010)
        states = {e["id"]: e["state"] for e in run.events()}
        self.assertEqual(states[old], "superseded", "a session-less replacement inherited the old event")
        self.assertEqual(len(run.events("pending")), 1)

    def test_a_prompt_that_goes_away_is_cleared(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        run.agent("coord", "working", WORKING_TEXT)
        run.sweep(now=1005)
        self.assertEqual([e["state"] for e in run.events()], ["cleared"])

    def test_the_same_prompt_after_its_event_closed_is_a_new_event(self):
        for close in ("cleared", "resolved"):
            with self.subTest(close=close):
                run = Run(self)
                run.agent("coord", "blocked", CLAUDE_PROMPT)
                run.register("coord")
                run.sweep(now=1000)
                first = run.events("pending")[0]["id"]
                if close == "resolved":
                    token = re.search(r"token=(\S+)", run.cli("claim", "--event", first, now=1001).stdout).group(1)
                    run.cli("resolve", "--event", first, "--token", token, now=1002)
                else:
                    run.agent("coord", "working", WORKING_TEXT)
                    run.sweep(now=1005)
                run.agent("coord", "blocked", CLAUDE_PROMPT)
                run.sweep(now=1010)
                states = {e["id"]: e["state"] for e in run.events()}
                self.assertEqual(states[first], close, "the closed event was reopened")
                self.assertEqual(len(run.events("pending")), 1, "a re-asked prompt was swallowed or crashed the sweep")

    def test_one_hung_worker_does_not_stall_the_sweep(self):
        run = Run(self)
        run.agent("hung", "working", sleep=10)
        run.agent("helper", "blocked", CLAUDE_PROMPT)
        run.register("hung")
        run.register("helper", item="question-1", role="helper")
        started = time.monotonic()
        run.sweep(now=1000, timeout="0.5")
        self.assertLess(time.monotonic() - started, 5, "a hung worker serialized the sweep")
        self.assertEqual([e["worker"] for e in run.events("pending")], ["helper"],
                         "the helper's block was missed while another worker hung")
        workers = {w["name"]: w for w in run.status()["workers"]}
        self.assertEqual(workers["hung"]["failures"], 1, "the timeout was not counted")

    def test_a_malformed_agent_record_is_a_failed_poll_not_a_crash(self):
        run = Run(self)
        run.agents["gone"] = {"raw": json.dumps({"result": {"agent": None}})}
        run.agents["odd"] = {"raw": json.dumps({"result": {"agent": {"agent_status": "blocked", "agent_session": "x"}}})}
        run.agents["list"] = {"raw": json.dumps({"result": []})}
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        for name in ("gone", "odd", "list", "coord"):
            run.register(name)
        run.sweep(now=1000)
        failures = {w["name"]: w["failures"] for w in run.status()["workers"]}
        self.assertEqual((failures["gone"], failures["list"]), (1, 1), "a malformed record was not counted as a failed poll")
        self.assertEqual(sorted(e["worker"] for e in run.events("pending")), ["coord", "odd"],
                         "one malformed record stopped detection for the others")

    def test_simultaneous_blocks_are_all_kept(self):
        run = Run(self)
        for index in range(12):
            run.agent(f"w{index}", "blocked", CLAUDE_PROMPT, session=f"ses-{index}")
            run.register(f"w{index}", item=f"item-{index}")
        run.sweep(now=1000)
        self.assertEqual(len(run.events("pending")), 12, "a block was lost when many arrived at once")

    def test_a_failed_read_never_clears_an_event(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        del run.agents["coord"]
        run.save()
        run.sweep(now=1005)
        self.assertEqual(len(run.events("pending")), 1, "a transport failure resolved a pending event")

    def test_no_prompt_text_or_secret_is_stored_or_printed(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        outputs = [run.sweep(now=1000).stdout, run.cli("status").stdout, run.wait(now=1001).stdout]
        stored = b"".join(p.read_bytes() for p in run.dir.glob("watcher.sqlite3*"))
        for text in outputs + [stored.decode("utf-8", "replace")]:
            self.assertNotIn(SECRET, text, "prompt text leaked into the store or an output")
            self.assertNotIn("curl", text, "prompt text leaked into the store or an output")

    def test_the_watcher_never_writes_terminal_input(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        for now in (1000, 1005, 1010):
            run.sweep(now=now)
            run.wait(now=now + 1)
        verbs = {" ".join(c.split()[:2]) for c in run.calls()}
        self.assertEqual(verbs, {"agent get", "agent read"}, "the watcher called more than get and read")
        herdr_verbs = re.findall(r'\["agent", "([a-z-]+)"', WATCHER.read_text(encoding="utf-8"))
        self.assertEqual(set(herdr_verbs), {"get", "read"}, "the watcher source can call more than get and read")


class HandlingTests(unittest.TestCase):
    def blocked_run(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        return run, run.events("pending")[0]["id"]

    def test_wait_names_the_event_and_backs_off_to_thirty_seconds(self):
        run, event = self.blocked_run()
        first = run.wait(now=1000)
        self.assertEqual(first.returncode, 0)
        self.assertRegex(first.stdout, rf"(?m)^EVENT {event} worker=coord item=item-a role=coordinator kind=blocked$")
        last = 1000
        for gap in (5, 10, 20, 30, 30):
            self.assertEqual(event_ids(run.wait(now=last + gap - 1).stdout), [], f"re-notified before the {gap} s backoff")
            self.assertEqual(event_ids(run.wait(now=last + gap).stdout), [event], f"not re-notified after {gap} s")
            last += gap

    def test_a_claim_is_the_acknowledgment_and_has_one_winner(self):
        run, event = self.blocked_run()
        run.wait(now=1000)
        won = run.cli("claim", "--event", event, now=1001)
        lost = run.cli("claim", "--event", event, now=1001)
        self.assertEqual(won.returncode, 0, won.stdout)
        self.assertNotEqual(lost.returncode, 0, "two handlers claimed the same event")
        self.assertIn("NOT_CLAIMABLE", lost.stdout)
        self.assertEqual(event_ids(run.wait(now=1010).stdout), [], "a claimed event was notified again")

    def test_an_unresolved_claim_is_due_again_after_thirty_seconds(self):
        run, event = self.blocked_run()
        run.cli("claim", "--event", event, now=1000)
        self.assertEqual(event_ids(run.wait(now=1029).stdout), [], "a claim expired early")
        self.assertEqual(event_ids(run.wait(now=1030).stdout), [event], "an abandoned claim was never retried")

    def test_resolve_needs_the_claim_token(self):
        run, event = self.blocked_run()
        token = re.search(r"token=(\S+)", run.cli("claim", "--event", event, now=1000).stdout).group(1)
        self.assertNotEqual(run.cli("resolve", "--event", event, "--token", "wrong", now=1001).returncode, 0)
        self.assertEqual(run.cli("resolve", "--event", event, "--token", token, now=1001).returncode, 0)
        self.assertEqual([(e["state"], e["detected_at"], e["updated_at"]) for e in run.events()],
                         [("resolved", 1000, 1001)], "status hides when an event was raised and settled")
        self.assertEqual(event_ids(run.wait(now=1100).stdout), [])

    def test_an_answered_prompt_that_cleared_resolves_quietly(self):
        run, event = self.blocked_run()
        token = re.search(r"token=(\S+)", run.cli("claim", "--event", event, now=1000).stdout).group(1)
        run.agent("coord", "working", WORKING_TEXT)
        run.sweep(now=1005)
        result = run.cli("resolve", "--event", event, "--token", token, now=1006)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ALREADY cleared", result.stdout)

    def test_a_dismissed_suspected_screen_is_not_raised_again_until_it_changes(self):
        run = Run(self)
        run.agent("coord", "unknown", CLAUDE_PROMPT)
        run.register("coord")
        run.sweep(now=1000)
        event = run.events("pending")[0]["id"]
        token = re.search(r"token=(\S+)", run.cli("claim", "--event", event, now=1001).stdout).group(1)
        run.cli("resolve", "--event", event, "--token", token, now=1002)
        for now in (1005, 1010, 1015):
            run.sweep(now=now)
        self.assertEqual(run.events("pending"), [], "a dismissed false positive kept waking the manager")
        run.agent("coord", "working", WORKING_TEXT)
        run.sweep(now=1020)
        run.agent("coord", "unknown", CLAUDE_PROMPT)
        run.sweep(now=1025)
        self.assertEqual(len(run.events("pending")), 1, "the same prompt returning later was never raised")

    def test_awaiting_the_user_stays_visible_without_notifications(self):
        run, event = self.blocked_run()
        token = re.search(r"token=(\S+)", run.cli("claim", "--event", event, now=1000).stdout).group(1)
        self.assertEqual(run.cli("await-user", "--event", event, "--token", token, now=1001).returncode, 0)
        for now in (1031, 1100, 2000):
            self.assertEqual(event_ids(run.wait(now=now).stdout), [], "an event awaiting the user was re-notified")
        self.assertEqual(run.status()["counts"]["awaiting_user"], 1, "the event awaiting the user left the board")
        again = run.cli("claim", "--event", event, now=2001)
        self.assertEqual(again.returncode, 0, "the user's answer cannot be applied")

    def test_unregister_clears_the_workers_open_events(self):
        run, event = self.blocked_run()
        run.cli("unregister", "--name", "coord", now=1001)
        self.assertEqual([e["state"] for e in run.events()], ["cleared"], "a closed worker's event stayed open")
        self.assertEqual(event_ids(run.wait(now=1100).stdout), [], "a closed worker's event is still notified")

    def test_claiming_an_unknown_event_is_refused(self):
        run = Run(self)
        result = run.cli("claim", "--event", "nosuchevent", now=1000)
        self.assertEqual((result.returncode, result.stdout.strip()), (1, "NOT_CLAIMABLE nosuchevent state=unknown"))

    def test_wait_times_out_without_events(self):
        run = Run(self)
        run.agent("coord", "working", WORKING_TEXT)
        run.register("coord")
        run.sweep(now=1000)
        result = run.wait(now=1001)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "TIMEOUT")


class LifecycleTests(unittest.TestCase):
    INTERVAL = "0.2"

    def until(self, check, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if check():
                return True
            time.sleep(0.05)
        return False

    def test_one_watcher_per_run_and_stop_ends_only_this_one(self):
        first, second = Run(self), Run(self)
        for run in (first, second):
            run.agent("coord", "working", WORKING_TEXT)
            run.register("coord")
        a = first.start("--interval", self.INTERVAL)
        b = second.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: first.status()["watcher"]["alive"] and second.status()["watcher"]["alive"]))
        duplicate = first.cli("run", "--interval", self.INTERVAL, timeout=10)
        self.assertEqual(duplicate.stdout.strip().split()[0], "ALREADY_RUNNING", duplicate.stdout)
        stopped = first.cli("stop", timeout=10)
        self.assertIn("STOPPED", stopped.stdout)
        self.assertEqual(a.wait(timeout=5), 0)
        self.assertFalse(first.status()["watcher"]["alive"])
        self.assertIsNone(b.poll(), "stopping one run's watcher stopped another's")
        self.assertTrue(second.status()["watcher"]["alive"])

    def test_stop_is_safe_when_no_watcher_runs(self):
        run = Run(self)
        fresh = run.cli("stop", timeout=10)
        self.assertEqual((fresh.returncode, fresh.stdout.strip()), (0, "NOT_RUNNING"), "stop fails on a fresh run")
        run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["watcher"]["alive"]))
        run.cli("stop", timeout=10)
        again = run.cli("stop", timeout=10)
        self.assertEqual((again.returncode, again.stdout.strip()), (0, "NOT_RUNNING"), "a second stop fails")

    def test_status_reports_identity_heartbeat_and_pending_count(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["counts"]["pending"] == 1), "the running watcher found nothing")
        watcher = run.status()["watcher"]
        self.assertRegex(watcher["instance"], r"^[0-9a-f]{8}$")
        self.assertLessEqual(watcher["started_at"], time.time())
        self.assertLess(watcher["heartbeat_age"], 2)
        self.assertTrue(watcher["alive"])

    def test_the_run_log_carries_no_prompt_text(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        watcher = run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["counts"]["pending"] == 1))
        run.cli("stop", timeout=10)
        log = watcher.communicate(timeout=5)[0]
        self.assertRegex(log, r"(?m)^EVENT \S+ worker=coord item=item-a role=coordinator kind=blocked$",
                         "the run log's EVENT line differs from wait's")
        self.assertNotIn(SECRET, log, "prompt text leaked into watcher.log")
        self.assertNotIn("curl", log, "prompt text leaked into watcher.log")

    def test_a_crashed_watcher_is_reported_and_replaced_without_losing_events(self):
        run = Run(self)
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        run.register("coord")
        crashed = run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["counts"]["pending"] == 1))
        old = run.status()["watcher"]["instance"]
        crashed.send_signal(signal.SIGKILL)
        crashed.wait()
        self.assertTrue(self.until(lambda: not run.status()["watcher"]["alive"]), "a dead watcher still looks alive")
        stale = run.cli("wait", timeout=10)
        self.assertIn("WATCHER stale", stale.stdout, "a waiting manager is never told its watcher died")
        reads_before = len(run.reads())
        run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["watcher"]["alive"]))
        self.assertNotEqual(run.status()["watcher"]["instance"], old)
        self.assertTrue(self.until(lambda: len(run.reads()) >= reads_before + 2),
                        "the replacement watcher never swept")
        self.assertEqual([e["state"] for e in run.events()], ["pending"], "a restart lost or duplicated the pending event")
        first = run.events()[0]["id"]
        run.agent("coord", "blocked", CLAUDE_PROMPT, session="ses-new")
        self.assertTrue(self.until(lambda: {e["id"]: e["state"] for e in run.events()}.get(first) == "superseded"),
                        "the replacement watcher does not record what it sees")
        self.assertEqual(len(run.events("pending")), 1)

    def test_a_real_wait_blocks_until_an_event_and_honors_its_timeout(self):
        run = Run(self)
        run.agent("coord", "working", WORKING_TEXT)
        run.register("coord")
        run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["watcher"]["alive"]))
        started = time.monotonic()
        idle = run.cli("wait", "--timeout", "1", timeout=10)
        self.assertEqual((idle.returncode, idle.stdout.strip()), (2, "TIMEOUT"), "a quiet run did not time out")
        self.assertGreaterEqual(time.monotonic() - started, 1, "wait gave up before its timeout")
        waiting = subprocess.Popen([sys.executable, str(WATCHER), "wait", "--run-dir", str(run.dir)],
                                   stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: waiting.poll() is None and waiting.kill())
        time.sleep(0.5)
        self.assertIsNone(waiting.poll(), "wait returned with nothing due")
        run.agent("coord", "blocked", CLAUDE_PROMPT)
        out, _ = waiting.communicate(timeout=5)
        self.assertEqual(waiting.returncode, 0)
        self.assertRegex(out, r"(?m)^EVENT \S+ worker=coord item=item-a role=coordinator kind=blocked$",
                         "a blocking wait never woke for the new prompt")

    def test_a_superseded_watcher_exits_instead_of_competing(self):
        run = Run(self)
        run.agent("coord", "working", WORKING_TEXT)
        run.register("coord")
        paused = run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["watcher"]["alive"]))
        paused.send_signal(signal.SIGSTOP)
        self.assertTrue(self.until(lambda: not run.status()["watcher"]["alive"]))
        run.start("--interval", self.INTERVAL)
        self.assertTrue(self.until(lambda: run.status()["watcher"]["alive"]))
        paused.send_signal(signal.SIGCONT)
        self.assertEqual(paused.wait(timeout=5), 0)
        self.assertIn("SUPERSEDED", paused.stdout.read())

    def test_unregistered_workers_are_no_longer_polled(self):
        run = Run(self)
        run.agent("coord", "working", WORKING_TEXT)
        run.register("coord")
        run.cli("unregister", "--name", "coord")
        run.sweep(now=1000)
        self.assertEqual(run.calls(), [], "a closed worker is still polled")

    def test_an_observation_in_flight_across_unregister_is_dropped(self):
        for reregister in (False, True):
            with self.subTest(reregister=reregister):
                run = Run(self)
                run.agent("coord", "blocked", CLAUDE_PROMPT, sleep=0.6)
                run.register("coord")
                sweep = subprocess.Popen([sys.executable, str(WATCHER), "sweep", "--run-dir", str(run.dir),
                                          "--herdr", str(run.herdr), "--now", "1000"],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertTrue(self.until(lambda: any(c.startswith("agent get") for c in run.calls())))
                run.cli("unregister", "--name", "coord")
                if reregister:
                    run.register("coord", item="item-b")
                sweep.communicate(timeout=10)
                self.assertEqual(run.events(), [], "a torn-down worker's late observation raised an event")

    def test_a_newer_store_is_refused_not_reset(self):
        run = Run(self)
        run.register("coord")
        with sqlite3.connect(run.dir / "watcher.sqlite3") as db:
            db.execute("PRAGMA user_version = 99")
        result = run.cli("status")
        self.assertEqual(result.returncode, 3, "a refused store does not exit 3")
        self.assertIn("SCHEMA", result.stdout + result.stderr)

    def test_a_corrupt_or_missing_store_exits_3_and_names_its_path(self):
        run = Run(self)
        (run.dir / "watcher.sqlite3").write_bytes(b"not a database" * 100)
        corrupt = run.cli("status")
        self.assertEqual(corrupt.returncode, 3, corrupt.stdout + corrupt.stderr)
        self.assertRegex(corrupt.stdout, rf"^STORE_ERROR {re.escape(str(run.dir / 'watcher.sqlite3'))}: ")
        missing = subprocess.run([sys.executable, str(WATCHER), "status", "--run-dir", str(run.dir / "no-such-dir")],
                                 capture_output=True, text=True)
        self.assertEqual(missing.returncode, 3, missing.stdout + missing.stderr)
        self.assertIn("no-such-dir", missing.stdout)


def flat(text):
    """Collapse whitespace so a rule wrapped across lines still matches."""
    return " ".join(text.split())


def section(text, heading):
    found = re.search(rf"(?ms)^## {heading}\n.*?(?=^## |\Z)", text)
    if not found:
        raise AssertionError(f"no '## {heading}' section")
    return found.group(0)


class StatusLineInventoryTests(unittest.TestCase):
    def test_agents_md_lists_every_line_the_watcher_prints(self):
        source = WATCHER.read_text(encoding="utf-8")
        printed = set(re.findall(r'(?:print\(f?|append\()"([A-Z][A-Z_]+)', source))
        printed |= {"EVENT", "RESOLVED", "AWAITING_USER"}  # built by event_line and settle's state.upper()
        agents = flat((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        inventory = re.search(r"`(START\|[^`]+)` lines from watch-workers\.py", agents)
        self.assertIsNotNone(inventory, "AGENTS.md lost the watcher's status-line inventory")
        listed = set(re.findall(r"[A-Z][A-Z_]+", inventory.group(1)))
        self.assertEqual(printed - listed, set(), "AGENTS.md omits status lines the watcher prints")


class ProseContractTests(unittest.TestCase):
    """The manager's side: the watcher is started, drained, and kept healthy."""

    def read(self, relative):
        return (MANAGER / relative).read_text(encoding="utf-8")

    def expect(self, label, text, pattern, why):
        if not re.search(pattern, flat(text)):
            self.fail(f"{label}: {why} — nothing matched {pattern!r}")

    def watch(self):
        return section(self.read("references/herdr.md"), "Watch for prompts")

    def test_the_watcher_starts_before_the_first_worker(self):
        self.expect("SKILL.md", self.read("SKILL.md"), r"(?i)references/herdr\.md`, starting its prompt watcher before the first worker",
                    "workers can start before anything watches them")
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)start it before the first worker",
                    "the start step lost its ordering")
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)register every worker.{0,120}helpers and replacements",
                    "helpers or replacement workers go unwatched")

    def test_every_command_the_prose_names_exists(self):
        named = set(re.findall(r"<watcher> ([a-z-]+)", flat(self.watch() + self.read("references/console.md"))))
        named |= set(re.findall(r"\(`([a-z-]+) --name`\)", self.watch()))
        self.assertTrue(named, "the prose names no watcher command")
        usage = subprocess.run([sys.executable, str(WATCHER), "--help"], capture_output=True, text=True).stdout
        offered = set(re.search(r"\{([a-z,-]+)\}", usage).group(1).split(","))
        self.assertLessEqual(named, offered, f"the prose names commands the script lacks: {sorted(named - offered)}")

    def test_the_manager_claims_rereads_and_verifies(self):
        steps = flat(self.watch())
        order = [steps.find(word) for word in ("claim --event", "Re-read the current prompt", "resolve --event")]
        self.assertTrue(all(i >= 0 for i in order) and order == sorted(order),
                        "the handling steps are missing or out of order: claim, re-read, answer, resolve")
        self.expect("herdr.md § Watch for prompts", steps, r"NOT_CLAIMABLE.{0,80}ignore it",
                    "a late or duplicate notice can trigger a second answer")
        self.expect("herdr.md § Watch for prompts", steps, r"STALE_TOKEN.{0,120}claim it again.{0,80}without sending anything again",
                    "a lapsed claim has no remedy, inviting a second answer")
        self.expect("herdr.md § Watch for prompts", steps, r"(?i)new event.{0,80}never by repeating keys",
                    "a confirmation dialog can be answered by replaying keys")
        self.expect("herdr.md § Watch for prompts", steps, r"await-user.{0,120}without further notices",
                    "a prompt waiting on the user keeps nagging or drops off the board")
        self.expect("console.md § The loop", section(self.read("references/console.md"), "The loop"),
                    r"(?i)drain the watcher's events first, whether or not it woke you",
                    "a manager that resumes on its own leaves pending events")

    def test_the_watcher_only_detects_and_policy_stays_the_managers(self):
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)only detects and notifies",
                    "the watcher's role grew past detection")
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)§ Approvals, unchanged",
                    "the approval policy is no longer the manager's")
        self.expect("herdr.md § Watch for prompts", self.watch(),
                    r"(?i)only `herdr agent get` and `herdr agent read` and never writes to a terminal",
                    "the watcher may type into a terminal")

    def test_the_delivery_blocker_is_stated(self):
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)protocol 22\) has no queued or idle-conditional delivery",
                    "the Herdr integration blocker is no longer documented")
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)wake-up is only as reliable as the host",
                    "the docs claim reliable wake-ups")

    def test_health_restart_and_stop_are_run_scoped(self):
        board = section(self.read("references/console.md"), "The board")
        self.assertRegex(board, r"watcher <instance> · heartbeat <age>s · pending <N>",
                         "the board header lost the watcher's identity, heartbeat or pending count")
        self.expect("herdr.md § Watch for prompts", self.watch(), r"(?i)never re-prompts a worker or resends a brief",
                    "watcher recovery may resend task briefs")
        self.expect("console.md § Ending the session", section(self.read("references/console.md"), "Ending the session"),
                    r"(?i)stop this run's watcher.{0,80}never stops another run's", "ending may stop another run's watcher")
        self.expect("console.md § Native subagents", section(self.read("references/console.md"), "Native subagents"),
                    r"(?i)no watcher runs.{0,120}claim no continuous monitoring",
                    "native runs claim monitoring they do not have")


if __name__ == "__main__":
    unittest.main()
