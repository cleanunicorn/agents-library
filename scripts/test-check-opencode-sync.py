#!/usr/bin/env python3
"""Exercise the sync checker in temporary repositories, without agent runs."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).resolve().with_name("check-opencode-sync.sh")


class SyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="opencode-sync-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ("scripts", "agents", "skills/review", ".opencode/agents",
                          ".opencode/skills"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        shutil.copy2(CHECKER, self.root / "scripts" / CHECKER.name)
        (self.root / "agents/architect.md").write_text("agent\n")
        (self.root / "skills/review/SKILL.md").write_text("skill\n")
        self.agent = self.root / ".opencode/agents/architect.md"
        self.skill = self.root / ".opencode/skills/review"
        self.agent.symlink_to("../../agents/architect.md")
        self.skill.symlink_to("../../skills/review", target_is_directory=True)

    def check(self, code, message):
        result = subprocess.run(
            ["bash", str(self.root / "scripts" / CHECKER.name)],
            cwd=tempfile.gettempdir(), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertIn(message, result.stdout)

    def test_valid_links_from_another_directory(self):
        self.check(0, "2 symlinks")

    def test_absolute_links(self):
        self.agent.unlink()
        self.agent.symlink_to(self.root / "agents/architect.md")
        self.skill.unlink()
        self.skill.symlink_to(self.root / "skills/review")
        self.check(0, "2 symlinks")

    def test_missing_link(self):
        self.agent.unlink()
        self.check(1, "MISSING:")

    def test_copy_instead_of_link(self):
        self.agent.unlink()
        self.agent.write_text("agent\n")
        self.check(1, "MISSING:")

    def test_dangling_agent_link(self):
        self.agent.unlink()
        self.agent.symlink_to("../../agents/missing.md")
        self.check(1, "WRONG:")

    def test_agent_link_to_wrong_file(self):
        self.agent.unlink()
        self.agent.symlink_to("../../skills/review/SKILL.md")
        self.check(1, "WRONG:")

    def test_dangling_skill_link(self):
        self.skill.unlink()
        self.skill.symlink_to("../../skills/missing")
        self.check(1, "WRONG:")

    def test_skill_link_to_another_directory(self):
        self.skill.unlink()
        self.skill.symlink_to("../../agents")
        self.check(1, "WRONG:")

    def test_stale_agent_link(self):
        (self.root / "agents/architect.md").unlink()
        self.check(1, "STALE:")

    def test_skill_directory_without_definition(self):
        (self.root / "skills/review/SKILL.md").unlink()
        self.check(1, "STALE:")

    def test_stale_skill_link(self):
        shutil.rmtree(self.root / "skills/review")
        self.check(1, "STALE:")


if __name__ == "__main__":
    unittest.main()
