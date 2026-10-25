#!/usr/bin/env python3
"""Exercise run_evals.py's transcript parsing offline, on synthetic transcripts.

The eval runner reads `claude -p --output-format stream-json` output, one JSON
event per line. These tests hold the parsing contract without Claude,
credentials, or network: `parse_transcript` keeps the text and skill set the
runner has always graded on, and `run_agent` keeps its command, timeout, and
error mapping. `subprocess.run` is mocked; no agent is ever started.

Every transcript fixture is defined once, in TRANSCRIPTS below. Any other
harness that needs these shapes imports this module rather than copying them.
"""

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "run_evals.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_evals", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()


def jsonl(*events):
    """One stream-json transcript: each event a line, raw strings kept as-is."""
    return "\n".join(e if isinstance(e, str) else json.dumps(e) for e in events)


def assistant(*blocks, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"role": "assistant", "content": list(blocks)}}


def text(body):
    return {"type": "text", "text": body}


def tool_use(name, tool_id, **tool_input):
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


def tool_result(tool_id, is_error=None, parent=None):
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}
    if is_error is not None:
        block["is_error"] = is_error
    return {"type": "user", "parent_tool_use_id": parent,
            "message": {"role": "user", "content": [block]}}


def result(body):
    return {"type": "result", "subtype": "success", "result": body}


SYSTEM_INIT = {"type": "system", "subtype": "init", "tools": ["Agent", "Skill"]}

TRANSCRIPTS = {
    "empty": "",
    "text_only": jsonl(
        SYSTEM_INIT,
        assistant(text("I delegated to three planners in parallel.")),
        result("Done: the team finished."),
    ),
    "malformed_only": jsonl("not json", "{\"type\": ", "", "5", "[1, 2]", "null"),
    "parser_mix": jsonl(
        SYSTEM_INIT,
        "this line is not json",
        "",
        assistant(text("first"), tool_use("Bash", "t1", command="ls"), text("second")),
        {"type": "user", "message": {"content": [{"type": "text", "text": "ignored"}]}},
        {"type": "stream_event", "event": {"text": "ignored too"}},
        assistant(
            tool_use("Skill", "t2", skill="agents-library:review-pr"),
            tool_use("Skill", "t3", skill="plan-feature"),
            tool_use("Skill", "t4", skill="agents-library:review-pr"),
        ),
        result("final answer"),
    ),
    "empty_result": jsonl(assistant(text("only text")), result("")),
    # A team: two planners launched in one message, their own events tagged
    # with the launching call's id, then a reviewer launched alone.
    "delegated": jsonl(
        SYSTEM_INIT,
        assistant(
            text("Launching planners."),
            tool_use("Agent", "a1", subagent_type="Plan", description="plan A",
                     prompt="secret prompt text", run_in_background=True),
            tool_use("Agent", "a2", subagent_type="Plan", description="plan B",
                     prompt="secret prompt text", run_in_background=True),
        ),
        assistant(tool_use("Read", "s1", file_path="run_evals.py"), parent="a1"),
        tool_result("s1", parent="a1"),
        assistant(tool_use("Grep", "s2", pattern="x"), parent="a2"),
        tool_result("a1"),
        tool_result("a2"),
        assistant(tool_use("Agent", "a3", subagent_type="general-purpose",
                           description="review", prompt="review it")),
        tool_result("a3"),
        result("Plans merged and reviewed."),
    ),
    # One agent doing everything itself, one tool per turn.
    "self_executed": jsonl(
        SYSTEM_INIT,
        assistant(tool_use("Read", "r1", file_path="run_evals.py")),
        tool_result("r1"),
        assistant(tool_use("Edit", "e1", file_path="run_evals.py")),
        tool_result("e1"),
        assistant(tool_use("Bash", "b1", command="bash scripts/check.sh")),
        tool_result("b1"),
        assistant(text("I delegated to three planners in parallel.")),
        result("Done: the team finished."),
    ),
    # The pre-rename tool name still marks a launch.
    "legacy_task": jsonl(
        assistant(tool_use("Task", "k1", subagent_type="Explore", prompt="look")),
        tool_result("k1"),
    ),
    # Every launch was refused, so the agent did the work itself.
    "failed_launch": jsonl(
        assistant(tool_use("Agent", "f1", subagent_type="Plan", prompt="p")),
        tool_result("f1", is_error=True),
        assistant(tool_use("Edit", "e1", file_path="a.py")),
        tool_result("e1"),
    ),
    # Valid JSON in the wrong shape must be skipped, not crash the parser.
    "wrong_shapes": jsonl(
        {"type": "assistant", "message": "not a dict"},
        {"type": "assistant", "message": {"content": "not a list"}},
        {"type": "assistant", "message": {"content": ["not a block", 3]}},
        {"type": "user", "message": {"content": [{"type": "tool_result"}]}},
        assistant(text("survivor")),
    ),
}


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(["claude"], returncode, stdout, stderr)


class ParseTranscriptTests(unittest.TestCase):
    def test_joins_assistant_and_result_text_in_order(self):
        output, _ = runner.parse_transcript(TRANSCRIPTS["parser_mix"])
        self.assertEqual(output, "first\nsecond\nfinal answer")

    def test_strips_skill_namespaces_into_a_set(self):
        _, skills = runner.parse_transcript(TRANSCRIPTS["parser_mix"])
        self.assertEqual(skills, {"review-pr", "plan-feature"})

    def test_skips_malformed_lines_and_non_object_json(self):
        self.assertEqual(runner.parse_transcript(TRANSCRIPTS["malformed_only"]), ("", set()))

    def test_ignores_system_user_and_unknown_events(self):
        output, _ = runner.parse_transcript(TRANSCRIPTS["parser_mix"])
        self.assertNotIn("ignored", output)

    def test_empty_result_adds_no_line(self):
        self.assertEqual(runner.parse_transcript(TRANSCRIPTS["empty_result"]),
                         ("only text", set()))

    def test_empty_transcript(self):
        self.assertEqual(runner.parse_transcript(""), ("", set()))

    def test_wrong_shaped_events_are_skipped(self):
        self.assertEqual(runner.parse_transcript(TRANSCRIPTS["wrong_shapes"]),
                         ("survivor", set()))

    def test_skill_without_name_records_empty_string(self):
        stdout = jsonl(assistant(tool_use("Skill", "t1")))
        self.assertEqual(runner.parse_transcript(stdout), ("", {""}))


class DelegationTraceTests(unittest.TestCase):
    def trace(self, name):
        return runner.parse_delegation_trace(TRANSCRIPTS[name])

    def test_delegated_team_records_launches_batches_and_subagent_events(self):
        trace = self.trace("delegated")
        self.assertEqual(trace["verdict"], "delegated")
        self.assertEqual(trace["max_launch_batch"], 2)
        self.assertEqual(trace["subagent_events"], 3)
        self.assertEqual(trace["launches"], [
            {"name": "Agent", "message": 0, "tool_use_id": "a1",
             "subagent_type": "Plan", "run_in_background": True},
            {"name": "Agent", "message": 0, "tool_use_id": "a2",
             "subagent_type": "Plan", "run_in_background": True},
            {"name": "Agent", "message": 1, "tool_use_id": "a3",
             "subagent_type": "general-purpose"},
        ])
        # Sub-agents' own tools are not counted as the top-level agent's.
        self.assertEqual(trace["tool_counts"], {"Agent": 3})

    def test_self_executed_run_is_distinguishable_from_a_team(self):
        team, alone = self.trace("delegated"), self.trace("self_executed")
        self.assertEqual(alone["verdict"], "self-executed")
        self.assertEqual(alone["launches"], [])
        self.assertEqual(alone["max_launch_batch"], 0)
        self.assertEqual(alone["subagent_events"], 0)
        self.assertEqual(alone["tool_counts"], {"Read": 1, "Edit": 1, "Bash": 1})
        self.assertNotEqual(team, alone)

    def test_legacy_task_name_is_a_launch(self):
        trace = self.trace("legacy_task")
        self.assertEqual(trace["verdict"], "delegated")
        self.assertEqual(trace["launches"][0]["name"], "Task")

    def test_a_refused_launch_is_not_a_team(self):
        trace = self.trace("failed_launch")
        self.assertEqual(trace["verdict"], "self-executed")
        self.assertIs(trace["launches"][0]["error"], True)

    def test_missing_evidence_is_unknown(self):
        for name in ("empty", "text_only", "malformed_only", "wrong_shapes"):
            with self.subTest(name):
                self.assertEqual(self.trace(name), runner.unknown_trace())

    def test_prose_claiming_delegation_is_not_evidence(self):
        self.assertEqual(self.trace("text_only")["verdict"], "unknown")
        self.assertEqual(self.trace("self_executed")["verdict"], "self-executed")

    def test_trace_keeps_no_prompt_or_description(self):
        dumped = json.dumps(self.trace("delegated"))
        for leaked in ("secret prompt text", "plan A", "review it", "Launching"):
            self.assertNotIn(leaked, dumped)


class RunAgentTests(unittest.TestCase):
    def run_agent(self, side_effect):
        with mock.patch.object(runner.subprocess, "run", side_effect=side_effect) as run:
            got = runner.run_agent(Path("/tmp/ws"), "do it", "haiku", 42, True)
        return got, run

    def test_success_returns_parsed_transcript(self):
        (output, skills, trace, err), run = self.run_agent(
            [completed(TRANSCRIPTS["parser_mix"])])
        self.assertEqual((output, skills, err),
                         ("first\nsecond\nfinal answer", {"review-pr", "plan-feature"}, ""))
        self.assertEqual(trace["verdict"], "self-executed")
        self.assertEqual(run.call_args.args[0], [
            "claude", "-p", "do it", "--output-format", "stream-json", "--verbose",
            "--dangerously-skip-permissions", "--setting-sources", "project",
            "--model", "haiku",
        ])
        self.assertEqual(run.call_args.kwargs["timeout"], 42)

    def test_nonzero_exit_keeps_output_and_reports_stderr_tail(self):
        (output, _, _, err), _ = self.run_agent(
            [completed(TRANSCRIPTS["empty_result"], 2, "x" * 600 + "boom")])
        self.assertEqual(output, "only text")
        self.assertEqual(err, "claude exited 2: " + ("x" * 600 + "boom")[-500:])

    def test_timeout(self):
        got, _ = self.run_agent(subprocess.TimeoutExpired("claude", 42))
        self.assertEqual(got, ("", set(), runner.unknown_trace(), "timeout"))

    def test_missing_cli(self):
        got, _ = self.run_agent(FileNotFoundError("claude"))
        self.assertEqual(got, ("", set(), runner.unknown_trace(),
                               "claude CLI not found on PATH"))


class RunCaseTests(unittest.TestCase):
    """--trace adds telemetry to each trial and changes nothing that is graded."""

    SUITE = {"skill": "manager"}
    CASE = {"id": "mg-x", "prompt": "run the team", "should_trigger": True,
            "assertions": [{"type": "output_regex", "pattern": "merged"}]}
    GRADED = ("passed", "failures", "skills_used", "trigger_ok", "output_tail")

    def run_case(self, trace, side_effect, trials=1):
        args = mock.Mock(trials=trials, build_only=False, model=None, timeout=None,
                         keep_workspaces=False, trace=trace)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runner, "build_workspace",
                                  side_effect=lambda *a: Path(tempfile.mkdtemp(dir=tmp))), \
                mock.patch.object(runner.subprocess, "run", side_effect=side_effect):
            return runner.run_case(args, Path(tmp), self.SUITE, self.CASE, [], True)

    def test_trace_flag_leaves_graded_fields_identical(self):
        stdout = TRANSCRIPTS["delegated"]
        [off] = self.run_case(False, [completed(stdout)])
        [on] = self.run_case(True, [completed(stdout)])
        self.assertNotIn("trace", off)
        self.assertEqual({k: on[k] for k in self.GRADED}, {k: off[k] for k in self.GRADED})
        self.assertEqual(on["trace"], runner.parse_delegation_trace(stdout))

    def test_each_trial_keeps_its_own_trace(self):
        trials = self.run_case(True, [completed(TRANSCRIPTS["delegated"]),
                                      completed(TRANSCRIPTS["self_executed"])], trials=2)
        self.assertEqual([t["trace"]["verdict"] for t in trials],
                         ["delegated", "self-executed"])

    def test_timed_out_trial_traces_unknown_and_still_fails(self):
        [trial] = self.run_case(True, subprocess.TimeoutExpired("claude", 1))
        self.assertEqual(trial["trace"], runner.unknown_trace())
        self.assertFalse(trial["passed"])
        self.assertIn("agent-error: timeout", trial["failures"])

    def test_build_only_records_no_trace(self):
        args = mock.Mock(trials=1, build_only=True, trace=True)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runner, "build_workspace", return_value=Path(tmp)), \
                mock.patch.object(runner.subprocess, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()):
            [trial] = runner.run_case(args, Path(tmp), self.SUITE, self.CASE, [], True)
        run.assert_not_called()
        self.assertEqual(trial, {"workspace": tmp, "built": True})


if __name__ == "__main__":
    unittest.main()
