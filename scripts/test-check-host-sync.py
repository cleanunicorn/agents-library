#!/usr/bin/env python3
"""Exercise the sync checker in temporary repositories, without agent runs."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).resolve().with_name("check-host-sync.sh")
# Must list the same mirrors as check-host-sync.sh and install-host.sh.
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
        self.check(0, f"{self.host}/ in sync (2 symlinks)")

    def test_absolute_links(self):
        self.agent.unlink()
        self.agent.symlink_to(self.root / "agents/architect.md")
        self.skill.unlink()
        self.skill.symlink_to(self.root / "skills/review")
        self.check(0, f"{self.host}/ in sync (2 symlinks)")

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

    def test_stray_agent_file(self):
        self.agent.write_text("not a link\n")
        self.skill.unlink()
        self.skill.mkdir()
        self.check(1, "STRAY:")

    def test_stray_skill_directory(self):
        extra = self.root / self.host / "skills" / "extra"
        extra.mkdir()
        self.check(1, "STRAY:")

    def test_stray_entry_named_like_a_source_skill(self):
        self.skill.unlink()
        self.skill.mkdir()
        self.check(1, "STRAY:")

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
        self.assertIn(f"{HOST_DIRS[1]}/ in sync (2 symlinks)", result.stdout)


class HostListAgreementTests(unittest.TestCase):
    """The three scripts that name the hosts must agree on what they are.

    A host added to one script but not the others installs a mirror the
    checker never inspects (or vice versa). The lists live as literals in
    each script; this test extracts and compares them so drift fails here.
    """

    SCRIPTS = ("install-host.sh", "check-host-sync.sh", "test-check-host-sync.py")
    # In install-host.sh each host appears as "<host>)"; in the other two
    # scripts the list is a shell/Python tuple or loop over ".<host>" dirs.
    CASE_LINE = re.compile(r"^\s{2}(\w+)\)\s+global_root=")
    QUOTED_DOT_DIR = re.compile(r'"(\.\w+)"')

    def host_sets(self):
        root = Path(__file__).resolve().parent
        found = {}
        for script in self.SCRIPTS:
            text = (root / script).read_text(encoding="utf-8")
            if script == "install-host.sh":
                found[script] = {match.group(1) for line in text.splitlines()
                                 if (match := self.CASE_LINE.match(line))}
            else:
                found[script] = {match.lstrip(".") for match
                                 in self.QUOTED_DOT_DIR.findall(text)}
        return found

    def test_host_lists_agree(self):
        found = self.host_sets()
        for script, hosts in found.items():
            self.assertEqual(hosts, found[self.SCRIPTS[0]],
                             f"{script} disagrees with {self.SCRIPTS[0]}: "
                             f"{sorted(hosts)} vs {sorted(found[self.SCRIPTS[0]])}")

    def test_lists_are_not_empty(self):
        for script, hosts in self.host_sets().items():
            self.assertTrue(hosts, f"{script} has no host list")


if __name__ == "__main__":
    unittest.main()
