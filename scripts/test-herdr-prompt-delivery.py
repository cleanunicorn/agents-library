#!/usr/bin/env python3
"""Check that every Herdr transport confirms a prompt reached its worker.

A prompt sent without `--wait` returns as soon as the text is written to the
pane. A freshly started agent can still be drawing its input box then, so the
text is dropped and the worker sits `idle` while the caller waits on it for
good (issue #66). `herdr agent prompt --wait` closes that: it fails with
`agent_prompt_stalled` unless the agent leaves `idle` soon after submission.
A short `--timeout` keeps the console responsive; completion is waited for in
the background. These checks hold that gate, the single re-prompt for a
worker still `idle`, and the rule that a timeout after activity is not a
reason to send again — in every skill's Herdr reference, since each skill
installs on its own.

The patterns match load-bearing words, not prose ornament, so a copy-edit
that keeps the rule keeps these green.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REFERENCES = sorted(ROOT.glob("skills/*/references/herdr.md"))
EXPECTED = {"manager", "batch-merge-prs"}

# What a prompt procedure must say, each with the reason it matters.
REQUIRED = [
    (r"agent prompt [^.]*--wait --timeout",
     "prompt through the short delivery gate"),
    (r"leav\w* `idle`",
     "delivery is confirmed by the agent leaving `idle`"),
    (r"`working` or `blocked`",
     "name the activity that proves delivery"),
    (r"background[^.]*`herdr agent wait <name>`|`herdr agent wait <name>`[^.]*background",
     "wait for completion in the background, not in the gate"),
    (r"`agent_prompt_stalled`",
     "a stalled gate is the non-delivery signal"),
    (r"still `idle`[^.]*\bread\b[^.]*re-prompt once",
     "still idle: read the pane, then re-prompt once"),
    (r"timeout after activity is not a reason",
     "a timeout after activity never triggers a resend"),
]

# An unconditional instruction to prompt without the gate must not return.
FORBIDDEN = re.compile(r"prompt[^.]*\b(without|no)\s+`--wait`", re.IGNORECASE)


def flat(text):
    """Collapse whitespace so a rule wrapped across lines still matches."""
    return " ".join(text.split())


def problems(text):
    """Return every way a Herdr reference breaks the delivery contract."""
    found = []
    body = flat(text)
    for pattern, why in REQUIRED:
        if not re.search(pattern, body):
            found.append(f"{why} — nothing matched {pattern!r}")
    if FORBIDDEN.search(body):
        found.append("prompts without `--wait`")
    return found


class HerdrPromptDeliveryTests(unittest.TestCase):
    def test_every_skill_with_herdr_is_covered(self):
        skills = {path.parent.parent.name for path in REFERENCES}
        self.assertTrue(EXPECTED <= skills, f"missing: {EXPECTED - skills}")

    def test_each_reference_gates_prompt_delivery(self):
        for path in REFERENCES:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(problems(path.read_text(encoding="utf-8")), [])

    def test_checker_catches_regressions(self):
        """The checker must fail on the shapes that let #66 through."""
        good = (ROOT / "skills/manager/references/herdr.md").read_text(encoding="utf-8")
        mutations = {
            "old no-wait bullet back": good + "\n- Prompt without `--wait`, then wait.\n",
            "gate removed": good.replace("--wait --timeout", "--timeout"),
            "retry unbounded": flat(good).replace("re-prompt once", "re-prompt"),
            "resend after activity": flat(good).replace(
                "timeout after activity is not a reason", "timeout is a reason"),
        }
        for label, text in mutations.items():
            with self.subTest(mutation=label):
                self.assertNotEqual(problems(text), [], "mutation went unnoticed")


if __name__ == "__main__":
    unittest.main()
