#!/usr/bin/env python3
"""Check that the manager answers routine worker approvals and relays only the rare ones.

A manager that relays every permission prompt stalls each worker until the
user answers; one that approves everything lets a worker merge, force-push, or
touch secrets because a dialog offered "Allow". These checks hold both halves:
the default (answer, persistently, and log it) and the five escalation cases,
plus the read-only roles that auto-approval must not widen.

The patterns match load-bearing words, not prose ornament, so a copy-edit
that keeps the rule keeps these green.
"""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANAGER = ROOT / "skills" / "manager"

OLD_RELAY_RULE = re.compile(r"(?i)never answer an approval")

# Each escalation case in console.md § Approvals, by the words that make it that case.
ESCALATIONS = {
    "forbidden or reserved actions": re.compile(r"(?is)merg.{0,80}force-push.{0,80}main branch"),
    "destruction outside the item": re.compile(r"(?is)irreversible destruction outside"),
    "secrets and global settings": re.compile(r"(?is)secrets.{0,40}credentials.{0,80}global"),
    "the ask-first list": re.compile(r"(?i)ask-first list"),
    "an unclassifiable prompt": re.compile(r"(?i)cannot classify"),
}

# Launch flags that remove every prompt, so no escalation case can surface.
BYPASS = re.compile(r"--dangerously-skip-permissions|bypassPermissions"
                    r"|--dangerously-bypass-approvals-and-sandbox|-a never\b|--auto\b")

# The escalation commands every launch recipe must keep prompting for, as each
# host's ask rule writes them. A host default that allows everything (opencode,
# kilo) otherwise lets these run silently even with no bypass flag.
ESCALATION_COMMANDS = ("git push*--force*", "git push*-f*", "gh pr merge*", "gh pr ready*",
                       "git branch -D*", "git worktree remove*", "rm -rf*")


def rule(text, number):
    """Return one numbered rule from SKILL.md's Rules list."""
    found = re.search(rf"(?ms)^{number}\. .*?(?=^\d+\. |^## )", text)
    if not found:
        raise AssertionError(f"SKILL.md has no rule {number}")
    return found.group(0)


def section(text, heading):
    """Return one `## heading` section, up to the next one."""
    found = re.search(rf"(?ms)^## {heading}\n.*?(?=^## |\Z)", text)
    if not found:
        raise AssertionError(f"no '## {heading}' section")
    return found.group(0)


def launch_rows(text):
    """Return herdr.md's pre-grant table as {kind: (coordinator cell, planner/reviewer cell)}."""
    rows = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) == 3 and cells[0] not in ("kind", "") and not set(cells[0]) <= set("-"):
            rows[cells[0]] = (cells[1], cells[2])
    return rows


class ManagerApprovalTests(unittest.TestCase):
    def read(self, relative):
        return (MANAGER / relative).read_text(encoding="utf-8")

    def expect(self, label, text, pattern, why):
        # Prose wraps anywhere; match the words, not the line breaks.
        if not re.search(pattern, " ".join(text.split())):
            self.fail(f"{label}: {why} — nothing matched {pattern!r}")

    def test_old_relay_everything_rule_is_gone(self):
        for path in sorted(MANAGER.rglob("*.md")):
            with self.subTest(path=str(path.relative_to(ROOT))):
                found = OLD_RELAY_RULE.search(path.read_text(encoding="utf-8"))
                self.assertIsNone(found, f"{path.name} still forbids answering approvals")

    def test_rule_7_points_at_the_approvals_policy(self):
        seven = rule(self.read("SKILL.md"), 7)
        self.expect("rule 7", seven, r"(?i)answer approvals yourself",
                    "the manager no longer answers approvals by default")
        self.expect("rule 7", seven, r"references/console\.md` § Approvals",
                    "rule 7 no longer names where the escalation list lives")

    def test_approvals_answer_by_default_and_name_every_escalation(self):
        policy = section(self.read("references/console.md"), "Approvals")
        label = "console.md § Approvals"
        self.expect(label, policy, r"(?i)answer every worker approval",
                    "the manager no longer answers approvals by default")
        self.expect(label, policy, r"(?i)broadest persistent option",
                    "answers are not persistent, so the same prompt returns")
        self.expect(label, policy, r"(?i)never one that writes the user's global",
                    "a persistent answer could rewrite global host settings")
        self.expect(label, policy, r"(?i)auto-approved",
                    "auto-answers are not logged for the user to audit")
        self.expect(label, policy, r"(?i)never authori[sz]es",
                    "an Allow in a host dialog could authorize a forbidden action")
        self.expect(label, policy, r"(?i)host permission is not role permission",
                    "an approved prompt could widen a read-only role")
        self.expect(label, policy, r"(?i)unattended.{0,120}reject",
                    "unattended runs have no reversible default for an escalation")
        for case, pattern in ESCALATIONS.items():
            with self.subTest(case=case):
                self.expect(label, policy, pattern.pattern, f"escalation case missing: {case}")

    def test_every_brief_states_its_access(self):
        for role in ("coordinator", "planner", "reviewer"):
            with self.subTest(role=role):
                self.expect(role, self.read(f"references/{role}-brief.md"), r"\*\*Access\.\*\*",
                            "the brief does not say what the manager pre-grants")

    def test_read_only_roles_write_only_to_the_run_directory(self):
        for role in ("planner", "reviewer"):
            with self.subTest(role=role):
                text = self.read(f"references/{role}-brief.md")
                self.expect(role, text, r"(?i)write access only to the run directory",
                            "the pre-grant no longer limits writes to the run directory")
                self.expect(role, text, r"(?i)host permission is not (role )?permission",
                            "an approved prompt could widen the role")

    def test_herdr_launches_with_pre_grants_and_answers_blocked_prompts(self):
        text = self.read("references/herdr.md")
        self.expect("herdr.md", text, r"herdr agent start [^\n]*--pane[^\n]*\n?[^\n]*-- <",
                    "agent start no longer forwards pre-grant args after --")
        rows = launch_rows(text)
        for kind in ("claude", "codex", "opencode, kilo"):
            with self.subTest(kind=kind):
                self.assertIn(kind, rows, f"herdr.md: no launch row for {kind}")
        self.expect("herdr.md", text, r"(?i)always allow",
                    "a blocked prompt is not answered with the persistent option")
        self.expect("herdr.md", text, r"(?i)send-keys",
                    "no way to answer a blocked prompt is named")
        self.expect("herdr.md", text, r"(?i)auto-approved",
                    "auto-answers are not logged")

    def test_no_launch_recipe_bypasses_every_prompt(self):
        for kind, cells in launch_rows(self.read("references/herdr.md")).items():
            with self.subTest(kind=kind):
                self.assertIsNone(BYPASS.search(" ".join(cells)),
                                  "a launch recipe removes the escalation surface")

    def test_each_kind_launches_with_its_grant(self):
        # The mechanism, not the briefs' wording: these cells are what the host enforces.
        rows = launch_rows(self.read("references/herdr.md"))
        expected = {
            "claude": (r"--permission-mode auto", r"--permission-mode dontAsk"),
            "codex": (r"-s workspace-write -a on-request", r"-s read-only -a on-request"),
            "opencode, kilo": (r"OPENCODE_CONFIG_CONTENT", r'"edit":"ask"'),
        }
        for kind, (coordinator, role) in expected.items():
            with self.subTest(kind=kind, role="coordinator"):
                self.assertRegex(rows[kind][0], coordinator, f"{kind} coordinator grant changed")
            with self.subTest(kind=kind, role="planner, reviewer"):
                self.assertRegex(rows[kind][1], role, f"{kind} read-only grant changed")

    def test_read_only_grants_write_only_to_the_run_directory(self):
        role = launch_rows(self.read("references/herdr.md"))["claude"][1]
        writes = re.findall(r"(?:Edit|Write)\(([^)]*)\)", role)
        self.assertEqual(sorted(writes), ["/<run_dir>/**", "/<run_dir>/**"],
                         "a claude planner/reviewer may write outside the run directory")

    def test_opencode_and_kilo_ask_for_every_escalation_command(self):
        text = self.read("references/herdr.md")
        row = next(line for line in text.splitlines() if line.startswith("| opencode, kilo"))
        for variable in ("OPENCODE_CONFIG_CONTENT", "KILO_CONFIG_CONTENT"):
            with self.subTest(variable=variable):
                self.assertIn(variable, row, "opencode/kilo launch without their ask rules")
        rules = re.search(r"<opencode ask> = '(\{.*\})'", text)
        self.assertIsNotNone(rules, "herdr.md: no <opencode ask> rule block")
        bash = json.loads(rules.group(1))["permission"]["bash"]
        for command in ESCALATION_COMMANDS:
            with self.subTest(command=command):
                self.assertEqual(bash.get(command), "ask", f"opencode/kilo run {command} unasked")

    def test_claude_coordinator_asks_for_every_escalation_command(self):
        text = self.read("references/herdr.md")
        self.assertIn("--settings <claude ask>", launch_rows(text)["claude"][0],
                      "claude's auto mode pushes to the main branch without a prompt")
        rules = re.search(r"<claude ask> = '(\{.*\})'", text)
        self.assertIsNotNone(rules, "herdr.md: no <claude ask> rule block")
        asked = {rule.replace(" ", "") for rule in json.loads(rules.group(1))["permissions"]["ask"]}
        for command in ESCALATION_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(f"Bash({command})".replace(" ", ""), asked,
                              f"claude runs {command} unasked")

    def test_approvals_check_afterwards_what_rules_miss(self):
        policy = section(self.read("references/console.md"), "Approvals")
        self.expect("console.md § Approvals", policy, r"(?i)check afterwards.{0,400}is-ancestor",
                    "nothing catches an escalation command that slipped past an ask rule")

    def test_native_path_pre_grants_and_board_keeps_the_audit(self):
        text = self.read("references/console.md")
        native = text[text.index("## Native subagents"):text.index("## Error handling")]
        self.expect("console.md native", native, r"(?i)pre-grant",
                    "the native path has no pre-grant")
        self.expect("console.md native", native, r"(?i)--add-dir",
                    "the native pre-grant names no directories")
        self.expect("console.md native", native, r"--permission-mode auto [^`]*--settings <claude ask>",
                    "the native session runs without the escalation ask rules")
        self.assertIsNone(BYPASS.search(native), "the native relaunch line removes every prompt")
        self.expect("console.md board", text, r"(?i)auto-approved",
                    "the board has no audit list")
        self.expect("console.md board", text, r"(?i)kept on every rewrite",
                    "the audit list can be lost when the board is rewritten")


if __name__ == "__main__":
    unittest.main()
