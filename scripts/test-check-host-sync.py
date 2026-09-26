#!/usr/bin/env python3
"""Exercise the sync checker in temporary repositories, without agent runs."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).resolve().with_name("check-host-sync.sh")
HOST_DIRS = (".opencode", ".kilo")


class SyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="host-sync-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ("scripts", "agents", "skills/review"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        for host in HOST_DIRS:
            for directory in (f"{host}/agents", f"{host}/skills"):
                (self.root / directory).mkdir(parents=True, exist_ok=True)
            agent = self.root / host / "agents" / "architect.md"
            skill = self.root / host / "skills" / "review"
            agent.symlink_to("../../agents/architect.md")
            skill.symlink_to("../../skills/review", target_is_directory=True)
        shutil.copy2(CHECKER, self.root / "scripts" / CHECKER.name)
        (self.root / "agents/architect.md").write_text("agent\n")
        (self.root / "skills/review/SKILL.md").write_text("skill\n")
        # The tests below mutate the first host's links; every other mirror
        # stays clean so each case exercises one broken host at a time.
        self.host = HOST_DIRS[0]
        self.agent = self.root / self.host / "agents/architect.md"
        self.skill = self.root / self.host / "skills/review"

    def check(self, code, message):
        result = subprocess.run(
            ["bash", str(self.root / "scripts" / CHECKER.name)],
            cwd=tempfile.gettempdir(), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertIn(message, result.stdout)

    def test_valid_links_from_another_directory(self):
        self.check(0, f"{self.host}/ in sync")

    def test_absolute_links(self):
        self.agent.unlink()
        self.agent.symlink_to(self.root / "agents/architect.md")
        self.skill.unlink()
        self.skill.symlink_to(self.root / "skills/review")
        self.check(0, f"{self.host}/ in sync")

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

    def test_broken_mirror_leaves_the_other_one_clean(self):
        self.agent.unlink()
        self.agent.write_text("agent\n")
        result = subprocess.run(
            ["bash", str(self.root / "scripts" / CHECKER.name)],
            cwd=tempfile.gettempdir(), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("MISSING:", result.stdout)
        self.assertIn(f"{HOST_DIRS[1]}/ in sync", result.stdout)


if __name__ == "__main__":
    unittest.main()
