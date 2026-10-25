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
    (r"shows no turn started[^.]*re-prompt once",
     "re-prompt only when the pane shows no turn started"),
    (r"timeout after activity is not a reason",
     "a timeout after activity never triggers a resend"),
]

# Where a second missed delivery goes: each skill installs on its own, so
# the manager hands it to its member-failure rule and batch-merge to its own
# fallback.
SECOND_MISS = {
    "manager": (r"second miss is a member that fails \(SKILL\.md rule 8\)",
                "is a member that fails (SKILL.md rule 8)"),
    "batch-merge-prs": (r"second miss fails that worker: use § Fallback",
                        "fails that worker: use § Fallback"),
}

# An unconditional instruction to prompt without the gate must not return.
FORBIDDEN = re.compile(r"prompt[^.]*\b(without|no)\s+`--wait`", re.IGNORECASE)


def flat(text):
    """Collapse whitespace so a rule wrapped across lines still matches."""
    return " ".join(text.split())


def problems(text, skill):
    """Return every way a Herdr reference breaks the delivery contract."""
    found = []
    body = flat(text)
    second_miss, _ = SECOND_MISS.get(skill, (r"second miss fails", ""))
    required = REQUIRED + [(second_miss, "a second missed delivery fails the worker")]
    for pattern, why in required:
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
                text = path.read_text(encoding="utf-8")
                self.assertEqual(problems(text, path.parent.parent.name), [])

    def test_checker_catches_regressions(self):
        """The checker must fail on the shapes that let #66 through."""
        for skill in sorted(EXPECTED):
            good = flat((ROOT / "skills" / skill / "references/herdr.md")
                        .read_text(encoding="utf-8"))
            mutations = {
                "old no-wait bullet back": good + " - Prompt without `--wait`, then wait.",
                "gate removed": good.replace("--wait --timeout", "--timeout"),
                "retry unbounded": good.replace("re-prompt once", "re-prompt"),
                "resend after activity": good.replace(
                    "timeout after activity is not a reason", "timeout is a reason"),
                "no-turn condition dropped": good.replace(
                    "if it shows no turn started, re-prompt", "re-prompt"),
                "second miss ignored": good.replace(
                    SECOND_MISS[skill][1], "is waited on"),
            }
            for label, text in mutations.items():
                with self.subTest(skill=skill, mutation=label):
                    self.assertNotEqual(text, good, "mutation changed nothing")
                    self.assertNotEqual(problems(text, skill), [], "mutation went unnoticed")


if __name__ == "__main__":
    unittest.main()
