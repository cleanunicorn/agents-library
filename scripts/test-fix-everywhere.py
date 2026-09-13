#!/usr/bin/env python3
"""Check that every definition which fixes code also fixes every other instance.

When an agent or skill fixes a problem, it must search the whole repository for
the same problem and fix the other instances in the same PR. These checks fail
if a definition drops that step or slips back to a per-area cap.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FIXING_SKILLS = {"review-pr", "simplify-sweep", "review-design", "review-ux-psychology"}


class FixEverywhereTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_agents_sweep_the_whole_repository(self):
        agents = sorted((ROOT / "agents").glob("*.md"))
        self.assertTrue(agents, "agents are missing")
        for path in agents:
            with self.subTest(agent=path.stem):
                text = path.read_text(encoding="utf-8")
                self.assertIn("2. **Sweep** — before implementing, search the **whole repository**", text)
                self.assertIn("🔁 **SWEEP**", text, "process is missing the SWEEP step")
                self.assertIn("🔁 **Sweep:**", text, "PR body is missing the sweep count")
                self.assertNotRegex(text, r"(?i)\bup to (2|two)\b|\bsame area\b",
                                    "per-area cap is back")

    def test_fixing_skills_sweep_before_committing(self):
        applying = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
                    if "**Apply the edit**" in path.read_text(encoding="utf-8")}
        self.assertLessEqual(FIXING_SKILLS, applying, "a fixing skill renamed its apply step")
        for name in sorted(applying):
            with self.subTest(skill=name):
                self.assertIn("**Fix every instance, not just the one found.**",
                              self.read(f"skills/{name}/SKILL.md"))

    def test_issue_fixer_sweeps(self):
        self.assertIn("**Fix every instance.**",
                      self.read("skills/triage-issues/references/issue-fix.md"))

    def test_guides_teach_the_rule(self):
        self.assertIn("### Fix it everywhere", self.read("AGENTS.md"))
        self.assertIn("**Fix it everywhere.**", self.read("templates/AGENTS.md"))


if __name__ == "__main__":
    unittest.main()
