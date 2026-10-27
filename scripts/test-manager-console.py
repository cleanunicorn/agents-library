#!/usr/bin/env python3
"""Check that the manager stays a console for every message after it starts.

A manager that follows its rules only on the turn that loaded it drifts back
to a plain session one message later: it answers a question by reading code
itself, runs a skill the user invokes in its own context, or starts an ad hoc
agent natively while every other worker runs in a Herdr tab. A context
summary makes this worse, since it can drop SKILL.md entirely. These checks
hold the rule that the mode persists, the per-turn re-check that survives a
summary, the board header that records the mode and transport, and the helper
role that gives non-change requests somewhere to go other than the manager.
They also hold the output budget: one paragraph, defined in console.md and
carried word for word by every brief, so a worker that dumps a gate log or a
whole file into its context is breaking a rule it was given, and the copies
cannot drift apart.

The patterns match load-bearing words, not prose ornament, so a copy-edit
that keeps the rule keeps these green.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANAGER = ROOT / "skills" / "manager"


def flat(text):
    """Collapse whitespace so a rule wrapped across lines still matches."""
    return " ".join(text.split())


def section(text, heading):
    """Return one `## heading` section, up to the next one."""
    found = re.search(rf"(?ms)^## {heading}\n.*?(?=^## |\Z)", text)
    if not found:
        raise AssertionError(f"no '## {heading}' section")
    return found.group(0)


def rule(text, number):
    """Return one numbered rule from SKILL.md's Rules list."""
    found = re.search(rf"(?ms)^{number}\. .*?(?=^\d+\. |^## )", text)
    if not found:
        raise AssertionError(f"SKILL.md has no rule {number}")
    return found.group(0)


class ManagerConsoleTests(unittest.TestCase):
    def read(self, relative):
        return (MANAGER / relative).read_text(encoding="utf-8")

    def expect(self, label, text, pattern, why):
        if not re.search(pattern, flat(text)):
            self.fail(f"{label}: {why} — nothing matched {pattern!r}")

    def test_the_console_persists_across_messages(self):
        persists = rule(self.read("SKILL.md"), 10)
        label = "SKILL.md rule 10"
        self.expect(label, persists, r"\*\*The console persists\.\*\*", "the persistence rule lost its name")
        self.expect(label, persists, r"(?i)every later message is a console turn",
                    "later messages are no longer bound to the console")
        self.expect(label, persists, r"(?i)whether or not it names the manager",
                    "a message that does not mention the manager escapes the console")
        self.expect(label, persists, r"(?i)every agent you start — ad hoc ones too — runs on the recorded transport",
                    "an ad hoc agent may start outside the recorded transport")
        self.expect(label, persists, r"(?i)\"just do it yourself\" does not end the console",
                    "a request to work directly ends the console")
        self.expect(label, persists, r"(?i)after a context summary, re-read this file and the board",
                    "a summary that drops SKILL.md drops the mode with it")

    def test_transport_is_decided_once_and_recorded(self):
        line = section(self.read("SKILL.md"), "Where the line sits")
        self.expect("SKILL.md § Where the line sits", line,
                    r"(?i)decide once.{0,80}board header.{0,120}every worker this session starts uses that transport",
                    "the transport is re-chosen per worker, so an ad hoc one can go native")

    def test_the_board_header_records_mode_and_transport(self):
        board = section(self.read("references/console.md"), "The board")
        header = re.search(r"(?m)^console: manager · .*$", board)
        self.assertIsNotNone(header, "console.md § The board has no console header sample")
        for field in ("skill <absolute path to SKILL.md>", "transport herdr", "native", "run_dir"):
            with self.subTest(field=field):
                self.assertIn(field, header.group(0), f"the console header lost `{field}`")
        self.expect("console.md § The board", board, r"(?i)kept on every rewrite",
                    "a board rewrite can drop the header")

    def test_every_turn_starts_by_checking_the_console(self):
        loop = section(self.read("references/console.md"), "The loop")
        self.assertRegex(loop, r"(?m)^0\. \*\*Still the console\*\*", "the loop no longer starts with the console check")
        self.expect("console.md § The loop", loop, r"(?i)context summary.{0,80}re-read both from the header's `skill` path",
                    "a summarized session never reloads the skill")
        self.expect("console.md § The loop", loop, r"(?i)start every worker on the header's `transport`",
                    "workers started later ignore the recorded transport")
        self.expect("console.md § The loop", loop, r"(?i)whatever it says and whether or not it names the manager",
                    "a message unrelated to the manager is handled outside the loop")
        self.expect("console.md § The loop", loop, r"(?i)skill the user invokes now.{0,120}a helper",
                    "a later skill invocation runs in the console's own context")

    def test_helpers_are_read_only_workers_on_the_transport(self):
        helpers = section(self.read("references/console.md"), "Helpers")
        label = "console.md § Helpers"
        self.expect(label, helpers, r"(?i)\*\*one helper\*\*", "a non-change request has no worker to go to")
        self.expect(label, helpers, r"(?i)read-only grant.{0,120}on the recorded transport",
                    "a helper launches without the read-only grant or off-transport")
        self.expect(label, helpers, r"(?i)write access only to the run directory", "a helper may write the repository")
        self.expect(label, helpers, r"(?i)never edits", "a helper may make the change itself")
        self.expect("herdr.md", self.read("references/herdr.md"),
                    r"(?i)a helper launches with the planner, reviewer column",
                    "Herdr launches a helper with the coordinator's grant")

    def test_only_the_user_ends_the_console(self):
        ending = section(self.read("references/console.md"), "Ending the session")
        self.expect("console.md § Ending the session", ending, r"(?i)ends only when the user ends it in words",
                    "something other than the user can end the console")
        self.expect("console.md § Ending the session", ending, r"(?i)does not end it \(SKILL\.md rule 10\)",
                    "the ending section no longer points back at the persistence rule")

    def test_every_worker_carries_the_same_output_budget(self):
        def budget(text, label):
            found = re.search(r"(?ms)^\*\*Output budget\.\*\*.*?(?=\n\n)", text)
            if not found:
                self.fail(f"{label}: no **Output budget.** paragraph")
            return flat(found.group(0))

        canonical = budget(self.read("references/console.md"), "console.md")
        for pattern, why in [
            (r"> <log> 2>&1", "growing output is no longer sent to a file"),
            (r"tail -n \d+", "logs are no longer read back with tail"),
            (r"grep -n", "files are no longer searched before reading"),
            (r"never `cat` it whole", "whole-file reads are allowed again"),
        ]:
            self.expect("console.md § Output budget", canonical, pattern, why)
        self.assertEqual(budget(self.read("references/worker-common.md"), "worker-common.md"), canonical,
                         "worker-common.md: the output budget drifted from console.md")
        for brief in ["coordinator-brief.md", "planner-brief.md", "reviewer-brief.md", "implementer-brief.md"]:
            self.expect(brief, self.read(f"references/{brief}"), r"Read `worker-common\.md` first",
                        "a brief no longer points at the shared worker contract carrying the output budget")
        self.expect("console.md § Helpers", section(self.read("references/console.md"), "Helpers"),
                    r"§ Output budget paragraph", "a helper's brief omits the output budget")
        self.expect("SKILL.md rule 9", rule(self.read("SKILL.md"), 9), r"§ Output budget",
                    "the manager's own rule no longer bounds its commands")


if __name__ == "__main__":
    unittest.main()
