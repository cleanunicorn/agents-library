#!/usr/bin/env python3
"""Exercise the skills' deterministic scripts against temporary repositories and a stub gh.

The skills are thin prose; these scripts are the part with behavior to pin:
run-gate.sh, test-commands.sh, check-prs.sh and list-issues.sh. No network,
credentials or model calls.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCH = ROOT / "skills" / "batch-merge-prs" / "scripts"
TRIAGE = ROOT / "skills" / "triage-issues" / "scripts"

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "Test", "GIT_COMMITTER_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "LC_ALL": "C",
}

# Answers only what the scripts ask; GH_FAIL names subcommands that must fail.
GH_STUB = """#!/bin/sh
case "$1 $2" in
  "auth status") exit 0 ;;
  "repo view") echo "owner/repo"; exit 0 ;;
  "label list") [ "$GH_FAIL" = labels ] && exit 1; echo "bug"; exit 0 ;;
  "issue list") [ "$GH_FAIL" = issues ] && exit 1; echo "[]"; exit 0 ;;
esac
if [ "$1 $2" = "pr view" ]; then
  case "$*" in
    *"-q .state"*) echo OPEN ;;
    *mergeCommit*) echo "" ;;
    *isDraft*) echo "$GH_DRAFT" ;;
  esac
  exit 0
fi
exit 1
"""


class Sandbox(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="skill-scripts-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, **GIT_ENV, "PATH": f"{self.bin}:{os.environ['PATH']}", "GH_DRAFT": "false"}

    def stub_gh(self):
        gh = self.bin / "gh"
        gh.write_text(GH_STUB)
        gh.chmod(0o755)

    def run_script(self, script, *args, cwd=None, env=None):
        return subprocess.run([shutil.which("bash"), str(script), *args], cwd=cwd or self.root,
                              env={**self.env, **(env or {})}, capture_output=True, text=True)

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()


class RunGateTests(Sandbox):
    def test_reports_the_commands_status_and_keeps_a_log(self):
        log = self.root / "logs" / "gate.log"
        result = self.run_script(BATCH / "run-gate.sh", "unit", str(log), "echo hello; exit 3")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout.splitlines()[-1], f"GATE unit exit=3 log={log}")
        self.assertIn("hello", log.read_text())

    def test_passing_command_exits_zero(self):
        result = self.run_script(BATCH / "run-gate.sh", "unit", str(self.root / "g.log"), "true")
        self.assertEqual(result.returncode, 0)
        self.assertIn("exit=0", result.stdout.splitlines()[-1])

    def test_wrong_argument_count_is_a_usage_error(self):
        self.assertEqual(self.run_script(BATCH / "run-gate.sh", "only-a-label").returncode, 2)


class TestCommandsTests(Sandbox):
    def project(self):
        project = self.root / "project"
        project.mkdir()
        return project

    def test_empty_project_prints_none(self):
        result = self.run_script(BATCH / "test-commands.sh", cwd=self.project())
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "NONE"))

    def test_guidance_files_and_manifests_are_listed(self):
        project = self.project()
        (project / "AGENTS.md").write_text("Run `make test`.\n")
        (project / "Makefile").write_text("test:\n\tpytest\nlint:\n\truff .\n")
        (project / "package.json").write_text('{"scripts": {"test": "jest", "start": "node ."}}')
        (project / "go.mod").write_text("module x\n")
        lines = self.run_script(BATCH / "test-commands.sh", cwd=project).stdout.splitlines()
        self.assertIn("SOURCE AGENTS.md", lines)
        self.assertIn("CANDIDATE Makefile make test", lines)
        self.assertIn("CANDIDATE Makefile make lint", lines)
        self.assertIn("CANDIDATE package.json npm run test", lines)
        self.assertNotIn("CANDIDATE package.json npm run start", lines)
        self.assertIn("CANDIDATE go.mod go test ./...", lines)

    def test_workflow_run_lines_become_candidates(self):
        project = self.project()
        workflows = project / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("steps:\n  - run: npm ci\n  - run: |\n      make test\n")
        lines = self.run_script(BATCH / "test-commands.sh", cwd=project).stdout.splitlines()
        self.assertIn("CANDIDATE .github/workflows/ci.yml npm ci", lines)
        self.assertIn("SOURCE .github/workflows/ci.yml (multi-line run block)", lines)

    def test_docs_pairing_tests_with_live_resources_are_cautions(self):
        project = self.project()
        (project / "AGENTS.md").write_text("The integration tests hit the production API.\nBe kind.\n")
        lines = self.run_script(BATCH / "test-commands.sh", cwd=project).stdout.splitlines()
        self.assertTrue(any(line.startswith("CAUTION AGENTS.md:") for line in lines), lines)
        self.assertFalse(any("Be kind" in line for line in lines))


class CheckPrsTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.stub_gh()
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self.git(self.root, "init", "-q", "--bare", "-b", "main", str(self.remote))
        self.git(self.root, "clone", "-q", str(self.remote), str(self.work))
        self.commit("base")
        self.git(self.work, "push", "-q", "origin", "main")

    def commit(self, name):
        (self.work / name).write_text(name)
        self.git(self.work, "add", name)
        self.git(self.work, "commit", "-qm", name)
        return self.git(self.work, "rev-parse", "HEAD")

    def publish_pr(self, number, sha):
        self.git(self.work, "push", "-q", "origin", f"{sha}:refs/pull/{number}/head")

    def check(self, *args, env=None):
        return self.run_script(BATCH / "check-prs.sh", "origin", *args, cwd=self.work, env=env)

    def test_classifies_each_pr_in_the_order_given(self):
        merged = self.commit("merged")
        self.git(self.work, "push", "-q", "origin", "main")
        self.publish_pr(1, merged)
        self.git(self.work, "checkout", "-q", "-b", "feature", "HEAD~1")
        new = self.commit("new")
        self.publish_pr(2, new)
        result = self.check("1", "2", "3", "not-a-pr", "2",
                            "https://github.com/other/place/pull/9")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "MAIN main",
            "REPO owner/repo",
            f"IN_MAIN 1 head-reachable {merged}",
            f"TODO 2 {new} OPEN",
            "SKIPPED 3 fetch-failed",
            "SKIPPED not-a-pr bad-ref",
            "SKIPPED https://github.com/other/place/pull/9 other-repo other/place",
        ])

    def test_a_draft_pr_is_reported_as_draft(self):
        self.git(self.work, "checkout", "-q", "-b", "feature")
        self.publish_pr(4, self.commit("wip"))
        result = self.check("4", env={"GH_DRAFT": "true"})
        self.assertIn("DRAFT", result.stdout.splitlines()[-1])

    def test_a_squash_merged_pr_is_patch_equivalent(self):
        self.git(self.work, "checkout", "-q", "-b", "feature")
        head = self.commit("feat")
        self.publish_pr(5, head)
        self.git(self.work, "checkout", "-q", "main")
        self.commit("diverge")
        self.git(self.work, "cherry-pick", head)
        self.git(self.work, "push", "-q", "origin", "main")
        result = self.check("5")
        self.assertEqual(result.stdout.splitlines()[-1], f"IN_MAIN 5 patch-equivalent {head}")

    def test_fatal_when_the_remote_cannot_be_fetched(self):
        result = self.run_script(BATCH / "check-prs.sh", "nowhere", "1", cwd=self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FATAL", result.stderr)

    def test_usage_error_without_prs(self):
        self.assertEqual(self.run_script(BATCH / "check-prs.sh", "origin", cwd=self.work).returncode, 2)


class ListIssuesTests(Sandbox):
    def test_prints_repo_labels_and_issues_sections(self):
        self.stub_gh()
        result = self.run_script(TRIAGE / "list-issues.sh")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(),
                         ["== repo ==", "owner/repo", "== labels ==", "bug", "== issues ==", "[]"])

    def test_failed_label_list_is_a_marker_not_fatal(self):
        self.stub_gh()
        result = self.run_script(TRIAGE / "list-issues.sh", env={"GH_FAIL": "labels"})
        self.assertEqual(result.returncode, 0)
        self.assertIn("(label list failed)", result.stdout)

    def test_failed_issue_list_is_fatal(self):
        self.stub_gh()
        result = self.run_script(TRIAGE / "list-issues.sh", env={"GH_FAIL": "issues"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("FATAL", result.stderr)

    def test_missing_gh_is_fatal(self):
        result = self.run_script(TRIAGE / "list-issues.sh", env={"PATH": str(self.root)})
        self.assertEqual(result.returncode, 1)
        self.assertIn("gh is not installed", result.stderr)


if __name__ == "__main__":
    unittest.main()
