#!/usr/bin/env python3
"""Exercise install.py against a sandboxed HOME with stub host CLIs on PATH.

No real host CLI, network, or user config is touched: HOME and
XDG_CONFIG_HOME point into a temp dir, and `claude`/`codex`/`opencode`/`kilo`
are shell stubs that log their arguments.
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
INSTALLER = REPO / "install.py"

STUB = """#!/bin/sh
echo "{name} $*" >> "$STUB_DIR/calls.log"
case "$*" in
  "plugin list"*) cat "$STUB_DIR/{name}-list.json" 2>/dev/null || echo '{empty}'; exit 0 ;;
esac
# "$2" is the subcommand after `plugin` (install, add, marketplace).
exit $(cat "$STUB_DIR/{name}-exit-$2" 2>/dev/null || echo 0)
"""


def load_installer():
    spec = importlib.util.spec_from_file_location("installer", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_installer()
AGENTS = sorted(p.stem for p in (REPO / "agents").glob("*.md"))
SKILLS = sorted(p.parent.name for p in (REPO / "skills").glob("*/SKILL.md"))


class Sandbox(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="install-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.stubs = self.root / "stubs"
        for directory in (self.home, self.project, self.stubs):
            directory.mkdir()
        for name in installer.HOSTS:
            self.add_stub(name)

    def add_stub(self, name):
        empty = "[]" if name == "claude" else '{"installed": []}'
        stub = self.stubs / name
        stub.write_text(STUB.format(name=name, empty=empty))
        stub.chmod(0o755)

    def run_installer(self, *args, cwd=None):
        env = {"HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
               "PATH": f"{self.stubs}:/usr/bin:/bin", "STUB_DIR": str(self.stubs)}
        result = subprocess.run([sys.executable, str(INSTALLER), *args], cwd=cwd or self.project,
                                env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        return result.returncode, result.stdout.splitlines(), result.stderr

    def calls(self):
        log = self.stubs / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def saved(self, project=False):
        path = (self.project / ".agents-library.json" if project
                else self.home / ".config" / "agents-library" / "selection.json")
        return json.loads(path.read_text())

    def opencode(self, *parts):
        return self.home / ".config" / "opencode" / Path(*parts)


class FileHostTests(Sandbox):
    def test_default_links_every_item_into_every_file_host(self):
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode,kilo")
        self.assertEqual(code, 0)
        self.assertEqual(len(out), 2 * (len(AGENTS) + len(SKILLS)))
        self.assertIn("LINKED opencode/architect", out)
        self.assertIn("LINKED kilo/review-pr", out)
        link = self.opencode("skills", "review-pr")
        self.assertEqual(link.resolve(), REPO / "skills" / "review-pr")

    def test_rerun_reports_ok(self):
        self.run_installer("--yes", "--hosts", "opencode")
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode")
        self.assertEqual(code, 0)
        self.assertTrue(all(line.startswith("OK ") for line in out), out)

    def test_skip_removes_our_install_and_is_remembered(self):
        self.run_installer("--yes", "--hosts", "opencode")
        code, out, _ = self.run_installer("--yes", "--skip", "manager,architect")
        self.assertEqual(code, 0)
        self.assertIn("REMOVED opencode/manager", out)
        self.assertIn("REMOVED opencode/architect", out)
        self.assertFalse(self.opencode("skills", "manager").exists())
        self.assertEqual(self.saved()["excluded"], ["architect", "manager"])

        # The next plain run keeps them unchecked without being told again.
        code, out, _ = self.run_installer("--yes")
        self.assertEqual(code, 0)
        self.assertNotIn("LINKED opencode/manager", out)
        self.assertFalse(self.opencode("skills", "manager").exists())

    def test_all_rechecks_everything(self):
        self.run_installer("--yes", "--hosts", "opencode", "--skip", "manager")
        code, out, _ = self.run_installer("--yes", "--all")
        self.assertIn("LINKED opencode/manager", out)
        self.assertEqual(self.saved()["excluded"], [])

    def test_only_keeps_the_named_items(self):
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode", "--only", "review-pr")
        self.assertEqual(out, ["LINKED opencode/review-pr"])
        self.assertEqual(len(self.saved()["excluded"]), len(AGENTS) + len(SKILLS) - 1)

    def test_only_removes_every_other_installed_item(self):
        self.run_installer("--yes", "--hosts", "opencode")
        code, out, _ = self.run_installer("--yes", "--force", "--only", "review-pr")
        self.assertEqual(code, 0)
        self.assertIn("OK opencode/review-pr", out)
        self.assertIn("REMOVED opencode/architect", out)
        self.assertEqual(sum(line.startswith("REMOVED ") for line in out), len(AGENTS) + len(SKILLS) - 1)
        self.assertEqual([p.name for p in self.opencode("skills").iterdir()], ["review-pr"])

    def test_unchecked_item_that_differs_is_kept(self):
        target = self.opencode("agents", "architect.md")
        target.parent.mkdir(parents=True)
        target.write_text("my own architect\n")
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode", "--skip", "architect")
        self.assertEqual(code, 0)
        self.assertIn("KEPT opencode/architect", out)
        self.assertEqual(target.read_text(), "my own architect\n")

    def test_conflict_then_force(self):
        target = self.opencode("agents", "architect.md")
        target.parent.mkdir(parents=True)
        target.write_text("x\n")
        code, out, stderr = self.run_installer("--yes", "--hosts", "opencode")
        self.assertEqual(code, 2)
        self.assertIn("CONFLICT opencode/architect", out)
        self.assertIn("--force", stderr)
        code, out, _ = self.run_installer("--yes", "--force")
        self.assertEqual(code, 0)
        self.assertIn("UPDATED opencode/architect", out)
        self.assertTrue(target.is_symlink())

    def test_symlinked_destination_root_is_refused(self):
        real = self.root / "elsewhere"
        real.mkdir()
        (self.home / ".config").mkdir()
        self.opencode().symlink_to(real)
        code, out, stderr = self.run_installer("--yes", "--hosts", "opencode")
        self.assertEqual(code, 3)
        self.assertIn("refusing to write through it", stderr)
        self.assertEqual(list(real.iterdir()), [])

    def test_dry_run_changes_and_saves_nothing(self):
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("LINKED opencode/architect", out)
        self.assertFalse(self.opencode().exists())
        self.assertFalse((self.home / ".config" / "agents-library").exists())


class CopyRemovalTests(Sandbox):
    """Unchecking a copied item removes it only while it is byte-identical to
    the library; anything a user added or changed keeps it in place."""

    def install_copies(self):
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode", "--copy")
        self.assertEqual(code, 0)
        self.assertIn("COPIED opencode/review-pr", out)

    def skip(self, name):
        code, out, _ = self.run_installer("--yes", "--hosts", "opencode", "--copy", "--skip", name)
        self.assertEqual(code, 0)
        return out

    def test_identical_copy_is_removed(self):
        self.install_copies()
        self.assertIn("REMOVED opencode/review-pr", self.skip("review-pr"))
        self.assertFalse(self.opencode("skills", "review-pr").exists())

    def test_edited_agent_copy_is_kept(self):
        self.install_copies()
        target = self.opencode("agents", "architect.md")
        target.write_text("my own architect\n")
        self.assertIn("KEPT opencode/architect", self.skip("architect"))
        self.assertEqual(target.read_text(), "my own architect\n")

    def test_file_added_to_a_copied_skill_keeps_it(self):
        # `tags` and `.git` are on filecmp's default ignore list.
        for name in ("notes.md", "tags", ".git"):
            with self.subTest(name=name):
                shutil.rmtree(self.home / ".config", ignore_errors=True)
                self.install_copies()
                added = self.opencode("skills", "review-pr", name)
                added.write_text("mine\n")
                self.assertIn("KEPT opencode/review-pr", self.skip("review-pr"))
                self.assertEqual(added.read_text(), "mine\n")

    def test_directory_replaced_by_a_file_keeps_it(self):
        self.install_copies()
        skill = self.opencode("skills", "review-pr")
        subdir = next(path for path in sorted(skill.iterdir()) if path.is_dir())
        shutil.rmtree(subdir)
        subdir.write_text("mine\n")
        self.assertIn("KEPT opencode/review-pr", self.skip("review-pr"))
        self.assertEqual(subdir.read_text(), "mine\n")


class FilesystemErrorTests(Sandbox):
    """A filesystem error on one item is reported as FAILED and the run goes
    on; it never escapes as a traceback."""

    def run_in_process(self, excluded, **patches):
        ledger = installer.Ledger(dry_run=False)
        items = installer.discover_items()
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.multiple(installer, **patches):
            installer.install_files("opencode", self.opencode(), items, excluded, "symlink", False, ledger)
        return ledger.status, out.getvalue().splitlines()

    def test_removal_error_is_failed_and_later_items_continue(self):
        self.run_installer("--yes", "--hosts", "opencode")
        denied = mock.Mock(side_effect=PermissionError("denied"))
        status, out = self.run_in_process(["architect", "manager"], remove=denied)
        self.assertEqual(status, installer.EXIT_FAILED)
        self.assertIn("FAILED opencode/architect", out)
        self.assertIn("FAILED opencode/manager", out)
        self.assertIn("OK opencode/review-pr", out)

    def test_comparison_error_is_failed_and_later_items_continue(self):
        self.run_installer("--yes", "--hosts", "opencode", "--copy", "--only", "review-pr")
        unreadable = mock.Mock(side_effect=PermissionError("denied"))
        status, out = self.run_in_process([], same_copy=unreadable, same_link=unreadable)
        self.assertEqual(status, installer.EXIT_FAILED)
        self.assertIn("FAILED opencode/review-pr", out)
        self.assertEqual(len(out), len(AGENTS) + len(SKILLS))

    def test_unwritable_selection_is_fatal(self):
        (self.home / ".config").mkdir()
        (self.home / ".config" / "agents-library").write_text("a file, not a directory\n")
        code, out, stderr = self.run_installer("--yes", "--hosts", "opencode")
        self.assertEqual(code, 1)
        self.assertIn("FATAL: cannot save selection", stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertEqual(out, [])


class HostSelectionTests(Sandbox):
    def test_default_hosts_are_the_ones_on_path(self):
        (self.stubs / "kilo").unlink()
        (self.stubs / "codex").unlink()
        code, out, _ = self.run_installer("--yes")
        self.assertEqual(code, 0)
        hosts = {line.split()[1].split("/")[0] for line in out}
        self.assertEqual(hosts, {"claude", "opencode"})

    def test_host_choice_is_remembered(self):
        self.run_installer("--yes", "--hosts", "kilo")
        code, out, _ = self.run_installer("--yes")
        self.assertEqual({line.split()[1].split("/")[0] for line in out}, {"kilo"})
        self.assertEqual(self.saved()["hosts"],
                         {"claude": False, "codex": False, "opencode": False, "kilo": True})

    def test_unknown_names_are_usage_errors(self):
        for args in (["--hosts", "vim"], ["--skip", "nope"], ["--only", "../etc"]):
            code, out, stderr = self.run_installer("--yes", *args)
            self.assertEqual(code, 1, args)
            self.assertIn("FATAL", stderr)
            self.assertEqual(out, [])

    def test_bad_arguments_are_usage_errors_not_conflicts(self):
        for args in (["--bogus"], ["--hosts"], ["--copy", "--symlink"]):
            code, out, stderr = self.run_installer("--yes", *args)
            self.assertEqual(code, 1, args)
            self.assertIn("FATAL: bad arguments", stderr)
            self.assertEqual(out, [])
        code, out, _ = self.run_installer("--help")
        self.assertEqual(code, 0)
        self.assertTrue(out[0].startswith("usage: install.py"))

    def test_checklist_needs_a_terminal(self):
        code, _, stderr = self.run_installer("--hosts", "opencode")
        self.assertEqual(code, 1)
        self.assertIn("pass --yes", stderr)

    def test_malformed_selection_is_not_overwritten(self):
        path = self.home / ".config" / "agents-library" / "selection.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"excluded": "manager"}')
        code, _, stderr = self.run_installer("--yes")
        self.assertEqual(code, 1)
        self.assertIn("malformed", stderr)
        self.assertEqual(path.read_text(), '{"excluded": "manager"}')


    def test_saved_selection_that_is_not_an_object_is_malformed(self):
        path = self.home / ".config" / "agents-library" / "selection.json"
        path.parent.mkdir(parents=True)
        for text in ("[]", "null", '"opencode"', "3"):
            path.write_text(text)
            code, _, stderr = self.run_installer("--yes")
            self.assertEqual(code, 1, text)
            self.assertIn("malformed", stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertEqual(path.read_text(), text)


class PluginHostTests(Sandbox):
    def test_plugins_install_through_their_cli(self):
        code, out, _ = self.run_installer("--yes", "--hosts", "claude,codex")
        self.assertEqual(code, 0)
        self.assertEqual(out, ["INSTALLED claude/agents-library", "INSTALLED codex/agents-library"])
        self.assertIn("claude plugin install agents-library --marketplace cleanunicorn/agents-library "
                      "--scope user", self.calls())
        self.assertIn("codex plugin marketplace add cleanunicorn/agents-library", self.calls())
        self.assertIn("codex plugin add agents-library@agents-library", self.calls())

    def test_installed_plugins_report_ok(self):
        (self.stubs / "claude-list.json").write_text(
            '[{"id": "agents-library@agents-library", "scope": "user"}]')
        (self.stubs / "codex-list.json").write_text(
            '{"installed": [{"pluginId": "agents-library@agents-library"}]}')
        code, out, _ = self.run_installer("--yes", "--hosts", "claude,codex")
        self.assertEqual(out, ["OK claude/agents-library", "OK codex/agents-library"])
        self.assertFalse(any("install" in call or " add " in call for call in self.calls()))

    def test_unexpected_plugin_listings_mean_not_installed(self):
        for claude, codex in (("{}", "[]"), ("[1]", '{"installed": [1]}'), ("[]", '{"installed": {}}')):
            (self.stubs / "claude-list.json").write_text(claude)
            (self.stubs / "codex-list.json").write_text(codex)
            code, out, stderr = self.run_installer("--yes", "--hosts", "claude,codex")
            self.assertEqual(code, 0, (claude, codex, stderr))
            self.assertEqual(out, ["INSTALLED claude/agents-library", "INSTALLED codex/agents-library"])

    def test_codex_marketplace_already_added_still_installs(self):
        (self.stubs / "codex-exit-marketplace").write_text("1")
        code, out, _ = self.run_installer("--yes", "--hosts", "codex")
        self.assertEqual(code, 0)
        self.assertEqual(out, ["INSTALLED codex/agents-library"])
        self.assertIn("codex plugin add agents-library@agents-library", self.calls())

    def test_failed_plugin_install_is_reported(self):
        (self.stubs / "claude-exit-install").write_text("1")
        code, out, stderr = self.run_installer("--yes", "--hosts", "claude,opencode", "--only", "architect")
        self.assertEqual(code, 3)
        self.assertEqual(out, ["FAILED claude/agents-library", "LINKED opencode/architect"])
        self.assertIn("exited 1", stderr)

    def test_unchecked_items_warn_for_plugin_hosts(self):
        code, _, stderr = self.run_installer("--yes", "--hosts", "claude", "--skip", "manager")
        self.assertEqual(code, 0)
        self.assertIn("whole plugin", stderr)


class ProjectTests(Sandbox):
    def test_project_copies_and_saves_in_the_project(self):
        code, out, stderr = self.run_installer("--yes", "--project", "--hosts", "claude,codex,opencode",
                                               "--skip", "manager")
        self.assertEqual(code, 0)
        self.assertIn("COPIED opencode/architect", out)
        self.assertIn("SKIPPED codex/agents-library", out)
        self.assertIn("INSTALLED claude/agents-library", out)
        self.assertIn("--scope project", " ".join(self.calls()))
        copied = self.project / ".opencode" / "skills" / "review-pr"
        self.assertTrue(copied.is_dir() and not copied.is_symlink())
        self.assertEqual(self.saved(project=True)["excluded"], ["manager"])
        self.assertFalse((self.home / ".config" / "agents-library").exists())

        code, out, _ = self.run_installer("--yes", "--project")
        self.assertIn("OK opencode/review-pr", out)


class ChecklistTests(unittest.TestCase):
    def rows(self):
        return [installer.Row(key, key, True) for key in ("a", "b", "c")]

    def test_space_toggles_the_cursor_row(self):
        checklist = installer.Checklist("t", self.rows())
        checklist.press("down")
        checklist.press(" ")
        self.assertEqual(checklist.checked(), ["a", "c"])

    def test_cursor_wraps(self):
        checklist = installer.Checklist("t", self.rows())
        checklist.press("up")
        self.assertEqual(checklist.cursor, 2)
        checklist.press("j")
        self.assertEqual(checklist.cursor, 0)

    def test_a_toggles_all(self):
        checklist = installer.Checklist("t", self.rows())
        checklist.press("a")
        self.assertEqual(checklist.checked(), [])
        checklist.press(" ")
        checklist.press("a")
        self.assertEqual(checklist.checked(), ["a", "b", "c"])

    def test_enter_and_quit_end_it(self):
        checklist = installer.Checklist("t", self.rows())
        self.assertIsNone(checklist.press("x"))
        self.assertEqual(checklist.press("enter"), "done")
        self.assertEqual(checklist.press("q"), "cancel")
        self.assertEqual(checklist.press("esc"), "cancel")

    def test_item_rows_start_checked_except_saved_exclusions(self):
        rows = installer.item_rows(installer.discover_items(), ["manager"])
        unchecked = [row.key for row in rows if not row.checked]
        self.assertEqual(unchecked, ["manager"])
        self.assertEqual(len(rows), len(AGENTS) + len(SKILLS))



class InteractiveTests(unittest.TestCase):
    """The glue between the checklists and the saved selection, with the
    terminal and the curses screens replaced by scripted answers."""

    ON_PATH = ("claude", "opencode")

    def setUp(self):
        which = mock.patch.object(installer.shutil, "which",
                                  side_effect=lambda binary: f"/bin/{binary}" if binary in self.ON_PATH else None)
        which.start()
        self.addCleanup(which.stop)
        terminal = mock.patch.object(installer, "sys")
        fake_sys = terminal.start()
        self.addCleanup(terminal.stop)
        fake_sys.stdin.isatty.return_value = fake_sys.stdout.isatty.return_value = True
        self.shown = []

    def answer(self, *answers):
        """Patch run_checklist to record each checklist and give the next answer."""
        replies = iter(answers)

        def run_checklist(checklist):
            self.shown.append(checklist)
            reply = next(replies)
            if isinstance(reply, Exception):
                raise reply
            return reply

        patcher = mock.patch.object(installer, "run_checklist", side_effect=run_checklist)
        patcher.start()
        self.addCleanup(patcher.stop)

    def resolve(self, saved, *argv):
        return installer.resolve(installer.parse_args(list(argv)), installer.discover_items(), saved, None)

    def test_host_rows_check_hosts_on_path_unless_a_saved_choice_says_otherwise(self):
        saved = installer.Selection({"claude": False, "kilo": True}, [])
        rows = {row.key: row for row in installer.host_rows(saved, None)}
        self.assertEqual({key: row.checked for key, row in rows.items()},
                         {"claude": False, "codex": False, "opencode": True, "kilo": True})
        self.assertEqual(rows["claude"].note, "found · whole plugin via its CLI")
        self.assertEqual(rows["kilo"].note, "not found on PATH")
        project_rows = {row.key: row for row in installer.host_rows(saved, Path("/project"))}
        self.assertIn("no project scope", project_rows["codex"].note)

    def test_both_checklists_decide_hosts_and_unchecked_items(self):
        everything_but_manager = [name for name in AGENTS + SKILLS if name != "manager"]
        self.answer(["claude", "opencode"], everything_but_manager)
        chosen = self.resolve(installer.Selection({}, ["architect"]))
        self.assertEqual(chosen.hosts, {"claude": True, "codex": False, "opencode": True, "kilo": False})
        self.assertEqual(chosen.excluded, ["manager"])
        hosts_screen, items_screen = self.shown
        self.assertEqual(hosts_screen.checked(), ["claude", "opencode"])
        unchecked = [row.key for row in items_screen.rows if not row.checked]
        self.assertEqual(unchecked, ["architect"])

    def test_items_screen_is_skipped_without_a_file_host(self):
        self.answer(["claude"])
        chosen = self.resolve(installer.Selection({}, ["architect"]))
        self.assertEqual(len(self.shown), 1)
        self.assertEqual(chosen.excluded, ["architect"])

    def test_cancelling_the_items_screen_installs_and_saves_nothing(self):
        self.answer(["opencode"], installer.Fatal("cancelled; nothing was installed or saved"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selection.json"
            with mock.patch.multiple(installer, selection_path=mock.Mock(return_value=path),
                                     install_files=mock.DEFAULT, install_plugin=mock.DEFAULT) as fakes:
                with self.assertRaises(installer.Fatal):
                    installer.main([])
            self.assertFalse(path.exists())
            fakes["install_files"].assert_not_called()
            fakes["install_plugin"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
