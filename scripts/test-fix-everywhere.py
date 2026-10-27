#!/usr/bin/env python3
"""Check that every definition which fixes code also fixes every other instance.

When an agent or skill fixes a problem, it must search the whole repository for
the same problem and fix the other instances in the same PR. These checks fail
if a definition drops that step or slips back to a cap that leaves identical
instances behind.

The patterns match load-bearing words, not prose ornament: a copy-edit that
keeps the rule intact keeps these green, and a failure prints the pattern that
went unmatched rather than the whole file.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Named, not counted: adding an agent or a fix-applying skill should force an
# explicit decision here rather than silently escaping the contract.
AGENTS = {"architect", "deadwood", "docbot", "refactor", "sentinel", "testforge",
          "uidesigner", "uxpolish"}
FIXING_SKILLS = {"manager"}

APPLIES_FIXES = re.compile(r"(?i)\*\*apply the (edit|change|fix)\*\*")
# Agents carry only identity and purpose, so the rule lives in the purpose:
# one problem, fixed at every place it occurs.
AGENT_FIXES_EVERYWHERE = re.compile(r"(?i)\b(everywhere it (occurs|recurs)|on every (view|page)\b)")
FIXES_EVERY_INSTANCE = re.compile(r"(?i)fix every instance")
# Any cap that stops at the instances nearby is the rule this PR removed.
CAP = re.compile(r"(?i)\b(up to|at most|no more than|only)\s+(2|two|3|three)\b"
                 r"|\bsame (area|module|vicinity|neighbou?rhood)\b")


class FixEverywhereTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def expect(self, label, text, pattern, why):
        if not pattern.search(text):
            self.fail(f"{label}: {why} — nothing matched {pattern.pattern!r}")

    def refute(self, label, text, pattern, why):
        found = pattern.search(text)
        if found:
            self.fail(f"{label}: {why} — found {found.group(0)!r}")

    def test_agents_fix_every_instance(self):
        found = {path.stem for path in (ROOT / "agents").glob("*.md")}
        self.assertEqual(found, AGENTS, "agents/ no longer holds exactly the named agents")
        for name in sorted(AGENTS):
            with self.subTest(agent=name):
                text = self.read(f"agents/{name}.md")
                self.expect(name, text, AGENT_FIXES_EVERYWHERE,
                            "the purpose no longer fixes every place the problem occurs")
                self.refute(name, text, CAP, "a per-area cap is back")

    def test_fixing_skills_fix_every_instance(self):
        found = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
                 if APPLIES_FIXES.search(path.read_text(encoding="utf-8"))}
        self.assertEqual(found, FIXING_SKILLS,
                         "a skill started or stopped applying fixes — add it here and give "
                         "it the sweep, or confirm it no longer applies fixes")
        for name in sorted(FIXING_SKILLS):
            with self.subTest(skill=name):
                text = self.read(f"skills/{name}/SKILL.md")
                self.expect(name, text, FIXES_EVERY_INSTANCE,
                            "apply phase does not fix the other instances")
                self.refute(name, text, CAP, "a per-area cap is back")

    def test_manager_coordinator_fixes_every_instance(self):
        path = "skills/manager/references/coordinator-brief.md"
        text = self.read(path)
        self.expect(path, text, FIXES_EVERY_INSTANCE, "the coordinator does not sweep")
        self.refute(path, text, CAP, "a per-area cap is back")

    def test_guides_teach_the_rule(self):
        guide = self.read("AGENTS.md")
        self.expect("AGENTS.md", guide, re.compile(r"(?mi)^#+\s+Fix it everywhere\s*$"),
                    "the Fix it everywhere section is gone — AGENTS.md links to #fix-it-everywhere")
        self.expect("templates/AGENTS.md", self.read("templates/AGENTS.md"),
                    re.compile(r"(?i)fix it everywhere"), "the template dropped the rule")
        for doc in ("AGENTS.md", "templates/AGENTS.md", "README.md"):
            self.refute(doc, self.read(doc), CAP, "a per-area cap is back")


if __name__ == "__main__":
    unittest.main()
